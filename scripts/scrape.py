#!/usr/bin/env python3
"""Step 1: Scrape CCN archives and write submissions.json.

Pipeline:
  scrape.py  →  submissions.json  (excludes [GAC update] posters)
  build.py   →  Anthropic themes + UMAP + abstracts_2_topics.csv

Dependencies:
  pip install -r requirements.txt
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import unescape
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from shared import (
    is_gac_update,
    is_metadata_keyword,
    is_plausible_keyword,
    keywords_are_title_derived,
    normalize_author_names,
    normalize_keyword_phrase,
    repair_mojibake,
    strip_citation_fragments,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SEARCH_2026_URL = "https://2026.ccneuro.org/search-papers/"
SEARCH_2026_BASE = "https://2026.ccneuro.org"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "CCNVisualizer/1.0 (academic research; github.com/kahinimehta/ccnvisualizer)",
    }
)

NOISE_KEYWORDS = {
    "cognitive science", "august", "september", "october", "november",
    "january", "february", "march", "april", "may", "june", "july",
    "oxford", "berlin", "germany", "san", "francisco", "philadelphia",
    "pennsylvania", "amsterdam", "netherlands", "boston", "massachusetts",
    "conference", "neuroscience", "computational", "cognitive", "ccn",
}


STOPWORDS = {
    "a", "about", "above", "across", "after", "again", "against", "all", "also",
    "an", "and", "any", "are", "as", "at", "be", "been", "before", "being", "between",
    "both", "but", "by", "can", "could", "did", "do", "does", "during", "each", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "him", "his", "how", "however", "if", "in", "into", "is", "it", "its", "just",
    "may", "might", "more", "most", "much", "must", "no", "not", "of", "on", "one",
    "only", "or", "other", "our", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up", "use",
    "using", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "will", "with", "within", "without", "would", "you", "your",
    "abstract", "paper", "study", "studies", "results", "show", "shows", "shown",
    "find", "found", "used", "using", "based", "approach", "model", "models", "data",
    "analysis", "method", "methods", "work", "present", "propose", "proposed",
    "here", "thus", "however", "although", "across", "among", "via", "well", "new",
    "two", "three", "first", "second", "third", "many", "several", "different",
    "including", "compared", "compare", "related", "across", "provide", "provides",
    "demonstrate", "demonstrates", "investigate", "investigates", "examined",
    "examines", "test", "tests", "tested", "human", "humans", "brain", "neural",
}

IGNORED_TOPIC_LABELS = {"view pdf", "view paper pdf", ""}


@dataclass
class Submission:
    id: str
    year: int
    title: str
    authors: str = ""
    abstract: str = ""
    author_keywords: list[str] = field(default_factory=list)
    extracted_keywords: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    topic_area: str = ""
    track: str = ""
    poster_number: str = ""
    source_url: str = ""
    submission_type: str = "poster"


def fetch(url: str, retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = SESSION.get(url, timeout=45)
            response.raise_for_status()
            return response.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def clean_text(text: str) -> str:

    text = unescape(text or "")
    text = repair_mojibake(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_keyword_field(raw: str) -> list[str]:
    if not raw:
        return []

    raw = strip_citation_fragments(raw)
    raw = re.sub(r"\s*;\s*", "; ", raw)
    raw = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw)
    normalized = (
        raw.replace("\u2003", "\u0001")
        .replace("\u00a0", " ")
        .replace("\u2002", "\u0001")
    )
    parts = re.split(r"[\u0001,;&|]+|\s{2,}", normalized)
    keywords = []
    for part in parts:
        kw = clean_text(part)
        kw = normalize_keyword_phrase(kw)
        if not kw or len(kw) <= 2:
            continue
        if any(
            marker in kw
            for marker in (
                "occurs at",
                "every synapse",
                "point in time",
                "synaptic plasticity occurs",
                "similar to structured",
                "connected room",
            )
        ):
            break
        if re.search(r"[∝≈≤≥±×÷′]|\bpr\(", kw):
            break
        keywords.append(kw)
    return keywords


def normalize_author_keywords(keywords: list[str]) -> list[str]:

    blocked = {"view pdf", "view paper pdf", "extended abstract", "search papers"}
    seen: set[str] = set()
    normalized: list[str] = []
    for kw in keywords:
        cleaned = normalize_keyword_phrase(clean_text(kw))
        if not cleaned:
            continue
        if re.fullmatch(r"[\d\(\)\–\-]+", cleaned):
            continue
        if re.search(r"\d+\(\d+\)", cleaned):
            continue
        if (
            cleaned
            and cleaned not in seen
            and cleaned not in blocked
            and cleaned not in NOISE_KEYWORDS
            and not is_metadata_keyword(cleaned)
            and is_plausible_keyword(cleaned)
        ):
            seen.add(cleaned)
            normalized.append(cleaned)
    if len(normalized) > 8:
        multi_word = [kw for kw in normalized if " " in kw and len(kw.split()) >= 2]
        if len(multi_word) >= 2:
            return multi_word[:8]
        if len(normalized) > 12 or (
            len(normalized) >= 6 and sum(1 for kw in normalized if " " not in kw) >= len(normalized) - 1
        ):
            return []
    return normalized


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS and not t.isdigit()]


def derive_archive_keywords(title: str, abstract: str, limit: int = 6) -> list[str]:
    """Last-resort token fallback when author keywords are unavailable in HTML or PDF."""
    derived: list[str] = []
    derived.extend(tokenize(title)[:4])
    if abstract and abstract != title and "@" not in abstract:
        counts = Counter(tokenize(abstract))
        for term, _ in counts.most_common(limit):
            if term not in derived:
                derived.append(term)
    return derived[:limit]


def resolve_keyword_fields(
    *,
    author_keywords: list[str],
    topic_area: str = "",
    track: str = "",
    title: str = "",
    abstract: str = "",
) -> tuple[list[str], list[str], list[str]]:
    """Return author keywords, extracted keywords, and combined keywords.

    Author keywords should be supplied from HTML or PDF before calling this helper.
    Conference track/topic labels and title/abstract tokens are only used when author
    keywords are missing.
    """
    author = normalize_author_keywords(author_keywords)
    extracted: list[str] = []

    conference_label = ""
    for label in (topic_area, track):
        normalized = clean_text(label).lower()
        if normalized and normalized not in IGNORED_TOPIC_LABELS:
            conference_label = normalized
            break

    if author:
        return author, extracted, author
    if conference_label and not is_metadata_keyword(conference_label):
        return [], extracted, [conference_label]
    return [], [], []


def backfill_keyword_fields(payload: dict, *, try_pdf: bool = True) -> dict:
    """Populate author_keywords / extracted_keywords on existing JSON without re-scraping."""

    for submission in payload.get("submissions", []):
        try:
            want_pdf = try_pdf and needs_pdf_keyword_refresh(submission)
            enrich_submission_keywords(submission, try_pdf=want_pdf)
        except Exception as exc:  # noqa: BLE001
            print(
                f"  Warning: keyword backfill failed for {submission.get('id')}: {exc}"
            )

    payload.setdefault("metadata", {})["keyword_source"] = KEYWORD_SOURCE_NOTE
    return payload


def parse_meetingtrakr_listing(html: str, base_url: str, year: int) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.select("table.listing tr"):
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        link = cells[1].find("a", href=re.compile(r"/poster/\?id="))
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"id=([^&'\"]+)", href)
        if not match:
            continue
        poster_id = match.group(1)
        title = clean_text(link.get_text())
        presenter = clean_text(cells[2].get_text()) if len(cells) > 2 else ""
        topic = clean_text(cells[3].get_text()) if len(cells) > 3 else ""
        poster_number = clean_text(cells[0].get_text())
        rows.append(
            {
                "id": poster_id,
                "year": year,
                "title": title,
                "authors": presenter,
                "topic_area": topic,
                "poster_number": poster_number,
                "detail_url": urljoin(base_url, href),
            }
        )
    return rows


def is_noise_paragraph(text: str) -> bool:
    lowered = text.lower()
    return (
        not text
        or "search papers" in lowered
        or lowered.startswith("view pdf")
        or lowered.startswith("view paper pdf")
        or "extended abstract:" in lowered
        or "poster session" in lowered and "poster <" not in lowered
        or lowered.startswith("poster ") and " in " in lowered and len(text) < 180
    )


def author_block_score(text: str) -> int:
    """Higher score = more complete author list (vs a lone presenter name)."""
    if not text:
        return 0
    score = 0
    if ";" in text:
        score += 4
    if re.search(r"\d", text):
        score += 2
    if re.search(r"\([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\)", text, re.I):
        score += 3
    # Multiple "First Last" style tokens separated by commas (accent-tolerant).
    name_token = r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’´`\-.]*"
    name_like = re.findall(rf"\b{name_token}(?:\s+{name_token}){{1,3}}\b", text, re.U)
    if len(name_like) >= 2:
        score += 5
    elif len(name_like) == 1:
        score += 1
    # Comma/and-separated people even when accents break the name regex.
    people = [part.strip() for part in re.split(r"\s*,\s*|\s+;\s*|\s+and\s+", text) if part.strip()]
    if len(people) >= 2:
        score += 3
    if "," in text:
        score += 1
    score += min(len(text) // 40, 6)
    return score


def looks_like_author_block(text: str, paragraph_html: str = "") -> bool:
    if not text or text.startswith("Presenter:") or text.startswith("Topic Area:"):
        return False
    if len(text) > 700:
        return False
    lowered = text.lower()
    if any(token in lowered for token in ("abstract", "keywords:", "extended abstract", "poster session")):
        return False
    if "<sup>" in paragraph_html:
        return True
    if re.search(r"\([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\)", text, re.I):
        return True
    # "Name 1 , Name 2 ; 1 Affiliation"
    if re.search(r"[A-Za-z]\s+\d+\s*,", text) and ";" in text:
        return True
    name_like = re.findall(r"\b[A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){1,3}\b", text)
    return len(name_like) >= 2 and "," in text


def authors_are_thin(authors: str) -> bool:
    """True when we only have a presenter-style single name."""
    if not authors or not authors.strip():
        return True
    return author_block_score(authors) < 4


def parse_meetingtrakr_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    rich = soup.select_one(".fl-rich-text")
    if not rich:
        return {}

    rich_html = str(rich)
    title_el = rich.find("h2")
    title = clean_text(title_el.get_text()) if title_el else ""

    poster_match = re.search(r"Poster\s+<b>([^<]+)</b>", rich_html)
    poster_number = clean_text(poster_match.group(1)) if poster_match else ""

    authors = ""
    presenter = ""
    abstract = ""
    topic_area = ""
    keywords: list[str] = []
    candidate_abstracts: list[str] = []

    for p in rich.find_all("p"):
        raw_text = p.get_text()
        if "Keywords:" in raw_text:
            keywords = parse_keyword_field(raw_text.split("Keywords:", 1)[1])
            continue
        text = clean_text(p.get_text(" ", strip=True))
        if is_noise_paragraph(text):
            continue
        if text.startswith("Presenter:"):
            # Keep as fallback only — never overwrite a fuller author block.
            presenter = clean_text(text.replace("Presenter:", "", 1))
            continue
        if text.startswith("Topic Area:"):
            topic_area = clean_text(text.replace("Topic Area:", "", 1))
            continue
        if looks_like_author_block(text, str(p)):
            if author_block_score(text) >= author_block_score(authors):
                authors = text
            continue
        if len(text) > 120:
            candidate_abstracts.append(text)

    if candidate_abstracts:
        abstract = max(candidate_abstracts, key=len)

    return {
        "title": title,
        "authors": authors or presenter,
        "presenter": presenter,
        "abstract": abstract,
        "topic_area": topic_area,
        "keywords": keywords,
        "poster_number": poster_number,
    }


def parse_legacy_listing(html: str, listing_url: str, year: int, link_pattern: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for link in soup.find_all("a", href=re.compile(link_pattern)):
        href = link.get("href", "")
        match = re.search(r"PaperNum=(\d+)", href)
        if not match:
            continue
        paper_num = match.group(1)
        title = clean_text(link.get_text())
        if not title or len(title) < 5:
            continue
        rows.append(
            {
                "id": paper_num,
                "year": year,
                "title": title,
                "detail_url": urljoin(listing_url, href),
            }
        )
    deduped = {row["id"]: row for row in rows}
    return list(deduped.values())


def parse_legacy_detail(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    title = ""
    authors = ""
    abstract = ""
    track = ""

    title_match = re.search(
        r"Paper Title:\s*</td>\s*<td[^>]*>\s*<b>(.*?)</b>",
        html,
        re.S | re.I,
    )
    if title_match:
        title = clean_text(BeautifulSoup(title_match.group(1), "lxml").get_text())

    if not title:
        for h3 in soup.select(".paper-detail h3, .card-body h3"):
            if "confdate" in (h3.get("class") or []):
                continue
            title = clean_text(h3.get_text())
            if title:
                break

    abstract_div = soup.select_one(".paper-abstract")
    if abstract_div:
        abstract = clean_text(abstract_div.get_text())

    track_div = soup.select_one(".session-trackname")
    if track_div:
        track = clean_text(track_div.get_text())

    for row in soup.select(".card-body .row"):
        text = clean_text(row.get_text())
        if (
            not authors
            and "," in text
            and len(text) < 400
            and "Abstract" not in text
            and "Session" not in text
            and "Track" not in text
        ):
            if re.search(r"[A-Z][a-z]+\s+[A-Z]", text):
                authors = text

    if not authors:
        authors_match = re.search(r"Authors:\s*</td>\s*<td[^>]*>(.*?)</td>", html, re.S | re.I)
        if authors_match:
            authors = clean_text(BeautifulSoup(authors_match.group(1), "lxml").get_text())

    if not abstract:
        abstract_match = re.search(r"Abstract:</TD>\s*<td[^>]*>(.*?)</td>", html, re.S | re.I)
        if abstract_match:
            abstract = clean_text(BeautifulSoup(abstract_match.group(1), "lxml").get_text())

    return {
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "track": track,
        "keywords": [],
    }


def scrape_meetingtrakr_year(year: int) -> list[Submission]:
    base_url = f"https://{year}.ccneuro.org/"
    listing_url = urljoin(base_url, "poster-sessions/?view=all")
    print(f"Fetching {listing_url}")
    listing_html = fetch(listing_url)
    listings = parse_meetingtrakr_listing(listing_html, base_url, year)
    print(f"  Found {len(listings)} posters for {year}")

    submissions: list[Submission] = []

    def fetch_detail(item: dict) -> Submission:

        detail_html = fetch(item["detail_url"])
        detail = parse_meetingtrakr_detail(detail_html)
        topic_area = detail.get("topic_area") or item.get("topic_area", "")
        title = detail.get("title") or item.get("title", "")
        abstract = detail.get("abstract", "")
        authors = detail.get("authors") or item.get("authors", "")
        # 2025/2026 pages often expose the full list before Presenter; if we still
        # only have a thin presenter string, pull names from the PDF header.
        if authors_are_thin(authors):
            pdf_authors = authors_from_pdf(
                year,
                source_url=item["detail_url"],
                html=detail_html,
            )
            if pdf_authors and author_block_score(pdf_authors) >= author_block_score(authors):
                authors = pdf_authors
        if authors_are_thin(authors):
            index_authors = authors_from_abstract_pdf_index(year, title)
            if index_authors and author_block_score(index_authors) >= author_block_score(authors):
                authors = index_authors
        author_keywords, extracted_keywords, keywords = finalize_submission_keywords(
            year=year,
            title=title,
            abstract=abstract,
            topic_area=topic_area,
            html_keywords=detail.get("keywords", []),
            source_url=item["detail_url"],
            detail_html=detail_html,
            # Keywords from HTML when present; PDF keyword mining is optional via --refresh-keywords.
            try_pdf=False,
        )
        return Submission(
            id=item["id"],
            year=year,
            title=title,
            authors=authors,
            abstract=abstract,
            author_keywords=author_keywords,
            extracted_keywords=extracted_keywords,
            keywords=keywords,
            topic_area=topic_area,
            poster_number=detail.get("poster_number") or item.get("poster_number", ""),
            source_url=item["detail_url"],
            submission_type="poster",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_detail, item): item for item in listings}
        for future in as_completed(futures):
            item = futures[future]
            try:
                submissions.append(future.result())
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: failed {year} poster {item.get('id')}: {exc}")
                title = item.get("title", "")
                authors = item.get("authors", "")
                if authors_are_thin(authors):
                    index_authors = authors_from_abstract_pdf_index(year, title)
                    if index_authors:
                        authors = index_authors
                author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
                    author_keywords=[],
                    topic_area=item.get("topic_area", ""),
                    title=title,
                )
                submissions.append(
                    Submission(
                        id=item["id"],
                        year=year,
                        title=title,
                        authors=authors,
                        abstract="",
                        author_keywords=author_keywords,
                        extracted_keywords=extracted_keywords,
                        keywords=keywords,
                        topic_area=item.get("topic_area", ""),
                        poster_number=item.get("poster_number", ""),
                        source_url=item.get("detail_url", ""),
                        submission_type="poster",
                    )
                )

    submissions.sort(key=lambda s: s.poster_number or s.title)
    kept = [submission for submission in submissions if not is_gac_update(submission.title)]
    excluded = len(submissions) - len(kept)
    if excluded:
        print(f"  Excluded {excluded} GAC update poster(s) for {year}")
    return kept


def scrape_legacy_year(year: int, listing_path: str, link_pattern: str) -> list[Submission]:
    base_url = f"https://{year}.ccneuro.org/"
    listing_url = urljoin(base_url, listing_path)
    print(f"Fetching {listing_url}")
    listing_html = fetch(listing_url)
    listings = parse_legacy_listing(listing_html, listing_url, year, link_pattern)
    print(f"  Found {len(listings)} papers for {year}")

    submissions: list[Submission] = []

    def fetch_detail(item: dict) -> Submission:

        detail_html = fetch(item["detail_url"])
        detail = parse_legacy_detail(detail_html)
        title = detail.get("title") or item.get("title", "")
        if title and re.search(r"\b(20\d{2}|january|february|march|april|may|june|july|august|september|october|november|december)\b", title, re.I):
            title = item.get("title", title)
        abstract = detail.get("abstract", "")
        track = detail.get("track", "")
        author_keywords, extracted_keywords, keywords = finalize_submission_keywords(
            year=year,
            title=title,
            abstract=abstract,
            track=track,
            source_url=item["detail_url"],
            detail_html=detail_html,
        )
        return Submission(
            id=item["id"],
            year=year,
            title=title,
            authors=detail.get("authors", ""),
            abstract=abstract,
            author_keywords=author_keywords,
            extracted_keywords=extracted_keywords,
            keywords=keywords,
            topic_area=track,
            track=track,
            source_url=item["detail_url"],
            submission_type="poster",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_detail, item): item for item in listings}
        for future in as_completed(futures):
            item = futures[future]
            try:
                submissions.append(future.result())
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: failed {year} poster {item.get('id')}: {exc}")
                author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
                    author_keywords=[],
                    topic_area=item.get("topic_area", ""),
                    title=item.get("title", ""),
                )
                submissions.append(
                    Submission(
                        id=item["id"],
                        year=year,
                        title=item.get("title", ""),
                        authors=item.get("authors", ""),
                        abstract="",
                        author_keywords=author_keywords,
                        extracted_keywords=extracted_keywords,
                        keywords=keywords,
                        topic_area=item.get("topic_area", ""),
                        poster_number=item.get("poster_number", ""),
                        source_url=item.get("detail_url", ""),
                        submission_type="poster",
                    )
                )

    submissions.sort(key=lambda s: s.title.lower())
    return submissions


def parse_2017_listing(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    for tr in soup.select("table tr"):
        link = tr.find("a", href=re.compile(r"abstract_(\d+)\.pdf"))
        if not link:
            continue
        match = re.search(r"abstract_(\d+)\.pdf", link.get("href", ""))
        if not match:
            continue
        cells = [clean_text(td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        paper_id = match.group(1)
        pdf_href = link.get("href", "")
        rows.append(
            {
                "id": paper_id,
                "year": 2017,
                "title": cells[2],
                "authors": cells[3],
                "pdf_url": urljoin(base_url, pdf_href),
            }
        )
    deduped = {row["id"]: row for row in rows}
    return list(deduped.values())


def scrape_2017_year() -> list[Submission]:

    base_url = "https://2017.ccneuro.org/"
    listing_url = urljoin(base_url, "index.html@p=618.html")
    print(f"Fetching {listing_url}")
    listing_html = fetch(listing_url)
    listings = parse_2017_listing(listing_html, base_url)
    print(f"  Found {len(listings)} papers for 2017")

    submissions: list[Submission] = []

    def fetch_paper(item: dict) -> Submission:
        pdf_bytes = fetch_pdf_bytes(item["pdf_url"])
        pdf_fields = parse_2017_pdf_fields(extract_pdf_text(pdf_bytes))
        topic_area = pdf_fields.get("topic_area", "") or ""
        title = item.get("title", "")
        abstract = pdf_fields.get("abstract", "")
        author_keywords, extracted_keywords, keywords = finalize_submission_keywords(
            year=2017,
            title=title,
            abstract=abstract,
            topic_area=topic_area,
            html_keywords=list(pdf_fields.get("keywords") or []),
            source_url=item["pdf_url"],
            try_pdf=True,
        )
        return Submission(
            id=item["id"],
            year=2017,
            title=title,
            authors=item.get("authors", ""),
            abstract=abstract,
            author_keywords=author_keywords,
            extracted_keywords=extracted_keywords,
            keywords=keywords,
            topic_area=topic_area,
            track=topic_area,
            source_url=item["pdf_url"],
            submission_type="poster",
        )

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_paper, item): item for item in listings}
        for future in as_completed(futures):
            item = futures[future]
            try:
                submissions.append(future.result())
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: failed 2017 paper {item.get('id')}: {exc}")
                author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
                    author_keywords=[],
                    topic_area="",
                    title=item.get("title", ""),
                )
                submissions.append(
                    Submission(
                        id=item["id"],
                        year=2017,
                        title=item.get("title", ""),
                        authors=item.get("authors", ""),
                        abstract="",
                        author_keywords=author_keywords,
                        extracted_keywords=extracted_keywords,
                        keywords=keywords,
                        source_url=item.get("pdf_url", ""),
                        submission_type="poster",
                    )
                )

    submissions.sort(key=lambda s: s.title.lower())
    return submissions


YEAR_CONFIGS = [
    {"year": 2017, "kind": "ccn2017"},
    {"year": 2018, "kind": "legacy", "listing_path": "Papers/AcceptedPapers.html", "link_pattern": r"ViewPaper"},
    {"year": 2019, "kind": "legacy", "listing_path": "Papers/AcceptedPapers.html", "link_pattern": r"ViewPaper"},
    {"year": 2022, "kind": "legacy", "listing_path": "accepted_papers.html", "link_pattern": r"view_paper"},
    {"year": 2023, "kind": "legacy", "listing_path": "accepted_papers.html", "link_pattern": r"view_paper"},
    {"year": 2024, "kind": "meetingtrakr"},
    {"year": 2025, "kind": "meetingtrakr"},
    {"year": 2026, "kind": "search2026"},
]


def normalize_match_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def load_prior_submissions_by_title(year: int) -> dict[str, dict]:
    path = DATA_DIR / "submissions.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    index: dict[str, dict] = {}
    for submission in payload.get("submissions", []):
        if submission.get("year") != year:
            continue
        key = normalize_match_title(submission.get("title", ""))
        if key:
            index[key] = submission
    return index


def match_prior_submission(title: str, index: dict[str, dict], *, cutoff: float = 0.86) -> dict | None:
    key = normalize_match_title(title)
    if key in index:
        return index[key]
    close = difflib.get_close_matches(key, list(index), n=1, cutoff=cutoff)
    if close:
        return index[close[0]]
    return None


def unique_2026_poster_number(poster_number: str, poster_id: str) -> str:
    poster_number = poster_number.strip()
    if re.match(r"^[A-Za-z]+\d+$", poster_number):
        return poster_number
    poster_id = poster_id.strip()
    if poster_id and poster_id != poster_number:
        return f"{poster_number}-{poster_id}"
    return poster_number


def fetch_2026_listings() -> list[dict]:
    SESSION.get(SEARCH_2026_URL, timeout=45)
    response = SESSION.post(
        SEARCH_2026_URL,
        data={
            "form": "search_form",
            "search_string": "",
            "search_papers": "Entire Paper",
            "submit": "Search",
        },
        timeout=120,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    listings: list[dict] = []
    for tr in soup.select("table.listing tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue
        link = cells[1].find("a", href=re.compile(r"poster/\?id="))
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"id=([^&'\"]*)", href)
        poster_id = match.group(1).strip() if match else ""
        poster_number = cells[0].get_text(strip=True)
        listings.append(
            {
                "poster_id": poster_id or poster_number,
                "poster_number": poster_number,
                "title": link.get_text(strip=True),
                "presenter": cells[2].get_text(strip=True),
                "topic_area": cells[3].get_text(strip=True),
            }
        )
    if not listings:
        raise RuntimeError("No 2026 poster rows found in search results.")
    return listings


def scrape_2026_year() -> list[Submission]:
    """Fetch 2026 search listings, then each poster detail for full author lists."""
    print(f"Fetching CCN 2026 listings from {SEARCH_2026_URL}")
    listings = fetch_2026_listings()
    print(f"  Found {len(listings)} posters for 2026")
    prior_by_title = load_prior_submissions_by_title(2026)
    submissions: list[Submission] = []
    carried = 0
    missing = 0
    year = 2026

    work_items: list[dict] = []
    for item in listings:
        poster = unique_2026_poster_number(item["poster_number"], item["poster_id"])
        poster_id = item["poster_id"]
        detail_url = f"{SEARCH_2026_BASE}/poster/?id={poster_id}" if poster_id else SEARCH_2026_BASE
        work_items.append(
            {
                "id": f"2026-{poster or item['title'][:24]}",
                "poster_id": poster_id,
                "year": year,
                "title": item["title"],
                "authors": item.get("presenter", ""),
                "topic_area": clean_text(item.get("topic_area", "")),
                "poster_number": poster,
                "detail_url": detail_url,
            }
        )

    def fetch_detail(item: dict) -> tuple[Submission, bool]:
        detail_html = ""
        detail: dict = {}
        if item.get("detail_url") and item["detail_url"] != SEARCH_2026_BASE:
            detail_html = fetch(item["detail_url"])
            detail = parse_meetingtrakr_detail(detail_html)

        title = detail.get("title") or item.get("title", "")
        topic_label = detail.get("topic_area") or item.get("topic_area", "")
        topic_area = topic_label.lower() if topic_label else ""
        authors = detail.get("authors") or item.get("authors", "")
        if authors_are_thin(authors) and detail_html:
            pdf_authors = authors_from_pdf(year, source_url=item["detail_url"], html=detail_html)
            if pdf_authors and author_block_score(pdf_authors) >= author_block_score(authors):
                authors = pdf_authors

        prior = match_prior_submission(title, prior_by_title)
        abstract = clean_text(detail.get("abstract", "")) or (
            clean_text(prior.get("abstract", "")) if prior else ""
        )
        had_abstract = bool(abstract)
        author_keywords, extracted_keywords, keywords = finalize_submission_keywords(
            year=year,
            title=title,
            abstract=abstract,
            topic_area=topic_area,
            html_keywords=detail.get("keywords") or ([topic_label] if topic_label else []),
            source_url=item["detail_url"],
            detail_html=detail_html or None,
            try_pdf=False,
        )
        submission = Submission(
            id=item["id"],
            year=year,
            title=title,
            authors=authors,
            abstract=abstract,
            author_keywords=author_keywords,
            extracted_keywords=extracted_keywords,
            keywords=keywords,
            topic_area=topic_area,
            poster_number=item.get("poster_number", ""),
            source_url=item["detail_url"],
            submission_type="poster",
        )
        return submission, had_abstract

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_detail, item): item for item in work_items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                submission, had_abstract = future.result()
                submissions.append(submission)
                if had_abstract:
                    carried += 1
                else:
                    missing += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: failed 2026 poster {item.get('id')}: {exc}")
                title = item.get("title", "")
                topic_label = item.get("topic_area", "")
                topic_area = topic_label.lower() if topic_label else ""
                prior = match_prior_submission(title, prior_by_title)
                abstract = clean_text(prior.get("abstract", "")) if prior else ""
                if abstract:
                    carried += 1
                else:
                    missing += 1
                author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
                    author_keywords=[topic_label] if topic_label else [],
                    topic_area=topic_area,
                    title=title,
                )
                submissions.append(
                    Submission(
                        id=item["id"],
                        year=year,
                        title=title,
                        authors=item.get("authors", ""),
                        abstract=abstract,
                        author_keywords=author_keywords,
                        extracted_keywords=extracted_keywords,
                        keywords=keywords,
                        topic_area=topic_area,
                        poster_number=item.get("poster_number", ""),
                        source_url=item.get("detail_url", ""),
                        submission_type="poster",
                    )
                )

    print(f"  Abstracts available: {carried}; missing: {missing}")
    submissions.sort(key=lambda s: s.poster_number or s.title)
    kept = [submission for submission in submissions if not is_gac_update(submission.title)]
    excluded = len(submissions) - len(kept)
    if excluded:
        print(f"  Excluded {excluded} GAC update poster(s) for 2026")
    return kept


def compute_stats(submissions: list[Submission]) -> dict:
    overall = Counter()
    by_year: dict[str, Counter] = defaultdict(Counter)
    topic_by_year: dict[str, Counter] = defaultdict(Counter)
    cooccurrence: Counter[tuple[str, str]] = Counter()

    for sub in submissions:
        year_key = str(sub.year)
        unique_keywords = list(dict.fromkeys(sub.keywords))
        for kw in unique_keywords:
            overall[kw] += 1
            by_year[year_key][kw] += 1
        if sub.topic_area:
            topic_by_year[year_key][sub.topic_area.lower()] += 1
        for i, kw1 in enumerate(unique_keywords):
            for kw2 in unique_keywords[i + 1 :]:
                pair = tuple(sorted((kw1, kw2)))
                cooccurrence[pair] += 1

    top_cooccurrence = [
        {"source": a, "target": b, "count": count}
        for (a, b), count in cooccurrence.most_common(200)
    ]

    return {
        "overall_top": overall.most_common(100),
        "by_year": {year: counter.most_common(50) for year, counter in by_year.items()},
        "topics_by_year": {year: counter.most_common(30) for year, counter in topic_by_year.items()},
        "cooccurrence": top_cooccurrence,
        "counts_by_year": Counter(str(s.year) for s in submissions),
    }


def serialize_stats(stats: dict) -> dict:
    return {
        "overall_top": stats["overall_top"],
        "by_year": stats["by_year"],
        "topics_by_year": stats["topics_by_year"],
        "cooccurrence": stats["cooccurrence"],
        "counts_by_year": dict(stats["counts_by_year"]),
    }


def scrape_all(years: Iterable[int] | None = None) -> dict:
    selected_years = set(years) if years else None
    all_submissions: list[Submission] = []

    for config in YEAR_CONFIGS:
        year = config["year"]
        if selected_years and year not in selected_years:
            continue
        try:
            if config["kind"] == "meetingtrakr":
                submissions = scrape_meetingtrakr_year(year)
            elif config["kind"] == "search2026":
                submissions = scrape_2026_year()
            elif config["kind"] == "ccn2017":
                submissions = scrape_2017_year()
            else:
                submissions = scrape_legacy_year(
                    year,
                    config["listing_path"],
                    config["link_pattern"],
                )
            all_submissions.extend(submissions)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: failed to scrape {year}: {exc}")

    stats = compute_stats(all_submissions)
    payload = {
        "metadata": {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": "https://ccneuro.org archives (2017-2026)",
            "years": sorted({s.year for s in all_submissions}),
            "total_count": len(all_submissions),
        },
        "submissions": [asdict(s) for s in all_submissions],
        "stats": serialize_stats(stats),
    }
    return payload


def write_outputs(payload: dict) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for submission in payload.get("submissions", []):
        submission["authors"] = normalize_author_names(submission.get("authors") or "")
    path = DATA_DIR / "submissions.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {path}")
    return payload


def merge_scraped_years(existing: dict, scraped: dict, years: Iterable[int]) -> dict:
    """Replace only the requested years in an existing submissions.json payload.

    Preserves classification fields (assigned_topics / primary_theme / secondary_topics)
    from prior rows when titles or ids still match.
    """
    year_set = {int(year) for year in years}
    kept = [sub for sub in existing.get("submissions", []) if int(sub.get("year") or 0) not in year_set]

    prior_by_title: dict[tuple[int, str], dict] = {}
    prior_by_id: dict[tuple[int, str], dict] = {}
    for sub in existing.get("submissions", []):
        year = int(sub.get("year") or 0)
        if year not in year_set:
            continue
        title_key = normalize_match_title(sub.get("title", ""))
        if title_key:
            prior_by_title[(year, title_key)] = sub
        sub_id = str(sub.get("id") or "")
        if sub_id:
            prior_by_id[(year, sub_id)] = sub

    preserve_fields = (
        "primary_theme",
        "secondary_topics",
        "assigned_topics",
        "author_keywords",
        "extracted_keywords",
        "keywords",
    )
    incoming: list[dict] = []
    for sub in scraped.get("submissions", []):
        merged = dict(sub)
        year = int(merged.get("year") or 0)
        prior = prior_by_id.get((year, str(merged.get("id") or ""))) or prior_by_title.get(
            (year, normalize_match_title(merged.get("title", "")))
        )
        if prior:
            for field_name in preserve_fields:
                if prior.get(field_name) and not merged.get(field_name):
                    merged[field_name] = prior[field_name]
            if prior.get("abstract") and not merged.get("abstract"):
                merged["abstract"] = prior["abstract"]
            # Keep a fuller prior author list when the new scrape only got a presenter.
            prior_authors = prior.get("authors") or ""
            new_authors = merged.get("authors") or ""
            if author_block_score(prior_authors) > author_block_score(new_authors):
                merged["authors"] = prior_authors
        incoming.append(merged)

    merged_subs = kept + incoming
    as_objs = [
        Submission(
            id=str(sub.get("id", "")),
            year=int(sub.get("year") or 0),
            title=sub.get("title", ""),
            authors=sub.get("authors", ""),
            abstract=sub.get("abstract", ""),
            author_keywords=list(sub.get("author_keywords") or []),
            extracted_keywords=list(sub.get("extracted_keywords") or []),
            keywords=list(sub.get("keywords") or []),
            topic_area=sub.get("topic_area", ""),
            track=sub.get("track", ""),
            poster_number=str(sub.get("poster_number") or ""),
            source_url=sub.get("source_url", ""),
            submission_type=sub.get("submission_type", "poster"),
        )
        for sub in merged_subs
    ]
    stats = compute_stats(as_objs)
    metadata = dict(existing.get("metadata") or {})
    metadata.update(
        {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "source": metadata.get("source") or "https://ccneuro.org archives (2017-2026)",
            "years": sorted({int(sub.get("year") or 0) for sub in merged_subs}),
            "total_count": len(merged_subs),
            "merged_years": sorted(year_set),
        }
    )
    return {
        "metadata": metadata,
        "submissions": merged_subs,
        "stats": serialize_stats(stats),
    }


CACHE_DIR = ROOT / "data" / "pdf_cache"

# Years where proceedings / authored PDFs may contain keywords or author lines.
YEARS_WITH_PDF = (2017, 2018, 2019, 2022, 2023, 2024, 2025, 2026)

KEYWORD_SOURCE_NOTE = (
    "author_keywords prefer author-provided fields (poster HTML, proceedings PDF, 2026 topic areas); "
    "extracted_keywords only when no author keywords or conference label is available"
)


def parse_pdf_url_from_html(html: str, base_url: str) -> str:
    for match in re.finditer(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, re.I):
        url = unescape(match.group(1))
        lowered = url.lower()
        if any(token in lowered for token in ("proceedings", "abstracts/", "/pdf/")) or lowered.endswith(".pdf"):
            return urljoin(base_url, url)

    onclick = re.search(r"window\.open\(['\"]([^'\"]+\.pdf[^'\"]*)['\"]", html, re.I)
    if onclick:
        return urljoin(base_url, unescape(onclick.group(1)))
    return ""


def normalize_pdf_text(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text)


def parse_proceedings_keywords(text: str) -> list[str]:
    if not text:
        return []

    normalized = normalize_pdf_text(text)
    match = re.search(
        r"\bKeywords?\s*:?\s*(.+?)(?:\bIntroduction\b|\b1\s+Introduction\b|\bBackground\b|\bAbstract\b|\Z)",
        normalized,
        re.I | re.S,
    )
    if not match:
        return []

    raw = clean_text(match.group(1))
    if not raw:
        return []
    return normalize_author_keywords(parse_keyword_field(raw))


def parse_2017_keywords(text: str) -> list[str]:
    match = re.search(
        r"Keywords\s*\n(?:Keywords\s*\n)?(?:\d+Conference[^\n]*\n)?(.+?)(?:\n\d+\s*$|\nCo-author|\n\* Presenting|\Z)",
        text,
        re.S,
    )
    if not match:
        return []

    keywords: list[str] = []
    for line in match.group(1).splitlines():
        cleaned = clean_text(line)
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if "conference on cognitive" in lowered:
            continue
        if re.fullmatch(r"\d+", cleaned):
            continue
        if lowered == "keywords":
            continue
        if ";" in cleaned:
            keywords.extend(parse_keyword_field(cleaned))
        else:
            keywords.append(lowered)
    return normalize_author_keywords(keywords)


def parse_keywords_from_pdf_text(text: str) -> list[str]:
    keywords = parse_proceedings_keywords(text)
    if keywords:
        return keywords
    return parse_2017_keywords(text)


def parse_authors_from_pdf_text(text: str) -> str:
    """Best-effort author list from the PDF header (before Abstract/Keywords)."""
    if not text:
        return ""

    # Keep a short header window; authors sit under the title.
    header = text[:3500]
    cutoff = re.search(
        r"(?im)^\s*(Abstract|Keywords?|Introduction|1\s+Introduction)\b",
        header,
    )
    if cutoff:
        header = header[: cutoff.start()]
    # Some PDFs glue "FranceAbstract" with no word boundary before Abstract.
    header = re.split(r"(?i)(?<![A-Za-z])Abstract(?![A-Za-z])", header, maxsplit=1)[0]

    # Allow initials like "A." / "U" inside names.
    name_token = r"(?:[A-ZÀ-ÖØ-Þ]\.?|[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’´`\-]+)"
    name_pattern = rf"{name_token}(?:\s+{name_token}){{1,4}}"
    skip_names = {"abstract", "keywords", "introduction", "extended abstract"}
    junk_tokens = {
        "canada",
        "france",
        "usa",
        "uk",
        "germany",
        "israel",
        "china",
        "japan",
        "italy",
        "spain",
        "tel",
        "aviv",
        "network",
        "neural",
        "convolutional",
        "models",
        "model",
        "brain",
        "human",
        "system",
        "layer",
        "tasks",
        "task",
        "data",
        "collection",
        "complete",
        "diverse",
        "naturalistic",
        "controlled",
        "build",
        "neuroai",
        "manifold",
        "riemannian",
        "encoding",
        "profile",
        "profiles",
        "spectral",
        "information",
        "cognitive",
        "sensory",
        "primate",
        "voice",
        "patches",
        "neurons",
        "multilevel",
        "linguistic",
        "predictions",
        "prediction",
        "the",
        "and",
        "for",
        "of",
        "in",
        "to",
        "a",
        "an",
    }
    affiliation_hints = (
        "university",
        "universit",
        "institute",
        "institut",
        "college",
        "laboratory",
        "lab ",
        "school of",
        "department",
        "département",
        "departement",
        "centre",
        "center",
        "hospital",
        "hôpital",
        "cnrs",
        "inria",
        "umr",
        "equal contribution",
        "correspondence",
        "presenting",
        "co-author",
        "mila",
        "québec",
        "quebec",
        "montréal",
        "montreal",
        "marseille",
        "équipe",
        "team",
    )

    def add_name(raw: str, bucket: list[str]) -> None:
        name = clean_text(raw)
        name = re.sub(r"\s*[\d†‡*#]+\s*$", "", name).strip(" ,;")
        if not name or name.lower() in skip_names or name in bucket:
            return
        parts = [part for part in name.split() if part]
        while parts and parts[0].lower().strip(".") in junk_tokens:
            parts.pop(0)
        while parts and parts[-1].lower().strip(".") in junk_tokens:
            parts.pop()
        # Title text sometimes prefixes the first author; keep the trailing name.
        if len(parts) > 3:
            parts = parts[-2:]
        if len(parts) < 2 or len(parts) > 5:
            return
        name = " ".join(parts)
        lowered_name = name.lower()
        # Use word boundaries so short hints like "mila" do not match "Camila".
        if any(re.search(rf"(?<![a-z]){re.escape(hint)}(?![a-z])", lowered_name) for hint in affiliation_hints):
            return
        if name not in bucket:
            bucket.append(name)

    compact = re.sub(r"\s+", " ", header)
    email_names: list[str] = []
    for match in re.finditer(r"\([^)]+@[^)]+\)", compact):
        before = compact[: match.start()].rstrip()
        before = re.sub(r"[\d†‡*#\s]+$", "", before)
        window = before[-220:]
        # Comma-separated author list ending at this email (common on 2025 PDFs).
        list_match = re.search(
            rf"({name_pattern}(?:\s*,\s*{name_pattern})+)\s*$",
            window,
        )
        if list_match:
            for part in list_match.group(1).split(","):
                add_name(part, email_names)
            continue
        # Otherwise take only the immediately preceding 2–4 name tokens.
        imm = re.search(rf"({name_pattern})\s*$", window)
        if imm:
            add_name(imm.group(1), email_names)

    if len(email_names) >= 2:
        return ", ".join(email_names)

    lines = [clean_text(line) for line in header.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return ", ".join(email_names) if email_names else ""

    body_lines = lines[1:] if len(lines) > 1 else lines
    names: list[str] = list(email_names)

    for line in body_lines:
        lowered = line.lower()
        if any(hint in lowered for hint in affiliation_hints):
            continue
        if re.search(r"https?://|www\.", lowered):
            continue
        match = re.match(
            rf"^({name_pattern})(?:\s*[\d†‡*#]+)?(?:\s*\([^)]+@[^)]+\))?\s*$",
            line,
        )
        if match:
            add_name(match.group(1), names)
            continue
        if looks_like_author_block(line):
            return line

    if len(names) >= 2:
        return ", ".join(names)
    if len(names) == 1:
        return names[0]
    return ""


_ABSTRACT_PDF_INDEX_CACHE: dict[int, list[str]] = {}


def list_abstract_pdf_filenames(year: int) -> list[str]:
    """Directory listing of /abstract_pdf/ for years that publish per-poster PDFs."""
    if year in _ABSTRACT_PDF_INDEX_CACHE:
        return _ABSTRACT_PDF_INDEX_CACHE[year]
    url = f"https://{year}.ccneuro.org/abstract_pdf/"
    try:
        html = fetch(url)
    except Exception:  # noqa: BLE001
        _ABSTRACT_PDF_INDEX_CACHE[year] = []
        return []
    names = sorted(
        {
            unescape(match.group(1))
            for match in re.finditer(r'href=["\']([^"\']+\.pdf)["\']', html, re.I)
            if not match.group(1).startswith("?")
        }
    )
    _ABSTRACT_PDF_INDEX_CACHE[year] = names
    return names


def authors_from_abstract_pdf_index(year: int, title: str) -> str:
    """Match a poster title to /abstract_pdf/ filenames when the detail page is down."""
    if year not in YEARS_WITH_PDF or not title:
        return ""
    files = list_abstract_pdf_filenames(year)
    if not files:
        return ""

    def norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

    title_norm = norm(title)
    title_words = re.findall(r"[A-Za-z0-9]+", title)
    scored: list[tuple[float, int, str]] = []
    for filename in files:
        body = re.sub(rf"^[A-Za-z'’\-]+_{year}_", "", filename.rsplit("/", 1)[-1])
        body = body.rsplit(".", 1)[0]
        score = difflib.SequenceMatcher(None, title_norm, norm(body)).ratio()
        file_words = {word.lower() for word in re.findall(r"[A-Za-z0-9]+", body)}
        title_set = {word.lower() for word in title_words}
        if title_set:
            score = max(score, len(file_words & title_set) / len(title_set))
        scored.append((score, len(filename), filename))
    scored.sort(key=lambda item: (-item[0], item[1]))

    for score, _, filename in scored[:5]:
        if score < 0.5:
            break
        pdf_url = urljoin(f"https://{year}.ccneuro.org/abstract_pdf/", filename)
        try:
            authors = parse_authors_from_pdf_text(pdf_text_from_url(pdf_url))
        except Exception:  # noqa: BLE001
            continue
        if authors and not authors_are_thin(authors):
            return authors
    return ""


def authors_from_pdf(
    year: int,
    source_url: str = "",
    html: str | None = None,
    *,
    fetch_html: bool = False,
) -> str:
    if year not in YEARS_WITH_PDF:
        return ""
    base_url = f"https://{year}.ccneuro.org/"
    if year == 2017 and source_url.lower().endswith(".pdf"):
        try:
            return parse_authors_from_pdf_text(pdf_text_from_url(source_url))
        except Exception:  # noqa: BLE001
            return ""

    if html is None and fetch_html and source_url and not source_url.lower().endswith(".pdf"):
        try:
            html = fetch(source_url)
        except Exception:  # noqa: BLE001
            html = None

    if not html:
        return ""
    pdf_url = parse_pdf_url_from_html(html, base_url)
    if not pdf_url:
        return ""
    try:
        return parse_authors_from_pdf_text(pdf_text_from_url(pdf_url))
    except Exception:  # noqa: BLE001
        return ""


def parse_2017_pdf_fields(text: str) -> dict[str, str | list[str]]:
    abstract_match = re.search(
        r"Presentation Abstract Summary\s+(.+?)(?:\nPaper Upload|\nCo-author|\Z)",
        text,
        re.S,
    )
    topic_match = re.search(r"Topic\s+(.+?)(?:\nStatus|\nSubmitter)", text, re.S)
    return {
        "abstract": clean_text(abstract_match.group(1)) if abstract_match else "",
        "topic_area": clean_text(topic_match.group(1)).lower() if topic_match else "",
        "keywords": parse_2017_keywords(text),
    }


def _cache_path(url: str, suffix: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return CACHE_DIR / f"{digest}{suffix}"


def fetch_pdf_bytes(url: str) -> bytes:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(url, ".pdf")
    if cache_file.exists():
        cached = cache_file.read_bytes()
        if cached.startswith(b"%PDF"):
            return cached
        cache_file.unlink(missing_ok=True)

    response = SESSION.get(url, timeout=60)
    response.raise_for_status()
    content = response.content
    if not content.startswith(b"%PDF"):
        raise ValueError(f"Not a PDF: {url}")
    cache_file.write_bytes(content)
    return content


def extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    return "".join((page.extract_text() or "") for page in reader.pages)


def sanitize_pdf_text(text: str) -> str:
    """Drop invalid Unicode surrogates that extracted PDF text sometimes contains."""
    return text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def pdf_text_from_url(url: str) -> str:
    text_cache = _cache_path(url, ".txt")
    if text_cache.exists():
        try:
            return text_cache.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text_cache.unlink(missing_ok=True)
    text = sanitize_pdf_text(extract_pdf_text(fetch_pdf_bytes(url)))
    text_cache.write_text(text, encoding="utf-8")
    return text


def keywords_from_pdf_url(url: str) -> list[str]:
    if not url:
        return []
    try:
        return parse_keywords_from_pdf_text(pdf_text_from_url(url))
    except Exception as exc:  # noqa: BLE001
        print(f"    keyword PDF fetch failed: {url} ({exc})")
        return []


def keywords_from_detail_html(html: str, base_url: str) -> list[str]:
    pdf_url = parse_pdf_url_from_html(html, base_url)
    if not pdf_url:
        return []
    return keywords_from_pdf_url(pdf_url)


def author_keywords_from_pdf(
    *,
    year: int,
    source_url: str,
    detail_html: str | None = None,
    fetch_html: bool = True,
) -> list[str]:
    if year not in YEARS_WITH_PDF:
        return []

    try:
        if year == 2017 and source_url.lower().endswith(".pdf"):
            return keywords_from_pdf_url(source_url)

        base_url = f"https://{year}.ccneuro.org/"
        html = detail_html
        if html is None and fetch_html and source_url and not source_url.lower().endswith(".pdf"):
            html = SESSION.get(source_url, timeout=45).text

        if html:
            pdf_url = parse_pdf_url_from_html(html, base_url)
            if pdf_url:
                return keywords_from_pdf_url(pdf_url)
    except Exception as exc:  # noqa: BLE001
        print(f"    author keyword PDF failed for {source_url}: {exc}")
    return []


def initial_html_keywords(submission: dict) -> list[str]:
    author = list(submission.get("author_keywords") or [])
    if author:
        return author

    year = submission.get("year")
    merged = list(submission.get("keywords") or [])
    if merged and year in (2024, 2025, 2026):
        return merged
    return merged if merged and year not in YEARS_WITH_PDF else []


def finalize_submission_keywords(
    *,
    year: int,
    title: str,
    abstract: str,
    topic_area: str = "",
    track: str = "",
    source_url: str = "",
    html_keywords: list[str] | None = None,
    detail_html: str | None = None,
    try_pdf: bool = True,
) -> tuple[list[str], list[str], list[str]]:
    """Prefer author keywords from HTML, then PDF; algorithmic tokens are last resort."""
    author = normalize_author_keywords(html_keywords or [])

    if not author and try_pdf:
        pdf_keywords = author_keywords_from_pdf(
            year=year,
            source_url=source_url,
            detail_html=detail_html,
            fetch_html=detail_html is None,
        )
        if pdf_keywords:
            author = pdf_keywords

    if author:
        return author, [], author

    return resolve_keyword_fields(
        author_keywords=[],
        topic_area=topic_area,
        track=track,
        title=title,
        abstract=abstract,
    )


def enrich_submission_keywords(
    submission: dict,
    *,
    detail_html: str | None = None,
    try_pdf: bool = True,
) -> dict:
    html_keywords = initial_html_keywords(submission)
    if not html_keywords and detail_html:

        if "Keywords:" in detail_html or "fl-rich-text" in detail_html:
            html_keywords = parse_meetingtrakr_detail(detail_html).get("keywords", [])

    author_keywords, extracted_keywords, keywords = finalize_submission_keywords(
        year=submission.get("year", 0),
        title=submission.get("title", ""),
        abstract=submission.get("abstract", ""),
        topic_area=submission.get("topic_area", ""),
        track=submission.get("track", ""),
        source_url=submission.get("source_url", ""),
        html_keywords=html_keywords,
        detail_html=detail_html,
        try_pdf=try_pdf,
    )
    submission["author_keywords"] = author_keywords
    submission["extracted_keywords"] = extracted_keywords
    submission["keywords"] = keywords
    return submission


def needs_pdf_keyword_refresh(submission: dict, *, force: bool = False) -> bool:
    if force:
        year = submission.get("year")
        return year in YEARS_WITH_PDF and bool(submission.get("source_url"))
    if submission.get("author_keywords"):
        return False
    year = submission.get("year")
    if year not in YEARS_WITH_PDF:
        return False
    return bool(submission.get("source_url"))


def _refresh_one(submission: dict, *, force: bool = False) -> tuple[str, bool]:
    had_author = bool(submission.get("author_keywords"))
    if force:
        submission["author_keywords"] = []
        submission["extracted_keywords"] = []
        submission["keywords"] = []
    if needs_pdf_keyword_refresh(submission, force=force):
        try:
            detail_html = fetch(submission["source_url"])
        except Exception:
            detail_html = None
        enrich_submission_keywords(submission, detail_html=detail_html, try_pdf=True)
    else:
        enrich_submission_keywords(submission, try_pdf=False)
    return submission.get("id", ""), bool(submission.get("author_keywords")) and not had_author


def refresh_keywords(payload: dict, *, years: set[int] | None = None, force: bool = False) -> dict:
    submissions = payload.get("submissions", [])
    if years:
        submissions = [sub for sub in submissions if sub.get("year") in years]
    print(f"Refreshing keywords for {len(submissions)} submissions")
    updated = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(_refresh_one, sub, force=force): sub for sub in submissions
        }
        for index, future in enumerate(as_completed(futures), start=1):
            _, gained = future.result()
            if gained:
                updated += 1
            if index % 100 == 0 or index == len(submissions):
                print(f"  processed {index}/{len(submissions)} ({updated} gained author keywords)")
    payload.setdefault("metadata", {})["keyword_source"] = KEYWORD_SOURCE_NOTE
    print(f"Done. {updated} submissions gained author keywords.")
    return payload

def add_2017_to_payload(payload: dict) -> dict:
    submissions_2017 = [asdict(item) for item in scrape_2017_year()]
    kept = [sub for sub in payload.get("submissions", []) if sub.get("year") != 2017]
    payload["submissions"] = submissions_2017 + kept
    payload.setdefault("metadata", {})
    payload["metadata"]["total_count"] = len(payload["submissions"])
    payload["metadata"]["years"] = sorted({sub["year"] for sub in payload["submissions"]})
    print(f"Merged {len(submissions_2017)} submissions from 2017.")
    return payload

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Scrape CCN archives → submissions.json")
    parser.add_argument("--years", nargs="*", type=int)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--refresh-keywords", action="store_true")
    parser.add_argument(
        "--force-keywords",
        action="store_true",
        help="With --refresh-keywords, re-fetch PDF keywords even when author_keywords exist",
    )
    parser.add_argument("--add-2017", action="store_true")
    args = parser.parse_args()
    if args.refresh_keywords:
        path = DATA_DIR / "submissions.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        years = set(args.years) if args.years else None
        write_outputs(refresh_keywords(payload, years=years, force=args.force_keywords))
        return
    if args.add_2017:
        path = DATA_DIR / "submissions.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        payload = add_2017_to_payload(payload)
        write_outputs(backfill_keyword_fields(payload))
        return
    years = [2024, 2025] if args.quick else args.years
    payload = scrape_all(years)
    path = DATA_DIR / "submissions.json"
    if years and path.exists():
        with path.open(encoding="utf-8") as fh:
            existing = json.load(fh)
        payload = merge_scraped_years(existing, payload, years)
        print(
            f"Merged years {sorted(set(years))} into existing submissions.json "
            f"({payload['metadata']['total_count']} total)."
        )
    # Persist scrape results before keyword normalization so a later failure cannot lose them.
    write_outputs(payload)
    # Align keyword list fields without a second PDF crawl (use --refresh-keywords for that).
    write_outputs(backfill_keyword_fields(payload, try_pdf=False))
    print(f"Done. Scraped {payload['metadata']['total_count']} submissions.")

if __name__ == "__main__":
    main()
