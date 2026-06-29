#!/usr/bin/env python3
"""Rebuild submissions.json with per-year keyword resolution and reassign themes."""

from __future__ import annotations

from scrape_ccn import scrape_all, write_outputs


def main() -> None:
    payload = write_outputs(scrape_all())

    with_kw = sum(1 for s in payload["submissions"] if s.get("keywords"))
    by_year: dict[int, int] = {}
    for sub in payload["submissions"]:
        if sub.get("keywords"):
            by_year[sub["year"]] = by_year.get(sub["year"], 0) + 1
    print(f"Done: {len(payload['submissions'])} submissions, {with_kw} with keywords")
    print("keyword years:", dict(sorted(by_year.items())))
    print("research_theme_method:", payload["metadata"].get("research_theme_method"))


if __name__ == "__main__":
    main()
