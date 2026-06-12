# Submission Visualizer

Interactive dashboard for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives (2018–2026).

**Live site:** https://ccn-visualizer.vercel.app/

**Dashboard guide:** [docs/DASHBOARD.md](docs/DASHBOARD.md) — layout, filters, research themes, data pipeline, and `google_topics.json` schema.

## Overview

- Scrapes CCN archives (`2018`–`2025`) and merges provisional **2026** posters from CSV
- Classifies every submission with a **primary research theme** (12 [Google Form](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) meetup topics) plus optional **secondary topics**
- Serves a responsive single-column dashboard (max-width 1080px) where **all charts and filters use primary themes**

## Dashboard features

| Feature | Description |
|---------|-------------|
| Research theme filter | Dropdown of all 12 Google Form topics with counts |
| Submissions over time | Line chart by conference year |
| Research theme ranking | Horizontal bars, full theme names |
| Themes over time | Annual (solid) + cumulative (dashed) lines per theme |
| Theme totals & YoY change | All-time bars + year-pair delta |
| Abstract embedding map | 2026 UMAP scatter, colored by Google topic; click to filter |
| Matching submissions | Searchable list with primary/secondary theme tags |
| Primary themes donut | Share of submissions by primary theme |
| Secondary topics cloud | Frequency of secondary theme tags |

## Research themes

12 primary topics from **CCN 2026 Activity Preferences**, question 1 (meetup affiliation). Configured in `docs/data/google_topics.json`.

| Assignment | Method |
|------------|--------|
| 2026 submissions | Embedding cluster → Google topic (`embedding_cluster_map`) |
| 2018–2025 | Text match against profiles from 2026 cluster data |
| Manual override | `assignments` in `google_topics.json` |

See [docs/DASHBOARD.md](docs/DASHBOARD.md) for the full topic list and cluster mapping table.

## Data sources

| Years | Source |
|-------|--------|
| 2018–2019 | `Papers/AcceptedPapers.html` |
| 2022–2023 | `accepted_papers.html` |
| 2024–2025 | MeetingTrakr poster sessions |
| 2026 (provisional) | `data/ccn-2026-pending-posters.csv` |

2026 CSV is provisional — replace the file and re-run the merge/theme scripts when updated.

## Local development

```bash
pip install -r scripts/requirements.txt

# Full pipeline
python scripts/scrape_ccn.py

# Individual steps
python scripts/scrape_ccn.py --quick      # 2024–2025 only
python scripts/merge_2026_csv.py          # merge/replace 2026 CSV
python scripts/build_cluster_viz.py       # 2026 UMAP JSON
python scripts/assign_research_themes.py  # primary + secondary themes
```

Serve locally:

```bash
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

## Google Form configuration

Topics are already loaded in `data/google_topics.json`. To add per-respondent data or analytics counts later:

1. Download CSV from [form analytics](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewanalytics)
2. Update `assignments` and/or `response_counts` in `data/google_topics.json`
3. Copy to `docs/data/google_topics.json`
4. Run `python scripts/assign_research_themes.py`

## Deployment

Pushes to `main` deploy the static `docs/` folder (GitHub Pages / Vercel). Scraping does **not** run on every push.

**Refresh data:** run the **Scrape CCN Data** GitHub Action, or scrape locally and commit `data/submissions.json` + `docs/data/*`.

### Vercel settings

| Setting | Value |
|---------|--------|
| Framework Preset | Other |
| Build Command | *(empty)* |
| Output Directory | `docs` |

## Repository layout

```
scripts/
  scrape_ccn.py                 # Archive scraper
  merge_2026_csv.py             # 2026 CSV merge
  build_cluster_viz.py          # UMAP export for dashboard
  assign_research_themes.py       # Google topic assignment
  ccn_abstract_clustering.ipynb # Collaborator embedding notebook
data/
  ccn-2026-pending-posters.csv
  google_topics.json
docs/
  index.html
  DASHBOARD.md                  # Dashboard & theme documentation
  js/app.js
  css/style.css
  data/submissions.json
  data/embeddings_2026.json
  data/google_topics.json
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
