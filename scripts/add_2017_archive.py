#!/usr/bin/env python3
"""Scrape CCN 2017 archive and merge into submissions.json."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from scrape_ccn import ROOT, scrape_2017_year, write_outputs

DATA_PATH = ROOT / "data" / "submissions.json"


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing {DATA_PATH}")

    with DATA_PATH.open(encoding="utf-8") as fh:
        payload = json.load(fh)

    submissions_2017 = [asdict(item) for item in scrape_2017_year()]
    kept = [sub for sub in payload.get("submissions", []) if sub.get("year") != 2017]
    payload["submissions"] = submissions_2017 + kept
    payload["metadata"]["total_count"] = len(payload["submissions"])
    payload["metadata"]["years"] = sorted({sub["year"] for sub in payload["submissions"]})

    write_outputs(payload)
    print(f"Merged {len(submissions_2017)} submissions from 2017.")


if __name__ == "__main__":
    main()
