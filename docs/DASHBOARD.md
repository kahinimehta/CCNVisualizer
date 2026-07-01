# CCN Submission Visualizer

Interactive exploration of CCN poster and paper archives (2017–2026).

## Data

The live dashboard reads **`data/abstracts.csv`** — one row per submission with:

| Column | Meaning |
|--------|---------|
| `title`, `first_author`, `year`, `authors` | Bibliographic fields |
| `author_keywords` | Author-provided keywords (poster HTML, proceedings/authored PDF, or 2026 CSV areas) |
| `extracted_keywords` | Algorithmic title/abstract tokens only when no author keywords exist |
| `abstract` | Full abstract text |
| `assigned_topics` | Research themes matched from keywords (multiple allowed, ` \| ` separated) |
| `umap_x`, `umap_y` | Map coordinates for 2026 |
| `cluster_track` | Embedding cluster label for 2026 audit (last column) |

## Keyword priority

For every submission we prefer **author-provided keywords** in this order:

1. **Poster / paper HTML** — `Keywords:` field on MeetingTrakr pages (2024–2025)
2. **Proceedings or authored PDF** — keyword line parsed from linked PDFs (2017–2025)
3. **2026 CSV** — `primary_area` / `secondary_area`
4. **`extracted_keywords`** — title/abstract token fallback only when steps 1–3 find nothing

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
python scripts/backfill_pdf_keywords.py  # refresh author keywords from HTML + PDFs
python scripts/build_abstracts_csv.py     # regenerate abstracts.csv from JSON
```

The scraper runs keyword enrichment automatically; use `backfill_pdf_keywords.py` after JSON changes to re-fetch PDF keyword lines and reassign themes.
