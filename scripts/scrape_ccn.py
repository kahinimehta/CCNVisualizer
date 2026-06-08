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


@dataclass
class Submission:
    id: str
    year: int
    title: str
    authors: str = ""
    abstract: str = ""
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
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_keyword_field(raw: str) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[&;,]+|\s{2,}", raw)
    keywords = []
    for part in parts:
        kw = clean_text(part)
        if kw and len(kw) > 2:
            keywords.append(kw.lower())
    return keywords


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS and not t.isdigit()]


def derive_keywords(title: str, abstract: str, topic_area: str = "", limit: int = 6) -> list[str]:
    derived: list[str] = []
    if topic_area and topic_area.lower() not in {"view pdf", "view paper pdf"}:
        derived.append(topic_area.lower())

    title_tokens = tokenize(title)
    derived.extend(title_tokens[:4])

    if abstract and abstract != title and "@" not in abstract:
        abstract_tokens = tokenize(abstract)
        counts = Counter(abstract_tokens)
        for term, _ in counts.most_common(limit):
            if term not in derived:
                derived.append(term)

    return derived[:limit]


def merge_keywords(explicit: list[str], derived: list[str]) -> list[str]:
    blocked = {"view pdf", "view paper pdf", "extended abstract", "search papers"}
    seen: set[str] = set()
    merged: list[str] = []
    for kw in explicit + derived:
        normalized = clean_text(kw).lower()
        if (
            normalized
            and normalized not in seen
            and normalized not in blocked
            and normalized not in NOISE_KEYWORDS
        ):
            seen.add(normalized)
            merged.append(normalized)
    return merged


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
        text = clean_text(p.get_text(" ", strip=True))
        if is_noise_paragraph(text):
            continue
        if text.startswith("Presenter:"):
            authors = clean_text(text.replace("Presenter:", ""))
            continue
        if text.startswith("Topic Area:"):
            topic_area = clean_text(text.replace("Topic Area:", ""))
            continue
        if text.startswith("Keywords:"):
            keywords = parse_keyword_field(text.replace("Keywords:", ""))
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
        detail_html = fetch(item["detail_url"])
        detail = parse_meetingtrakr_detail(detail_html)
        explicit_keywords = detail.get("keywords", [])
        topic_area = detail.get("topic_area") or item.get("topic_area", "")
        title = detail.get("title") or item.get("title", "")
        abstract = detail.get("abstract", "")
        derived = derive_keywords(title, abstract, topic_area=topic_area)
        keywords = merge_keywords(explicit_keywords, derived)
        return Submission(
            id=item["id"],
            year=year,
            title=title,
            authors=detail.get("authors") or item.get("authors", ""),
            abstract=abstract,
            keywords=keywords,
            topic_area=topic_area,
            poster_number=detail.get("poster_number") or item.get("poster_number", ""),
            source_url=item["detail_url"],
            submission_type="poster",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_detail, item): item for item in listings}
        for future in as_completed(futures):
            submissions.append(future.result())

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
        detail_html = fetch(item["detail_url"])
        detail = parse_legacy_detail(detail_html)
        title = detail.get("title") or item.get("title", "")
        if title and re.search(r"\b(20\d{2}|january|february|march|april|may|june|july|august|september|october|november|december)\b", title, re.I):
            title = item.get("title", title)
        abstract = detail.get("abstract", "")
        track = detail.get("track", "")
        derived = derive_keywords(title, abstract, topic_area=track)
        keywords = merge_keywords(detail.get("keywords", []), derived)
        return Submission(
            id=item["id"],
            year=year,
            title=title,
            authors=detail.get("authors", ""),
            abstract=abstract,
            keywords=keywords,
            topic_area=track,
            track=track,
            source_url=item["detail_url"],
            submission_type="poster",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_detail, item): item for item in listings}
        for future in as_completed(futures):
            submissions.append(future.result())

    submissions.sort(key=lambda s: s.title.lower())
    return submissions


YEAR_CONFIGS = [
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
            "source": "https://ccneuro.org archives (2018-2025)",
            "years": sorted({s.year for s in all_submissions}),
            "total_count": len(all_submissions),
        },
        "submissions": [asdict(s) for s in all_submissions],
        "stats": serialize_stats(stats),
    }
    return payload


def write_outputs(payload: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    full_path = DATA_DIR / "submissions.json"
    docs_path = DOCS_DATA_DIR / "submissions.json"

    for path in (full_path, docs_path):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")


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
    write_outputs(payload)
    print(f"Done. Scraped {payload['metadata']['total_count']} submissions.")


if __name__ == "__main__":
    main()
