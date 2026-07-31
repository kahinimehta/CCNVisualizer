#!/usr/bin/env python3
"""Restore author keywords from a historical abstracts_2_topics.csv snapshot."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "submissions.json"
CSV_PATH = ROOT / "docs" / "data" / "abstracts_2_topics.csv"
LIST_DELIMITER = " | "

sys.path.insert(0, str(ROOT / "scripts"))
from shared import reconcile_submission_keywords  # noqa: E402


def load_csv_keywords_from_git(commit: str) -> dict[tuple[str, str], list[str]]:
    raw = subprocess.check_output(
        ["git", "show", f"{commit}:{CSV_PATH.relative_to(ROOT)}"],
        text=True,
    )
    keywords: dict[tuple[str, str], list[str]] = {}
    for row in csv.DictReader(StringIO(raw)):
        text = (row.get("keywords") or "").strip()
        if not text:
            continue
        parsed = [part.strip() for part in text.split(LIST_DELIMITER) if part.strip()]
        if parsed:
            keywords[(str(row["year"]), row["id"])] = parsed
    return keywords


def restore_keywords(payload: dict, source: dict[tuple[str, str], list[str]], *, only_empty: bool) -> int:
    restored = 0
    for submission in payload.get("submissions", []):
        key = (str(submission.get("year")), str(submission.get("id")))
        if key not in source:
            continue
        if only_empty and (submission.get("keywords") or submission.get("author_keywords")):
            continue
        submission["author_keywords"] = list(source[key])
        submission["extracted_keywords"] = []
        submission["keywords"] = list(source[key])
        reconcile_submission_keywords(submission)
        restored += 1
    return restored


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-commit",
        default="c3189b0",
        help="Git commit containing the CSV snapshot to restore from",
    )
    parser.add_argument(
        "--overlay-commit",
        action="append",
        default=["1715042"],
        help="Additional commits whose CSV rows override matching year/id entries",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Overwrite existing keywords, not only empty fields",
    )
    args = parser.parse_args()

    source = load_csv_keywords_from_git(args.from_commit)
    for commit in args.overlay_commit:
        source.update(load_csv_keywords_from_git(commit))

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    restored = restore_keywords(payload, source, only_empty=not args.all)
    with DATA_PATH.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"Restored keywords for {restored} submissions from {args.from_commit}.")


if __name__ == "__main__":
    main()
