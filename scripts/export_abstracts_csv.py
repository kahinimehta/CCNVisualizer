#!/usr/bin/env python3
"""Export submissions with assigned research themes to CSV."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
OUTPUT_PATH = ROOT / "data" / "abstracts_with_topics.csv"

AFFILIATION_HINTS = (
    "university",
    "college",
    "institute",
    "institut",
    "laboratory",
    "laboratoire",
    "school",
    "center",
    "centre",
    "hospital",
    "department",
    "faculty",
    "academy",
    "google",
    "microsoft",
    "meta",
    "united states",
    "united kingdom",
    "netherlands",
    "germany",
    "france",
    "canada",
    "australia",
    "switzerland",
    "sweden",
    "israel",
    "japan",
    "china",
    "india",
    "singapore",
)


def first_author(authors: str) -> str:
    if not authors:
        return ""
    block = authors.split(";")[0].strip()
    if not block:
        return ""
    parts = [part.strip() for part in block.split(",") if part.strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    tail = parts[1].lower()
    if any(hint in tail for hint in AFFILIATION_HINTS) or re.search(r"\b(states|kingdom|republic)\b", tail):
        return parts[0]
    return parts[0]


def assigned_topics(submission: dict) -> str:
    topics: list[str] = []
    primary = submission.get("primary_theme", "")
    if primary:
        topics.append(primary)
    for topic in submission.get("secondary_topics") or []:
        if topic and topic not in topics:
            topics.append(topic)
    return "; ".join(topics)


def export_csv(payload: dict, output_path: Path) -> int:
    rows = sorted(payload["submissions"], key=lambda item: (item["year"], item.get("title", "").lower()))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["title", "first_author", "year", "topics_assigned"],
        )
        writer.writeheader()
        for submission in rows:
            writer.writerow(
                {
                    "title": submission.get("title", ""),
                    "first_author": first_author(submission.get("authors", "")),
                    "year": submission.get("year", ""),
                    "topics_assigned": assigned_topics(submission),
                }
            )
    return len(rows)


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}. Run scrape_ccn.py first.")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    count = export_csv(payload, OUTPUT_PATH)
    print(f"Wrote {count} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
