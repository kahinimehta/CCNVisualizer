#!/usr/bin/env python3
"""Merge provisional CCN 2026 poster CSV into submissions.json."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from dataclasses import asdict, fields

from scrape_ccn import Submission, compute_stats, resolve_keyword_fields, serialize_stats

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "ccn-2026-pending-posters.csv"
DATA_PATH = ROOT / "data" / "submissions.json"
DOCS_PATH = ROOT / "docs" / "data" / "submissions.json"
YEAR = 2026
SUBMISSION_FIELDS = {field.name for field in fields(Submission)}


def submission_from_dict(item: dict) -> Submission:
    return Submission(**{key: value for key, value in item.items() if key in SUBMISSION_FIELDS})


def normalize_topic_area(primary: str, secondary: str = "") -> str:
    parts = [p.strip() for p in re.split(r"[+;,]", f"{primary},{secondary}") if p.strip()]
    if not parts:
        return ""
    return parts[0].lower()


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
    topic_area = normalize_topic_area(primary, secondary)
    track = (row.get("track") or "").strip()
    author_keywords, extracted_keywords, keywords = resolve_keyword_fields(
        author_keywords=author_keywords_from_csv(row),
        topic_area=topic_area,
    )

    return Submission(
        id=f"2026-{poster or title[:24]}",
        year=YEAR,
        title=title,
        authors="",
        abstract=abstract,
        author_keywords=author_keywords,
        extracted_keywords=extracted_keywords,
        keywords=keywords,
        topic_area=topic_area,
        track=track,
        poster_number=poster,
        source_url="https://2026.ccneuro.org/",
        submission_type="poster",
    )


def load_csv_submissions() -> list[Submission]:
    if not CSV_PATH.exists():
        print(f"No 2026 CSV at {CSV_PATH}; skipping merge.")
        return []

    with CSV_PATH.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    submissions = [csv_row_to_submission(row) for row in rows if (row.get("title") or "").strip()]
    print(f"Loaded {len(submissions)} submissions from {CSV_PATH.name}")
    return submissions


def merge_into_payload(payload: dict) -> dict:
    csv_submissions = load_csv_submissions()
    if not csv_submissions:
        return payload

    kept_dicts = [s for s in payload.get("submissions", []) if s.get("year") != YEAR]
    submission_objs = [submission_from_dict(item) for item in kept_dicts] + csv_submissions

    stats = compute_stats(submission_objs)
    years = sorted({s.year for s in submission_objs})

    payload["submissions"] = [asdict(s) for s in submission_objs]
    payload["stats"] = serialize_stats(stats)
    payload["metadata"]["total_count"] = len(submission_objs)
    payload["metadata"]["years"] = years
    payload["metadata"]["source"] = "https://ccneuro.org archives (2018-2025) + 2026 pending CSV"
    payload["metadata"]["csv_2026"] = {
        "path": str(CSV_PATH.relative_to(ROOT)),
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "count": len(csv_submissions),
        "note": "Provisional — replace CSV and re-run merge when updated data is available.",
    }
    return payload


def write_payload(payload: dict) -> None:
    for path in (DATA_PATH, DOCS_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"Wrote {path}")


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}. Run scrape_ccn.py first.")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    payload = merge_into_payload(payload)
    write_payload(payload)
    print(f"Done. Total submissions: {payload['metadata']['total_count']}")


if __name__ == "__main__":
    main()
