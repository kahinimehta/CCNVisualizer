#!/usr/bin/env python3
"""Rebuild submissions.json using author-provided keywords and reassign themes."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from assign_research_themes import apply_assignments
from merge_2026_csv import merge_into_payload
from scrape_ccn import (
    DOCS_DATA_DIR,
    DATA_DIR,
    Submission,
    compute_stats,
    scrape_meetingtrakr_year,
    serialize_stats,
)

SUBMISSION_FIELDS = {field.name for field in Submission.__dataclass_fields__.values()}

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    source_path = DOCS_DATA_DIR / "submissions.json"
    with source_path.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    legacy_subs: list[Submission] = []
    for row in payload["submissions"]:
        if row["year"] >= 2024:
            continue
        row = {k: v for k, v in dict(row).items() if k in SUBMISSION_FIELDS}
        row["keywords"] = []
        legacy_subs.append(Submission(**row))

    meetingtrakr_subs: list[Submission] = []
    for year in (2024, 2025):
        meetingtrakr_subs.extend(scrape_meetingtrakr_year(year))

    all_submissions = legacy_subs + meetingtrakr_subs
    all_submissions.sort(key=lambda s: (s.year, s.poster_number or "", s.title.lower()))
    stats = compute_stats(all_submissions)
    payload = {
        "metadata": {
            **payload.get("metadata", {}),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "years": sorted({s.year for s in all_submissions}),
            "total_count": len(all_submissions),
            "keyword_source": "author_provided",
        },
        "submissions": [asdict(s) for s in all_submissions],
        "stats": serialize_stats(stats),
    }
    payload = merge_into_payload(payload)

    embeddings_path = DOCS_DATA_DIR / "embeddings_2026.json"
    with embeddings_path.open(encoding="utf-8") as fh:
        embeddings = json.load(fh)
    payload = apply_assignments(payload, embeddings)

    for path in (DATA_DIR / "submissions.json", DOCS_DATA_DIR / "submissions.json"):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")

    with_kw = sum(1 for s in payload["submissions"] if s.get("keywords"))
    print(f"Done: {len(payload['submissions'])} submissions, {with_kw} with author keywords")
    print("keyword_years:", payload["metadata"].get("keyword_years"))
    print("research_theme_method:", payload["metadata"].get("research_theme_method"))


if __name__ == "__main__":
    main()
