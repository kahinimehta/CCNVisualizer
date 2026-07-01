# Submission Visualizer

Interactive dashboard for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives (2017–2026).

**Live site:** https://ccn-visualizer.vercel.app/

**Dashboard guide:** [docs/DASHBOARD.md](docs/DASHBOARD.md) · **Implementation:** [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)

**Research themes source:** [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) (Google Form question 1)

## Overview

- Archive data (`2017`–`2025`) was scraped once from ccneuro.org and is treated as static
- **2026** posters are merged from `data/ccn-2026-pending-posters.csv` — the main data that gets updated going forward
- Research themes are the 12 meetup topics from the [Google Form](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform); submissions can carry **multiple assigned topics**
- The live dashboard reads **`docs/data/abstracts.csv` only** — one row per submission with keywords, assigned topics, UMAP coordinates, and links

## Data pipeline

```
scrape → submissions.json → assign_research_themes.py → abstracts.csv → dashboard
```

See [docs/DASHBOARD.md](docs/DASHBOARD.md) and [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) for the full workflow and clustering algorithm.

## Dashboard features

| Feature | Description |
|---------|-------------|
| Research theme filter | Dropdown of all 12 Google Form topics |
| Submissions over time | Line chart by conference year |
| Research theme ranking | Horizontal bars, full theme names |
| Year-over-year change | Theme share delta between two years |
| Abstract embedding map | All-years UMAP scatter; dot color = primary topic |
| Matching submissions | Searchable list with assigned topic tags |

## Research themes

The 12 topics come from [**CCN 2026 Activity Preferences**](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1. Optional override list: `data/google_topics.json`.

| Years | Keyword source |
|-------|----------------|
| 2017–2025 | Poster HTML `Keywords:` field and/or proceedings PDF keyword line |
| 2026 | CSV `primary_area` / `secondary_area` |
| Any year (fallback) | Title/abstract tokens when author keywords unavailable |

## Updating 2026 data

When an updated 2026 poster list is available:

1. Replace `data/ccn-2026-pending-posters.csv`
2. Run:

```bash
pip install -r scripts/requirements.txt
python scripts/merge_2026_csv.py
python scripts/assign_research_themes.py
```

Or trigger the **Update 2026 Data** GitHub Action.

This refreshes `submissions.json`, `embeddings_all.json`, `abstracts.csv`, and theme assignments.

## Initial / full rebuild

```bash
python scripts/scrape_ccn.py
python scripts/backfill_pdf_keywords.py   # optional keyword refresh
python scripts/assign_research_themes.py
```

## Local development

```bash
pip install -r scripts/requirements.txt
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

## Deployment

Pushes to `main` deploy the static `docs/` folder (GitHub Pages / Vercel).

| Setting | Value |
|---------|--------|
| Framework Preset | Other |
| Build Command | *(empty)* |
| Output Directory | `docs` |

## Repository layout

```
scripts/
  scrape_ccn.py               # Archive scraper
  merge_2026_csv.py             # Merge/replace 2026 CSV
  pdf_keywords.py               # Keyword resolution (HTML → PDF → fallback)
  backfill_pdf_keywords.py      # Refresh keywords for all years
  assign_research_themes.py     # Theme assignment + UMAP + CSV export
  build_all_embeddings.py       # UMAP coordinates (embeddings_all.json)
  build_abstracts_csv.py        # Dashboard CSV export
  topic_features.py             # Text weighting, stoplists, topic anchors
data/
  ccn-2026-pending-posters.csv
  google_topics.json            # Optional theme name override
  submissions.json              # Build artifact (not loaded by dashboard)
  embeddings_all.json           # UMAP coords (merged into CSV)
  abstracts.csv
docs/
  data/abstracts.csv            # Dashboard runtime source of truth
  js/app.js
  DASHBOARD.md
  IMPLEMENTATION.md
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
