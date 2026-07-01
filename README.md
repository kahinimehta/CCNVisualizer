# Submission Visualizer

Interactive dashboard for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives (2018–2026).

**Live site:** https://ccn-visualizer.vercel.app/

**Dashboard guide:** [docs/DASHBOARD.md](docs/DASHBOARD.md) · **Implementation:** [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)

**Research themes source:** [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) (Google Form question 1)

## Overview

- Archive data (`2018`–`2025`) was scraped once from ccneuro.org and is treated as static
- **2026** posters are merged from `data/ccn-2026-pending-posters.csv` — this is the only data that gets updated going forward
- Research themes are the 12 meetup topics from the [Google Form](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform); submissions can carry **multiple assigned topics** plus a **cluster track** for 2026 audit
- The live dashboard reads **`docs/data/abstracts.csv`** (built from JSON) — one row per submission with author keywords, extracted keywords, abstract, assigned topics, and cluster track

## Dashboard features

| Feature | Description |
|---------|-------------|
| Research theme filter | Dropdown of all 12 Google Form topics with counts |
| Submissions over time | Line chart by conference year |
| Research theme ranking | Horizontal bars, full theme names |
| Themes over time | Annual (solid) + cumulative (dashed) lines per theme |
| Theme totals & YoY change | All-time bars + year-pair delta |
| Abstract embedding map | 2026 UMAP scatter, colored by cluster track; click to filter |
| Matching submissions | Searchable list with assigned topic tags and cluster track |
| Primary themes donut | Share of submissions by primary theme |
| Secondary topics cloud | Frequency of secondary theme tags |

## Research themes

The 12 primary topics come from [**CCN 2026 Activity Preferences**](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1. They are stored in `data/google_topics.json` and `docs/data/google_topics.json`.

| Years | Assignment method |
|-------|-------------------|
| 2025, 2026 | Official CCN topic label → Google theme (`CCN_TOPIC_MAP`) |
| 2018–2024 | Keyword + text scoring; 2026 papers also get a soft embedding-cluster boost |

See [docs/DASHBOARD.md](docs/DASHBOARD.md) for the full topic list, label map, and why Vision skew was fixed.

## Data sources

| Years | Source | Updates? |
|-------|--------|----------|
| 2018–2019 | `Papers/AcceptedPapers.html` | Static |
| 2022–2023 | `accepted_papers.html` | Static |
| 2024–2025 | MeetingTrakr poster sessions | Static |
| 2026 | `data/ccn-2026-pending-posters.csv` | **Replace CSV when new data arrives** |

## Updating 2026 data

When an updated 2026 poster list is available:

1. Replace `data/ccn-2026-pending-posters.csv`
2. Run the update pipeline:

```bash
pip install -r scripts/requirements.txt
python scripts/merge_2026_csv.py
python scripts/build_cluster_viz.py
python scripts/assign_research_themes.py
```

Or trigger the **Update 2026 Data** GitHub Action (Actions → Update 2026 Data → Run workflow).

This refreshes `submissions.json`, `abstracts.csv`, `embeddings_2026.json`, and theme assignments. Commit and push to deploy.

## Initial / full rebuild

To re-scrape the full archive (rarely needed):

```bash
python scripts/scrape_ccn.py              # scrape 2018–2025 + merge 2026 CSV + assign themes
python scripts/build_cluster_viz.py       # 2026 UMAP JSON
python scripts/assign_research_themes.py  # re-assign themes only
```

## Local development

```bash
pip install -r scripts/requirements.txt
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

## Google Form topics

The form link is the canonical source for theme names. If question 1 options change on the form, update the `topics` array in `data/google_topics.json`, copy to `docs/data/google_topics.json`, and re-run `python scripts/assign_research_themes.py`.

No form response data or analytics are used — only the published topic list from the form.

## Deployment

Pushes to `main` deploy the static `docs/` folder (GitHub Pages / Vercel).

### Vercel settings

| Setting | Value |
|---------|--------|
| Framework Preset | Other |
| Build Command | *(empty)* |
| Output Directory | `docs` |

## Repository layout

```
scripts/
  scrape_ccn.py                 # One-time archive scraper
  merge_2026_csv.py             # Merge/replace 2026 CSV (primary update path)
  build_cluster_viz.py          # UMAP export for dashboard
  build_abstracts_csv.py        # Export audit CSV for the dashboard
  assign_research_themes.py     # Google topic assignment + CSV export
  ccn_abstract_clustering.ipynb # Collaborator embedding notebook
data/
  ccn-2026-pending-posters.csv  # Updated when new 2026 data arrives
  google_topics.json            # 12 themes from Google Form Q1
docs/
  index.html
  DASHBOARD.md
  IMPLEMENTATION.md             # Data sources, algorithms, per-chart reference
  js/app.js
  css/style.css
  data/abstracts.csv            # Dashboard source of truth (also in docs/data/)
  data/submissions.json
  data/embeddings_2026.json
  data/google_topics.json
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
