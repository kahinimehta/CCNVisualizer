#!/usr/bin/env python3
"""Backfill author keywords from proceedings PDFs and refresh theme assignments."""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from assign_research_themes import apply_assignments, write_payload
from build_abstracts_csv import build_from_payload
from pdf_keywords import PDF_KEYWORD_YEARS, keywords_from_detail_html, keywords_from_pdf_url
from scrape_ccn import ROOT, fetch, resolve_keyword_fields

DATA_PATH = ROOT / "data" / "submissions.json"
EMBEDDINGS_PATH = ROOT / "docs" / "data" / "embeddings_2026.json"


def update_submission(submission: dict) -> tuple[str, bool, int]:
    year = submission.get("year")
    if year not in PDF_KEYWORD_YEARS:
        return submission.get("id", ""), False, 0

    pdf_keywords: list[str] = []
    source_url = submission.get("source_url", "")
    try:
        if year == 2017 and source_url.lower().endswith(".pdf"):
            pdf_keywords = keywords_from_pdf_url(source_url)
        elif source_url:
            base_url = f"https://{year}.ccneuro.org/"
            detail_html = fetch(source_url)
            pdf_keywords = keywords_from_detail_html(detail_html, base_url)
    except Exception:
        pdf_keywords = []

    if pdf_keywords:
        submission["author_keywords"] = pdf_keywords
        submission["extracted_keywords"] = []
        submission["keywords"] = pdf_keywords
        return submission.get("id", ""), True, len(pdf_keywords)

    author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
        author_keywords=[],
        topic_area=submission.get("topic_area", ""),
        track=submission.get("track", ""),
        title=submission.get("title", ""),
        abstract=submission.get("abstract", ""),
    )
    submission["author_keywords"] = author_keywords
    submission["extracted_keywords"] = extracted_keywords
    submission["keywords"] = keywords
    return submission.get("id", ""), False, 0


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    targets = [sub for sub in payload["submissions"] if sub.get("year") in PDF_KEYWORD_YEARS]
    print(f"Fetching PDF keywords for {len(targets)} submissions ({PDF_KEYWORD_YEARS})")

    updated = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(update_submission, sub): sub for sub in targets}
        for index, future in enumerate(as_completed(futures), start=1):
            _, from_pdf, _ = future.result()
            if from_pdf:
                updated += 1
            if index % 50 == 0 or index == len(targets):
                print(f"  processed {index}/{len(targets)} ({updated} from PDF)")

    payload["metadata"]["keyword_source"] = (
        "author_keywords from poster pages, proceedings PDFs (2017-2019, 2022-2023), or 2026 CSV; "
        "else official topic/track labels; else title/abstract tokens only when PDF/HTML keywords missing"
    )

    embeddings = None
    if EMBEDDINGS_PATH.exists():
        with EMBEDDINGS_PATH.open(encoding="utf-8") as fh:
            embeddings = json.load(fh)
        payload = apply_assignments(payload, embeddings)

    write_payload(payload)
    build_from_payload(payload, embeddings)
    print(f"Done. PDF keywords for {updated}/{len(targets)} submissions.")


if __name__ == "__main__":
    main()
