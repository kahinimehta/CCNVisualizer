#!/usr/bin/env python3
"""Repair scraped text fields in submissions.json and rewrite abstracts.csv."""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from shared import (  # noqa: E402
    content_keywords,
    normalize_field_text,
    reconcile_submission_keywords,
    repair_submission_text,
    submission_row_key,
)

DATA_PATH = ROOT / "data" / "submissions.json"
EMBEDDING_PATH = ROOT / "data" / "embeddings_all.json"
CSV_OUTPUT_PATHS = (ROOT / "data" / "abstracts.csv", ROOT / "docs" / "data" / "abstracts.csv")
LIST_DELIMITER = " | "

CSV_FIELDS = [
    "id",
    "year",
    "title",
    "author",
    "keywords",
    "assigned_topics",
    "authors",
    "abstract",
    "umap_x",
    "umap_y",
    "source_url",
    "poster_number",
]

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


def join_list(values: list[str]) -> str:
    return LIST_DELIMITER.join(value for value in values if value)


def assigned_topics(submission: dict) -> list[str]:
    topics = list(submission.get("assigned_topics") or [])
    if topics:
        return topics
    primary = submission.get("primary_theme")
    return [primary] if primary else []


def embedding_index(embeddings: dict) -> dict:
    lookup: dict[str, dict] = {}
    for point in embeddings.get("points", []):
        lookup[str(point.get("id", ""))] = point
        if point.get("poster_number"):
            lookup[f"2026-{point['poster_number']}"] = point
    return lookup


def build_csv_rows(payload: dict, embeddings: dict) -> list[dict[str, str]]:
    lookup = embedding_index(embeddings)
    rows: list[dict[str, str]] = []
    for submission in sorted(
        payload.get("submissions", []),
        key=lambda item: (item.get("year", 0), str(item.get("title", "")).lower()),
    ):
        sub_id = submission.get("id", "")
        poster = str(submission.get("poster_number") or "")
        point = lookup.get(submission_row_key(submission)) or lookup.get(f"2026-{poster}")
        authors = submission.get("authors", "")
        rows.append(
            {
                "id": sub_id,
                "year": str(submission.get("year", "")),
                "title": normalize_field_text(submission.get("title", "")),
                "author": normalize_field_text(first_author(authors)),
                "keywords": join_list(content_keywords(submission)),
                "assigned_topics": join_list(assigned_topics(submission)),
                "authors": normalize_field_text(authors),
                "abstract": normalize_field_text(submission.get("abstract", "")),
                "umap_x": "" if not point else str(point.get("x", "")),
                "umap_y": "" if not point else str(point.get("y", "")),
                "source_url": submission.get("source_url", ""),
                "poster_number": poster,
            }
        )
    return rows


def repair_payload(payload: dict) -> dict:
    for submission in payload.get("submissions", []):
        repair_submission_text(submission)
        reconcile_submission_keywords(submission)
    return payload


def write_csv(rows: list[dict[str, str]]) -> None:
    for path in CSV_OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path}")


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    payload = repair_payload(payload)
    DATA_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {DATA_PATH}")

    if EMBEDDING_PATH.exists():
        with EMBEDDING_PATH.open(encoding="utf-8") as fh:
            embeddings = json.load(fh)
    else:
        embeddings = {"points": []}

    write_csv(build_csv_rows(payload, embeddings))
    print(f"Repaired {len(payload.get('submissions', []))} submissions.")


if __name__ == "__main__":
    main()
