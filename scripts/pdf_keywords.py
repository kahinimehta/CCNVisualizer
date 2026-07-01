#!/usr/bin/env python3
"""Extract and resolve author keywords from HTML pages and proceedings PDFs."""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

from pypdf import PdfReader

from scrape_ccn import SESSION, clean_text, normalize_author_keywords, parse_keyword_field, resolve_keyword_fields
from topic_features import sanitize_keyword_list, strip_citation_fragments

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
        from scrape_ccn import parse_meetingtrakr_detail

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
