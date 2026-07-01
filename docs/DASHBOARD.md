# CCN Submission Visualizer

Interactive exploration of CCN poster and paper archives (2017–2026).

## Data

The live dashboard reads **`data/abstracts.csv`** — one row per submission with:

| Column | Meaning |
|--------|---------|
| `title`, `first_author`, `year`, `authors` | Bibliographic fields |
| `author_keywords` | Keywords authors provided (or 2026 CSV research areas) |
| `extracted_keywords` | Algorithm tokens only when author keywords are unavailable |
| `abstract` | Full abstract text |
| `assigned_topics` | Research themes matched from keywords (multiple allowed, ` \| ` separated) |
| `umap_x`, `umap_y` | Map coordinates for 2026 |
| `cluster_track` | Embedding cluster label for 2026 audit (last column) |

## Filters

- **Year** — all years or a single conference year
- **Research theme** — matches any value in `assigned_topics` for that row
- **Search** — title, authors, abstract, keywords, topics, cluster track
- **Embedding map** — click a cluster track to filter 2026 submissions by `cluster_track`

## Charts

| Panel | What it counts |
|-------|----------------|
| Theme ranking / donut / theme mix | Each assigned topic separately; theme mix shows % share within each year |
| Embedding map | 2026 UMAP layout colored by `cluster_track` |
| Paper list | All assigned topics + cluster track when present |

## Updating data

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py              # rebuild JSON from ccneuro.org
python scripts/add_2017_archive.py       # scrape 2017 proceedings PDFs
python scripts/backfill_pdf_keywords.py  # PDF keywords for 2017-2019, 2022-2023
python scripts/build_abstracts_csv.py     # regenerate abstracts.csv from JSON
```

The scraper also writes `abstracts.csv` automatically after theme assignment.
