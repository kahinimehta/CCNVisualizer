#!/usr/bin/env python3
"""Step 1: Scrape CCN archives and write submissions.json.

Dependencies (install once):
  pip install requests beautifulsoup4 lxml pypdf
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from html import unescape
from io import BytesIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DOCS_DATA_DIR = ROOT / "docs" / "data"
CSV_PATH_2026 = ROOT / "data" / "ccn-2026-pending-posters.csv"

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

# Conference area labels and method/format tags — not topical content.
METADATA_KEYWORD_PHRASES = frozenset(
    {
        "psychological / behavioral research",
        "computational cognitive science / cognitive modeling",
        "theoretical / computational neuroscience",
        "experimental neuroscience (systems / cognitive)",
        "artificial intelligence / machine learning",
        "methods & computational tools",
        "brain networks & neural dynamics",
        "visual processing & computational vision",
        "object recognition & visual attention",
        "reward, value & social decision making",
        "memory, spatial cognition & skill learning",
        "predictive processing & cognitive control",
        "language & communication",
        "extended abstract",
        "extended abstracts",
        "cognitive science",
        "neuroscience",
        "psychology",
        "engineering",
        "mathematics",
        "philosophy",
        "artificial intelligence",
        "linguistics",
    }
)

METADATA_KEYWORD_TOKENS = frozenset(
    {
        "fmri",
        "eeg",
        "meg",
        "ecog",
        "bold",
        "neuroimaging",
        "psychological",
        "behavioral",
        "computational",
        "modeling",
        "experimental",
        "systems",
        "cognitive",
        "abstract",
        "poster",
        "paper",
        "proceedings",
    }
)

GENERIC_KEYWORD_LABELS = frozenset({"cognitive science", "cognitive"})

CITATION_FRAGMENT_RES = (
    re.compile(r"\bet\s+al\.?", re.I),
    re.compile(r"\bp\.?\s*\d+(?:\s*[-–—]\s*\d+)?", re.I),
    re.compile(r"\bpp\.?\s*\d+", re.I),
    re.compile(r"\bdoi\s*[:.]?\s*\S+", re.I),
    re.compile(r"https?://\S+", re.I),
    re.compile(r"\bvol\.?\s*\d+", re.I),
    re.compile(r"\bno\.?\s*\d+", re.I),
    re.compile(r"\(\s*\d{4}[a-z]?\s*\)", re.I),
)

# Topic prototype anchors — used for TF-IDF cosine scoring.
TOPIC_ANCHORS: dict[str, list[str]] = {
    "RL, motor control & planning": [
        "reinforcement learning",
        "reward",
        "motor control",
        "planning",
        "policy",
        "navigation",
        "action selection",
        "skill learning",
        "habit",
        "basal ganglia",
    ],
    "Naturalistic encoding/decoding": [
        "naturalistic",
        "encoding model",
        "decoding",
        "voxel-wise",
        "stimulus reconstruction",
        "movie",
        "narrative",
        "resting state",
        "natural scenes",
        "video",
    ],
    "Neural population geometry & dynamics": [
        "neural population",
        "population dynamics",
        "geometry",
        "manifold",
        "latent dynamics",
        "trajectory",
        "oscillation",
        "connectivity",
        "state space",
    ],
    "Decision-making and metacognition": [
        "decision making",
        "decision-making",
        "metacognition",
        "confidence",
        "choice",
        "judgment",
        "belief updating",
        "inference",
        "evidence accumulation",
    ],
    "Vision": [
        "visual",
        "vision",
        "retina",
        "v1",
        "v2",
        "retinotopic",
        "scene perception",
        "optic flow",
        "gaze",
        "saccade",
        "conscious vision",
        "visual awareness",
        "perceptual",
    ],
    "Language/auditory neuroscience": [
        "language",
        "auditory",
        "speech",
        "semantic",
        "syntax",
        "word",
        "listening",
        "voice",
        "reading",
        "phonology",
    ],
    "LLMs, reasoning, interpretability": [
        "large language model",
        "language model",
        "llm",
        "transformer",
        "gpt",
        "chatgpt",
        "prompt",
        "prompting",
        "in-context learning",
        "rlhf",
        "chain-of-thought",
        "chain of thought",
        "foundation model",
        "instruction tuning",
        "fine-tuning",
        "generative model",
        "pretrained",
    ],
    "Memory": [
        "memory",
        "hippocampus",
        "recall",
        "working memory",
        "episodic",
        "retrieval",
        "spatial memory",
        "consolidation",
    ],
    "Social cognition & theory of mind": [
        "social cognition",
        "theory of mind",
        "mentalizing",
        "social interaction",
        "empathy",
        "tom",
        "agent",
        "cooperation",
        "mental state",
    ],
    "Attention & cognitive control / executive function": [
        "attention",
        "executive function",
        "cognitive control",
        "task switching",
        "inhibition",
        "working memory control",
        "predictive processing",
        "conflict monitoring",
    ],
    "Clinical / computational psychiatry": [
        "clinical",
        "psychiatry",
        "depression",
        "schizophrenia",
        "patient",
        "disorder",
        "mental health",
        "autism",
        "anxiety",
        "bipolar",
    ],
    "Methods, theory & everything else": [
        "method",
        "benchmark",
        "framework",
        "simulation",
        "theory",
        "analysis toolkit",
        "interpretability",
        "explainability",
        "attention mechanism",
        "recurrent neural network",
        "rnn",
        "lstm",
        "symbolic reasoning",
        "generalization",
        "statistical",
    ],
}

TITLE_WEIGHT = 2
ABSTRACT_WEIGHT = 3
KEYWORD_WEIGHT = 1

RELEVANCE_RATIO = 0.5
ABSOLUTE_COSINE_FLOOR = 0.05
MAX_ASSIGNED_TOPICS = 5
BROAD_HINT_BOOST = 0.04


def strip_citation_fragments(text: str) -> str:
    if not text:
        return ""
    cleaned = text
    for pattern in CITATION_FRAGMENT_RES:
        cleaned = pattern.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;")
    return cleaned.strip()


def normalize_keyword_phrase(keyword: str) -> str:
    return strip_citation_fragments(re.sub(r"\s+", " ", (keyword or "").strip().lower()))


def is_metadata_keyword(keyword: str) -> bool:
    normalized = normalize_keyword_phrase(keyword)
    if not normalized:
        return True
    if normalized in METADATA_KEYWORD_PHRASES:
        return True
    if normalized in GENERIC_KEYWORD_LABELS:
        return True
    tokens = re.findall(r"[a-z][a-z0-9\-]{2,}", normalized)
    if tokens and all(token in METADATA_KEYWORD_TOKENS for token in tokens):
        return True
    return False


def sanitize_keyword_list(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for keyword in keywords or []:
        normalized = normalize_keyword_phrase(str(keyword))
        if not normalized or len(normalized) <= 2:
            continue
        if is_metadata_keyword(normalized):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def sanitize_submission_keywords(submission: dict) -> None:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        submission[field] = sanitize_keyword_list(list(submission.get(field) or []))


def content_keywords(submission: dict) -> list[str]:
    for field in ("author_keywords", "extracted_keywords", "keywords"):
        values = sanitize_keyword_list(list(submission.get(field) or []))
        if values:
            return values
    return []


def is_weak_keyword_set(keywords: list[str]) -> bool:
    cleaned = sanitize_keyword_list(keywords)
    return not cleaned


def submission_embedding_text(submission: dict) -> str:
    """Build weighted embedding text: abstract-heavy, metadata keywords excluded."""
    title = (submission.get("title") or "").strip()
    abstract = (submission.get("abstract") or "").strip()
    chunks: list[str] = []
    if title:
        chunks.extend([title] * TITLE_WEIGHT)
    if abstract:
        chunks.extend([abstract] * ABSTRACT_WEIGHT)
    keywords = content_keywords(submission)
    if keywords:
        keyword_blob = " ".join(keywords)
        chunks.extend([keyword_blob] * KEYWORD_WEIGHT)
    blob = ". ".join(chunks).strip()
    return blob or title or "empty"


def topic_prototype_text(theme: str) -> str:
    anchors = TOPIC_ANCHORS.get(theme, [])
    parts: list[str] = []
    for anchor in anchors:
        repeat = 3 if " " in anchor else 2
        parts.extend([anchor] * repeat)
    return " ".join(parts) or theme.lower()


def vectorizer_stop_words() -> list[str]:
    return sorted(ENGLISH_STOP_WORDS | METADATA_KEYWORD_TOKENS)

import re

# Typical signs of UTF-8 bytes interpreted as Latin-1 (e.g. Ã¶ → ö).
_MOJIBAKE_MARKERS = re.compile(r"[ÃÄÅÆÇÐÑØÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ\u0080-\u009f]")


def repair_mojibake(text: str) -> str:
    """Fix UTF-8-as-Latin-1 mojibake when possible; otherwise return unchanged."""
    if not text or not _MOJIBAKE_MARKERS.search(text):
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def repair_submission_text(submission: dict) -> None:
    """Normalize text fields on a submission dict in place."""
    for field in ("title", "authors", "abstract", "topic_area", "track"):
        if field in submission and submission[field]:
            submission[field] = repair_mojibake(str(submission[field]))

    for field in ("author_keywords", "extracted_keywords", "keywords", "secondary_topics", "assigned_topics"):
        values = submission.get(field)
        if not values:
            continue
        submission[field] = [repair_mojibake(str(value)) for value in values if value]

    if submission.get("primary_theme"):
        submission["primary_theme"] = repair_mojibake(str(submission["primary_theme"]))

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

    text = unescape(text or "")
    text = repair_mojibake(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_keyword_field(raw: str) -> list[str]:
    if not raw:
        return []

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


def write_outputs(payload: dict) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for path in (DATA_DIR / "submissions.json", DOCS_DATA_DIR / "submissions.json"):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")
    return payload




import hashlib
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin



ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "pdf_cache"

# Years where proceedings / authored PDFs may contain a keyword line.
YEARS_WITH_PDF = (2017, 2018, 2019, 2022, 2023, 2024, 2025)

KEYWORD_SOURCE_NOTE = (
    "author_keywords prefer author-provided fields (poster HTML, proceedings PDF, 2026 CSV); "
    "extracted_keywords only when no author keywords or conference label is available"
)


def parse_pdf_url_from_html(html: str, base_url: str) -> str:
    for match in re.finditer(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, re.I):
        url = match.group(1)
        lowered = url.lower()
        if any(token in lowered for token in ("proceedings", "abstracts/", "/pdf/")) or lowered.endswith(".pdf"):
            return urljoin(base_url, url)

    onclick = re.search(r"window\.open\(['\"]([^'\"]+\.pdf[^'\"]*)['\"]", html, re.I)
    if onclick:
        return urljoin(base_url, onclick.group(1))
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
        r"\bKeywords?\s*:\s*(.+?)(?:\bIntroduction\b|\b1\s+Introduction\b|\bBackground\b|\bAbstract\b|\Z)",
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
        return cache_file.read_bytes()

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


def pdf_text_from_url(url: str) -> str:
    text_cache = _cache_path(url, ".txt")
    if text_cache.exists():
        return text_cache.read_text(encoding="utf-8")
    text = extract_pdf_text(fetch_pdf_bytes(url))
    text_cache.write_text(text, encoding="utf-8")
    return text


def keywords_from_pdf_url(url: str) -> list[str]:
    if not url:
        return []
    return parse_keywords_from_pdf_text(pdf_text_from_url(url))


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


def needs_pdf_keyword_refresh(submission: dict) -> bool:
    if submission.get("author_keywords"):
        return False
    year = submission.get("year")
    if year not in YEARS_WITH_PDF:
        return False
    return bool(submission.get("source_url"))


# Backwards-compatible alias used by older scripts.
PDF_KEYWORD_YEARS = YEARS_WITH_PDF


SUBMISSION_FIELDS = {f.name for f in fields(Submission)}

def submission_from_dict(item: dict) -> Submission:
    return Submission(**{key: value for key, value in item.items() if key in SUBMISSION_FIELDS})

def normalize_topic_area_csv(primary: str, secondary: str = "") -> str:
    parts = [p.strip() for p in re.split(r"[+;,]", f"{primary},{secondary}") if p.strip()]
    return parts[0].lower() if parts else ""

def author_keywords_from_csv(row: dict[str, str]) -> list[str]:
    keywords: list[str] = []
    for field in ("primary_area", "secondary_area"):
        raw = (row.get(field) or "").strip()
        if not raw:
            continue
        for part in re.split(r"[+;,]", raw):
            kw = part.strip()
            if kw:
                keywords.append(kw)
    return keywords

def csv_row_to_submission(row: dict[str, str]) -> Submission:
    poster = (row.get("or_number") or "").strip()
    title = (row.get("title") or "").strip()
    abstract = (row.get("abstract") or "").strip()
    primary = (row.get("primary_area") or "").strip()
    secondary = (row.get("secondary_area") or "").strip()
    topic_area = normalize_topic_area_csv(primary, secondary)
    author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
        author_keywords=author_keywords_from_csv(row), topic_area=topic_area,
    )
    return Submission(
        id=f"2026-{poster or title[:24]}", year=2026, title=title, authors="", abstract=abstract,
        author_keywords=author_keywords, extracted_keywords=extracted_keywords, keywords=keywords,
        topic_area=topic_area, track=(row.get("track") or "").strip(), poster_number=poster,
        source_url="https://2026.ccneuro.org/", submission_type="poster",
    )

def load_csv_submissions() -> list[Submission]:
    if not CSV_PATH_2026.exists():
        print(f"No 2026 CSV at {CSV_PATH_2026}; skipping merge.")
        return []
    with CSV_PATH_2026.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    submissions = [csv_row_to_submission(row) for row in rows if (row.get("title") or "").strip()]
    print(f"Loaded {len(submissions)} submissions from {CSV_PATH_2026.name}")
    return submissions

def merge_2026_into_payload(payload: dict) -> dict:
    csv_subs = load_csv_submissions()
    if not csv_subs:
        return payload
    kept = [s for s in payload.get("submissions", []) if s.get("year") != 2026]
    submission_objs = [submission_from_dict(item) for item in kept] + csv_subs
    stats = compute_stats(submission_objs)
    payload["submissions"] = [asdict(s) for s in submission_objs]
    payload["stats"] = serialize_stats(stats)
    payload.setdefault("metadata", {})
    payload["metadata"]["total_count"] = len(submission_objs)
    payload["metadata"]["years"] = sorted({s.year for s in submission_objs})
    payload["metadata"]["source"] = "https://ccneuro.org archives (2017-2025) + 2026 pending CSV"
    payload["metadata"]["csv_2026"] = {"path": str(CSV_PATH_2026.relative_to(ROOT)), "merged_at": datetime.now(timezone.utc).isoformat(), "count": len(csv_subs)}
    return payload

def _refresh_one(submission: dict) -> tuple[str, bool]:
    had_author = bool(submission.get("author_keywords"))
    if needs_pdf_keyword_refresh(submission):
        try:
            detail_html = fetch(submission["source_url"])
        except Exception:
            detail_html = None
        enrich_submission_keywords(submission, detail_html=detail_html, try_pdf=True)
    else:
        enrich_submission_keywords(submission, try_pdf=False)
    return submission.get("id", ""), bool(submission.get("author_keywords")) and not had_author

def refresh_keywords(payload: dict) -> dict:
    submissions = payload.get("submissions", [])
    print(f"Refreshing keywords for {len(submissions)} submissions")
    updated = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_refresh_one, sub): sub for sub in submissions}
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
    parser.add_argument("--merge-2026", action="store_true")
    parser.add_argument("--refresh-keywords", action="store_true")
    parser.add_argument("--add-2017", action="store_true")
    args = parser.parse_args()
    if args.refresh_keywords:
        path = DATA_DIR / "submissions.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        write_outputs(refresh_keywords(payload))
        return
    if args.add_2017:
        path = DATA_DIR / "submissions.json"
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        with path.open(encoding="utf-8") as fh:
            payload = json.load(fh)
        payload = add_2017_to_payload(payload)
        if args.merge_2026:
            payload = merge_2026_into_payload(payload)
        write_outputs(backfill_keyword_fields(payload))
        return
    years = [2024, 2025] if args.quick else args.years
    payload = scrape_all(years)
    if args.merge_2026:
        payload = merge_2026_into_payload(payload)
    write_outputs(backfill_keyword_fields(payload))
    print(f"Done. Scraped {payload['metadata']['total_count']} submissions.")

if __name__ == "__main__":
    main()
