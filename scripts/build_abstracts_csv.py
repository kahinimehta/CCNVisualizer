#!/usr/bin/env python3
"""Build the dashboard CSV from submissions.json + embedding coordinates."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
EMBEDDINGS_PATH = ROOT / "docs" / "data" / "embeddings_2026.json"
OUTPUT_PATHS = (ROOT / "data" / "abstracts.csv", ROOT / "docs" / "data" / "abstracts.csv")

LIST_DELIMITER = " | "

CSV_FIELDS = [
    "id",
    "year",
    "title",
    "first_author",
    "authors",
    "author_keywords",
    "extracted_keywords",
    "abstract",
    "assigned_topics",
    "umap_x",
    "umap_y",
    "source_url",
    "poster_number",
    "cluster_track",
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
    if any(hint in tail for hint in AFFILIATION_HINTS) or re.search(
        r"\b(states|kingdom|republic)\b", tail
    ):
        return parts[0]
    return parts[0]


def join_list(values: list[str]) -> str:
    return LIST_DELIMITER.join(value for value in values if value)


def keyword_fields(submission: dict) -> tuple[list[str], list[str]]:
    """Split stored author vs extracted keywords, with legacy fallbacks for older JSON."""
    author = list(submission.get("author_keywords") or [])
    extracted = list(submission.get("extracted_keywords") or [])
    if author or extracted:
        return author, extracted

    keywords = list(submission.get("keywords") or [])
    year = submission.get("year")
    if year in (2018, 2019):
        return [], keywords
    return keywords, []


def assigned_topics(submission: dict) -> list[str]:
    assigned = list(submission.get("assigned_topics") or [])
    if assigned:
        return assigned
    topics: list[str] = []
    primary = submission.get("primary_theme", "")
    if primary:
        topics.append(primary)
    for topic in submission.get("secondary_topics") or []:
        if topic and topic not in topics:
            topics.append(topic)
    return topics


def embedding_index(embeddings: dict) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for point in embeddings.get("points", []):
        lookup[point["id"]] = point
        if point.get("poster_number"):
            lookup[f"2026-{point['poster_number']}"] = point
    return lookup


def build_rows(payload: dict, embeddings: dict | None = None) -> list[dict[str, str]]:
    embedding_lookup = embedding_index(embeddings or {})
    rows: list[dict[str, str]] = []

    for submission in sorted(
        payload.get("submissions", []),
        key=lambda item: (item.get("year", 0), str(item.get("title", "")).lower()),
    ):
        author_keywords, extracted_keywords = keyword_fields(submission)
        sub_id = submission.get("id", "")
        poster = str(submission.get("poster_number") or "")
        point = embedding_lookup.get(sub_id) or embedding_lookup.get(f"2026-{poster}")

        cluster_track = submission.get("cluster_track") or ""
        if not cluster_track and point:
            cluster_track = point.get("cluster_name", "")

        rows.append(
            {
                "id": sub_id,
                "year": str(submission.get("year", "")),
                "title": submission.get("title", ""),
                "first_author": first_author(submission.get("authors", "")),
                "authors": submission.get("authors", ""),
                "author_keywords": join_list(author_keywords),
                "extracted_keywords": join_list(extracted_keywords),
                "abstract": submission.get("abstract", ""),
                "assigned_topics": join_list(assigned_topics(submission)),
                "umap_x": "" if not point else str(point.get("x", "")),
                "umap_y": "" if not point else str(point.get("y", "")),
                "source_url": submission.get("source_url", ""),
                "poster_number": poster,
                "cluster_track": cluster_track,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {path}")


def build_from_payload(payload: dict, embeddings: dict | None = None) -> list[dict[str, str]]:
    rows = build_rows(payload, embeddings)
    write_csv(rows)
    return rows


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    embeddings = None
    if EMBEDDINGS_PATH.exists():
        with EMBEDDINGS_PATH.open(encoding="utf-8") as fh:
            embeddings = json.load(fh)

    rows = build_from_payload(payload, embeddings)
    print(f"Built {len(rows)} rows")


if __name__ == "__main__":
    main()
