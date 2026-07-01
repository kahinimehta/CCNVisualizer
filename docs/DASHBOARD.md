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
| `umap_x`, `umap_y` | Map coordinates for all years (TF-IDF + UMAP on title + abstract) |

There is **one topic system** — the 12 CCN 2026 Activity Preferences research themes. Older separate “embedding cluster” labels (e.g. *Visual Cortex Models*) are no longer shown; they were machine clusters that duplicated the same theme vocabulary.

## Keyword priority

For every submission we prefer **author-provided keywords** in this order:

1. **Poster / paper HTML** — `Keywords:` field on MeetingTrakr pages (2024–2025)
2. **Proceedings or authored PDF** — keyword line parsed from linked PDFs (2017–2025)
3. **2026 CSV** — `primary_area` / `secondary_area`
4. **`extracted_keywords`** — title/abstract token fallback only when steps 1–3 find nothing

## Filters

- **Year** — all years or a single conference year
- **Research theme** — matches any value in `assigned_topics` for that row
- **Search** — title, authors, abstract, keywords, assigned topics
- **Embedding map** — shows submissions that pass the same filters; topic dropdown filters by any assigned topic

## Charts

| Panel | What it counts |
|-------|----------------|
| Theme ranking / year-over-year change | Each assigned topic separately; submissions can appear in multiple topics |
| Embedding map | All years; each dot is a **pie slice per assigned topic** (same colors as legend) |
| Paper list | Colored topic tags only (no separate cluster line) |

## Updating data

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py              # rebuild JSON from ccneuro.org
python scripts/backfill_pdf_keywords.py   # refresh author keywords from HTML + PDFs
python scripts/assign_research_themes.py  # assign Google Form topics
python scripts/build_all_embeddings.py    # UMAP coordinates for all years
python scripts/build_abstracts_csv.py     # regenerate abstracts.csv from JSON
```

The scraper runs keyword enrichment automatically; use `backfill_pdf_keywords.py` after JSON changes to re-fetch PDF keyword lines and reassign themes.
