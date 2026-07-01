#!/usr/bin/env python3
"""Extract author keywords from CCN legacy proceedings PDFs."""

from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

from pypdf import PdfReader

from scrape_ccn import SESSION, clean_text, normalize_author_keywords, parse_keyword_field

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "pdf_cache"

PDF_KEYWORD_YEARS = (2018, 2019)


def parse_legacy_pdf_url(html: str, base_url: str) -> str:
    for match in re.finditer(r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']', html, re.I):
        url = match.group(1)
        if "proceedings" in url.lower() or url.lower().endswith(".pdf"):
            return urljoin(base_url, url)

    onclick = re.search(r"window\.open\(['\"]([^'\"]+\.pdf[^'\"]*)['\"]", html, re.I)
    if onclick:
        return urljoin(base_url, onclick.group(1))
    return ""


def normalize_pdf_text(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)
    text = text.replace("\n", " ")
    return re.sub(r"\s+", " ", text)


def parse_keywords_from_pdf_text(text: str) -> list[str]:
    if not text:
        return []

    normalized = normalize_pdf_text(text)
    match = re.search(
        r"\bKeywords?\s*:\s*(.+?)(?:\bIntroduction\b|\b1\s+Introduction\b|\bBackground\b|\Z)",
        normalized,
        re.I | re.S,
    )
    if not match:
        return []

    raw = clean_text(match.group(1))
    if not raw:
        return []
    return normalize_author_keywords(parse_keyword_field(raw))


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


def keywords_from_pdf_url(url: str) -> list[str]:
    if not url:
        return []

    text_cache = _cache_path(url, ".txt")
    if text_cache.exists():
        text = text_cache.read_text(encoding="utf-8")
    else:
        text = extract_pdf_text(fetch_pdf_bytes(url))
        text_cache.write_text(text, encoding="utf-8")

    return parse_keywords_from_pdf_text(text)


def keywords_from_detail_html(html: str, base_url: str) -> list[str]:
    pdf_url = parse_legacy_pdf_url(html, base_url)
    if not pdf_url:
        return []
    return keywords_from_pdf_url(pdf_url)
