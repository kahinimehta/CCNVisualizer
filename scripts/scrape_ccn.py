#!/usr/bin/env python3
"""Scrape CCN conference poster/paper submissions from ccneuro.org archives."""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DATA_DIR = ROOT / "docs" / "data"

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
    from text_encoding import repair_mojibake

    text = unescape(text or "")
    text = repair_mojibake(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_keyword_field(raw: str) -> list[str]:
    if not raw:
        return []
    from topic_features import normalize_keyword_phrase, strip_citation_fragments

    raw = strip_citation_fragments(raw)
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
        if kw and len(kw) > 2:
            keywords.append(kw)
    return keywords


def normalize_author_keywords(keywords: list[str]) -> list[str]:
    from topic_features import is_metadata_keyword, normalize_keyword_phrase

    blocked = {"view pdf", "view paper pdf", "extended abstract", "search papers"}
    seen: set[str] = set()
    normalized: list[str] = []
    for kw in keywords:
        cleaned = normalize_keyword_phrase(clean_text(kw))
        if (
            cleaned
            and cleaned not in seen
            and cleaned not in blocked
            and cleaned not in NOISE_KEYWORDS
            and not is_metadata_keyword(cleaned)
        ):
            seen.add(cleaned)
            normalized.append(cleaned)
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
    """Return author keywords, extracted keywords, and combined keywords for theme scoring.

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
    if conference_label:
        return [], extracted, [conference_label]
    extracted = normalize_author_keywords(derive_archive_keywords(title, abstract))
    return [], extracted, extracted


def backfill_keyword_fields(payload: dict) -> dict:
    """Populate author_keywords / extracted_keywords on existing JSON without re-scraping."""
    from pdf_keywords import KEYWORD_SOURCE_NOTE, enrich_submission_keywords, needs_pdf_keyword_refresh

    for submission in payload.get("submissions", []):
        if needs_pdf_keyword_refresh(submission):
            enrich_submission_keywords(submission, try_pdf=True)
        else:
            enrich_submission_keywords(submission, try_pdf=False)

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
            authors = clean_text(text.replace("Presenter:", ""))
            continue
        if text.startswith("Topic Area:"):
            topic_area = clean_text(text.replace("Topic Area:", ""))
            continue
        if not authors and ("<sup>" in str(p) or re.search(r"\([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\)", text, re.I)):
            authors = text
            continue
        if len(text) > 120:
            candidate_abstracts.append(text)

    if candidate_abstracts:
        abstract = max(candidate_abstracts, key=len)

    return {
        "title": title,
        "authors": authors,
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
        from pdf_keywords import finalize_submission_keywords

        detail_html = fetch(item["detail_url"])
        detail = parse_meetingtrakr_detail(detail_html)
        topic_area = detail.get("topic_area") or item.get("topic_area", "")
        title = detail.get("title") or item.get("title", "")
        abstract = detail.get("abstract", "")
        author_keywords, extracted_keywords, keywords = finalize_submission_keywords(
            year=year,
            title=title,
            abstract=abstract,
            topic_area=topic_area,
            html_keywords=detail.get("keywords", []),
            source_url=item["detail_url"],
            detail_html=detail_html,
        )
        return Submission(
            id=item["id"],
            year=year,
            title=title,
            authors=detail.get("authors") or item.get("authors", ""),
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

    submissions.sort(key=lambda s: s.poster_number or s.title)
    return submissions


def scrape_legacy_year(year: int, listing_path: str, link_pattern: str) -> list[Submission]:
    base_url = f"https://{year}.ccneuro.org/"
    listing_url = urljoin(base_url, listing_path)
    print(f"Fetching {listing_url}")
    listing_html = fetch(listing_url)
    listings = parse_legacy_listing(listing_html, listing_url, year, link_pattern)
    print(f"  Found {len(listings)} papers for {year}")

    submissions: list[Submission] = []

    def fetch_detail(item: dict) -> Submission:
        from pdf_keywords import finalize_submission_keywords

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
    from pdf_keywords import fetch_pdf_bytes, extract_pdf_text, finalize_submission_keywords, parse_2017_pdf_fields

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
]


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
            "source": "https://ccneuro.org archives (2017-2025)",
            "years": sorted({s.year for s in all_submissions}),
            "total_count": len(all_submissions),
        },
        "submissions": [asdict(s) for s in all_submissions],
        "stats": serialize_stats(stats),
    }
    return payload


def merge_2026_csv(payload: dict) -> dict:
    """Merge provisional 2026 CSV if present (replaces any prior 2026 rows)."""
    try:
        from merge_2026_csv import merge_into_payload

        return merge_into_payload(payload)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: 2026 CSV merge skipped: {exc}")
        return payload


def assign_research_themes(payload: dict) -> dict:
    """Assign primary_theme and secondary_topics on every submission."""
    try:
        from assign_research_themes import apply_assignments
        import json
        from pathlib import Path

        embeddings_path = ROOT / "docs" / "data" / "embeddings_2026.json"
        if not embeddings_path.exists():
            print("Warning: embeddings_2026.json missing; theme assignment skipped.")
            return payload
        with embeddings_path.open(encoding="utf-8") as fh:
            embeddings = json.load(fh)
        return apply_assignments(payload, embeddings)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: research theme assignment skipped: {exc}")
        return payload


def write_outputs(payload: dict) -> dict:
    payload = merge_2026_csv(payload)
    payload = backfill_keyword_fields(payload)
    payload = assign_research_themes(payload)
    try:
        from build_abstracts_csv import build_from_payload
        import json
        from pathlib import Path

        embeddings_path = ROOT / "docs" / "data" / "embeddings_2026.json"
        embeddings = None
        if embeddings_path.exists():
            with embeddings_path.open(encoding="utf-8") as fh:
                embeddings = json.load(fh)
        build_from_payload(payload, embeddings)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: abstracts.csv export skipped: {exc}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    full_path = DATA_DIR / "submissions.json"
    docs_path = DOCS_DATA_DIR / "submissions.json"

    for path in (full_path, docs_path):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")
    return payload


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Scrape CCN archives")
    parser.add_argument("--years", nargs="*", type=int, help="Specific years to scrape")
    parser.add_argument("--quick", action="store_true", help="Scrape only 2024-2025 for a fast test")
    args = parser.parse_args()

    years = args.years
    if args.quick:
        years = [2024, 2025]

    payload = scrape_all(years)
    payload = write_outputs(payload)
    print(f"Done. Scraped {payload['metadata']['total_count']} submissions.")


if __name__ == "__main__":
    main()
