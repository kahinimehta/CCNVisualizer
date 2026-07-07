#!/usr/bin/env python3
"""Scrape CCN 2026 poster metadata from ccneuro.org and refresh the pending CSV.

The 2026 site exposes a MeetingTrakr search listing (POST /search-papers/) with
poster board number, title, presenter, and topic area. Public poster detail pages
currently redirect to presenter instructions, so abstracts are carried forward from
the existing CSV when titles match (including fuzzy matches for minor renames).

After running this script, rebuild themes and UMAP locally:

    python scripts/build.py --merge-2026 --classify-refresh

Use --dry-run to preview counts without overwriting the CSV.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "ccn-2026-pending-posters.csv"
BACKUP_DIR = ROOT / "data" / "backups"

BASE_URL = "https://2026.ccneuro.org"
SEARCH_URL = f"{BASE_URL}/search-papers/"
USER_AGENT = "CCNVisualizer/1.0 (academic research; github.com/kahinimehta/ccnvisualizer)"

CSV_FIELDS = [
    "track",
    "or_number",
    "status",
    "title",
    "abstract",
    "primary_area",
    "secondary_area",
]


@dataclass
class ListingRow:
    poster_id: str
    poster_number: str
    title: str
    presenter: str
    topic_area: str


@dataclass
class CsvRow:
    track: str
    or_number: str
    status: str
    title: str
    abstract: str
    primary_area: str
    secondary_area: str

    def as_dict(self) -> dict[str, str]:
        return {
            "track": self.track,
            "or_number": self.or_number,
            "status": self.status,
            "title": self.title,
            "abstract": self.abstract,
            "primary_area": self.primary_area,
            "secondary_area": self.secondary_area,
        }


def normalize_title(title: str) -> str:
    text = re.sub(r"\s+", " ", (title or "").strip().lower())
    return text


def load_existing_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def proceedings_titles(rows: list[dict[str, str]]) -> set[str]:
    titles: set[str] = set()
    for row in rows:
        if (row.get("track") or "").strip() == "Proceedings":
            titles.add(normalize_title(row.get("title", "")))
    return titles


def build_title_index(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    for row in rows:
        key = normalize_title(row.get("title", ""))
        if key:
            index[key] = row
    return index


def match_existing_row(
    title: str,
    *,
    title_index: dict[str, dict[str, str]],
    normalized_keys: list[str],
    cutoff: float,
) -> dict[str, str] | None:
    key = normalize_title(title)
    if key in title_index:
        return title_index[key]

    close = difflib.get_close_matches(key, normalized_keys, n=1, cutoff=cutoff)
    if close:
        return title_index[close[0]]
    return None


def fetch_all_listings(session: requests.Session) -> list[ListingRow]:
    session.get(SEARCH_URL, timeout=45)
    response = session.post(
        SEARCH_URL,
        data={
            "form": "search_form",
            "search_string": "",
            "search_papers": "Entire Paper",
            "submit": "Search",
        },
        timeout=120,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    listings: list[ListingRow] = []

    for tr in soup.select("table.listing tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue
        link = cells[1].find("a", href=re.compile(r"poster/\?id="))
        if not link:
            continue
        href = link.get("href", "")
        match = re.search(r"id=([^&'\"]*)", href)
        poster_id = match.group(1).strip() if match else ""
        poster_number = cells[0].get_text(strip=True)
        listings.append(
            ListingRow(
                poster_id=poster_id or poster_number,
                poster_number=poster_number,
                title=link.get_text(strip=True),
                presenter=cells[2].get_text(strip=True),
                topic_area=cells[3].get_text(strip=True),
            )
        )

    if not listings:
        raise RuntimeError(
            "No poster rows found in search results. "
            "The MeetingTrakr listing may be unavailable."
        )
    return listings


def poster_sort_key(poster_number: str) -> tuple[str, int, str]:
    match = re.match(r"^([A-Za-z]+)(\d+)$", poster_number.strip())
    if match:
        return (match.group(1).upper(), int(match.group(2)), poster_number)
    return (poster_number, 0, poster_number)


def unique_or_number(poster_number: str, poster_id: str) -> str:
    """Board numbers with a session letter prefix are unique; bare numerals repeat across sessions."""
    if re.match(r"^[A-Za-z]+\d+$", poster_number.strip()):
        return poster_number.strip()
    poster_id = poster_id.strip()
    if poster_id and poster_id != poster_number.strip():
        return f"{poster_number.strip()}-{poster_id}"
    return poster_number.strip()


def build_csv_rows(
    listings: list[ListingRow],
    existing_rows: list[dict[str, str]],
    *,
    carryforward_abstracts: bool,
    fuzzy_cutoff: float,
) -> tuple[list[CsvRow], dict[str, int]]:
    title_index = build_title_index(existing_rows)
    normalized_keys = list(title_index)
    proc_titles = proceedings_titles(existing_rows)

    stats = {
        "scraped": len(listings),
        "abstracts_carried": 0,
        "abstracts_missing": 0,
        "fuzzy_title_matches": 0,
        "proceedings": 0,
        "extended_abstracts": 0,
    }

    output: list[CsvRow] = []
    for item in sorted(listings, key=lambda row: poster_sort_key(row.poster_number)):
        is_proceedings = normalize_title(item.title) in proc_titles
        if not is_proceedings and carryforward_abstracts:
            prior = match_existing_row(
                item.title,
                title_index=title_index,
                normalized_keys=normalized_keys,
                cutoff=fuzzy_cutoff,
            )
            if prior and (prior.get("track") or "").strip() == "Proceedings":
                is_proceedings = True

        track = "Proceedings" if is_proceedings else "Extended_Abstracts"
        status = "accepted" if is_proceedings else "pending"
        if is_proceedings:
            stats["proceedings"] += 1
        else:
            stats["extended_abstracts"] += 1

        abstract = ""
        secondary_area = ""
        if carryforward_abstracts:
            prior = match_existing_row(
                item.title,
                title_index=title_index,
                normalized_keys=normalized_keys,
                cutoff=fuzzy_cutoff,
            )
            if prior:
                abstract = (prior.get("abstract") or "").strip()
                secondary_area = (prior.get("secondary_area") or "").strip()
                if normalize_title(prior.get("title", "")) != normalize_title(item.title):
                    stats["fuzzy_title_matches"] += 1
            if abstract:
                stats["abstracts_carried"] += 1
            else:
                stats["abstracts_missing"] += 1

        output.append(
            CsvRow(
                track=track,
                or_number=unique_or_number(item.poster_number, item.poster_id),
                status=status,
                title=item.title,
                abstract=abstract,
                primary_area=item.topic_area,
                secondary_area=secondary_area,
            )
        )

    return output, stats


def backup_csv(path: Path) -> Path | None:
    if not path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUP_DIR / f"ccn-2026-pending-posters.{stamp}.csv"
    shutil.copy2(path, backup_path)
    return backup_path


def write_csv(path: Path, rows: list[CsvRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_dict())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape CCN 2026 poster metadata and refresh data/ccn-2026-pending-posters.csv"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=CSV_PATH,
        help=f"CSV path to write (default: {CSV_PATH.relative_to(ROOT)})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary only; do not overwrite the CSV",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip timestamped backup of the existing CSV",
    )
    parser.add_argument(
        "--no-abstract-carryforward",
        action="store_true",
        help="Do not reuse abstracts from the existing CSV",
    )
    parser.add_argument(
        "--fuzzy-cutoff",
        type=float,
        default=0.86,
        help="Title similarity threshold for abstract carry-forward (0-1)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    print(f"Fetching CCN 2026 listings from {SEARCH_URL}")
    listings = fetch_all_listings(session)
    print(f"  Found {len(listings)} posters/papers")

    existing_rows = load_existing_csv(args.output if args.output.exists() else CSV_PATH)
    rows, stats = build_csv_rows(
        listings,
        existing_rows,
        carryforward_abstracts=not args.no_abstract_carryforward,
        fuzzy_cutoff=args.fuzzy_cutoff,
    )

    print("Summary:")
    print(f"  scraped rows:          {stats['scraped']}")
    print(f"  proceedings:           {stats['proceedings']}")
    print(f"  extended abstracts:    {stats['extended_abstracts']}")
    if not args.no_abstract_carryforward:
        print(f"  abstracts carried:     {stats['abstracts_carried']}")
        print(f"  abstracts missing:     {stats['abstracts_missing']}")
        print(f"  fuzzy title matches:   {stats['fuzzy_title_matches']}")

    if args.dry_run:
        print("Dry run — no files written.")
        return

    backup_path = None
    if not args.no_backup:
        backup_path = backup_csv(args.output)
        if backup_path:
            print(f"Backed up existing CSV to {backup_path.relative_to(ROOT)}")

    write_csv(args.output, rows)
    print(f"Wrote {len(rows)} rows to {args.output.relative_to(ROOT)}")
    print()
    print("Next: rebuild themes and grouping locally")
    print("  python scripts/build.py --merge-2026 --classify-refresh")


if __name__ == "__main__":
    main()
