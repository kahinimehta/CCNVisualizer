#!/usr/bin/env python3
"""Refresh author keywords from HTML pages and proceedings PDFs."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from assign_research_themes import apply_assignments, write_payload
from build_abstracts_csv import build_from_payload
from pdf_keywords import KEYWORD_SOURCE_NOTE, enrich_submission_keywords, needs_pdf_keyword_refresh
from scrape_ccn import ROOT, fetch

DATA_PATH = ROOT / "data" / "submissions.json"


def refresh_submission(submission: dict) -> tuple[str, bool]:
    had_author = bool(submission.get("author_keywords"))
    if needs_pdf_keyword_refresh(submission):
        try:
            detail_html = fetch(submission["source_url"])
        except Exception:
            detail_html = None
        enrich_submission_keywords(submission, detail_html=detail_html, try_pdf=True)
    else:
        enrich_submission_keywords(submission, try_pdf=False)
    gained_author = bool(submission.get("author_keywords")) and not had_author
    return submission.get("id", ""), gained_author


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    submissions = payload.get("submissions", [])
    pdf_targets = [sub for sub in submissions if needs_pdf_keyword_refresh(sub)]
    print(f"Refreshing keywords for {len(submissions)} submissions ({len(pdf_targets)} need PDF lookup)")

    updated = 0
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(refresh_submission, sub): sub for sub in submissions}
        for index, future in enumerate(as_completed(futures), start=1):
            _, gained_author = future.result()
            if gained_author:
                updated += 1
            if index % 100 == 0 or index == len(submissions):
                print(f"  processed {index}/{len(submissions)} ({updated} gained author keywords)")

    payload["metadata"]["keyword_source"] = KEYWORD_SOURCE_NOTE
    payload = apply_assignments(payload)
    write_payload(payload)
    build_from_payload(payload)
    print(f"Done. {updated} submissions now have author keywords from HTML/PDF.")


if __name__ == "__main__":
    main()
