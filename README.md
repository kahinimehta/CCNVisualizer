# Submission Visualizer

Interactive dashboard for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives (2017–2026).

**Live site:** https://ccn-visualizer.vercel.app/

**Documentation:** [docs/DASHBOARD.md](docs/DASHBOARD.md) (user guide) · [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) (workflow & algorithms)

**Research themes source:** [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) (Google Form question 1)

## Overview

- Archive data (`2017`–`2025`) was scraped once from ccneuro.org and is treated as static
- **2026** posters are merged from `data/ccn-2026-pending-posters.csv` — the main data that gets updated going forward
- Research themes are the 12 meetup topics from the [Google Form](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform); submissions can carry **multiple assigned topics**
- The live dashboard reads **`docs/data/abstracts.csv` only** — one row per submission with keywords, assigned topics, UMAP coordinates, and links

## Data pipeline

```
scrape.py → submissions.json → build.py → abstracts.csv → dashboard
                                  ├── embeddings_all.json (UMAP coords → merged into CSV)
                                  └── submissions.json (updated with assigned_topics)
```

See [docs/DASHBOARD.md](docs/DASHBOARD.md) and [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) for the full workflow and clustering algorithm.

## Dashboard features

| Feature | Description |
|---------|-------------|
| KPI summary | Total submissions, filtered count, theme count, years covered |
| Research theme filter | Header dropdown — all 12 Google Form topics |
| Submissions over time | Line chart by conference year |
| Research theme ranking | Horizontal bars; multi-label counts |
| Year-over-year change | Theme share delta between two selected years |
| Abstract embedding map | All-years UMAP scatter; dot color = primary topic; click for all topics |
| Matching submissions | Searchable list with assigned topic tags |

## Research themes

The 12 topics come from [**CCN 2026 Activity Preferences**](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1. Optional build-time override: `data/google_topics.json`.

| Years | Keyword source |
|-------|----------------|
| 2017–2025 | Poster HTML `Keywords:` field and/or proceedings PDF keyword line |
| 2026 | CSV `primary_area` / `secondary_area` |
| Any year (fallback) | Title/abstract tokens when author keywords unavailable |

## Updating data

### 2026-only update

1. Replace `data/ccn-2026-pending-posters.csv`
2. Run:

```bash
pip install numpy scikit-learn umap-learn
python scripts/build.py --merge-2026
```

Or trigger the **Update 2026 Data** GitHub Action.

### Full rebuild

```bash
pip install requests beautifulsoup4 lxml pypdf numpy scikit-learn umap-learn
python scripts/scrape.py --merge-2026
python scripts/scrape.py --refresh-keywords   # optional keyword refresh
python scripts/build.py
```

Or trigger **Scrape CCN Data** (workflow dispatch).

Both paths refresh `submissions.json`, `embeddings_all.json`, `abstracts.csv`, and theme assignments.

## Local development

```bash
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
  scrape.py                     # Step 1: scrape archives → submissions.json
  build.py                      # Step 2: themes + UMAP + abstracts.csv
data/
  ccn-2026-pending-posters.csv  # Provisional 2026 poster list
  google_topics.json            # Optional theme name override (build time)
  submissions.json              # Build artifact (not loaded by dashboard)
  embeddings_all.json           # UMAP coords (merged into CSV)
  abstracts.csv
docs/
  data/abstracts.csv            # Dashboard runtime source of truth
  js/app.js                       # Dashboard logic; GOOGLE_FORM_TOPICS + colors
  DASHBOARD.md                    # User guide
  IMPLEMENTATION.md               # Workflow & algorithm reference
.github/workflows/
  update-2026-data.yml            # 2026 CSV merge + theme/CSV rebuild
  scrape-data.yml                 # Full archive scrape
  scrape-and-deploy.yml           # GitHub Pages deploy
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
