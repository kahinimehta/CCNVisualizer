# Submission Visualizer

Interactive dashboard for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives.

**Live site:** https://ccn-visualizer.vercel.app/

Dashboard UI uses a card-based layout styled with CCN brand colors (navy, pink, blue, green). See **[docs/DASHBOARD.md](docs/DASHBOARD.md)** for layout, filter logic, and component details.

## What it does

- Scrapes CCN archives from `2018.ccneuro.org` through `2025.ccneuro.org`
- Merges provisional **2026** pending posters from `data/ccn-2026-pending-posters.csv`
- Assigns every submission a **primary research theme** from the [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) Google Form (12 meetup topics), plus optional **secondary topics**
- Builds an interactive dashboard where **all charts and filters use primary research themes**:
  - Research theme dropdown filter
  - Submissions over time
  - Research theme ranking and donut
  - Themes over time (annual + cumulative progression)
  - Total by theme and year-over-year change
  - 2026 abstract embedding map (UMAP)
  - Secondary topics cloud
  - Searchable submission list

## Research themes

The 10 themes come from the collaborator embedding pipeline (`scripts/ccn_abstract_clustering.ipynb`). Every paper gets exactly one primary theme; up to three secondary themes may also be assigned.

- **2026:** exact cluster label from `embeddings_2026.json`
- **2018–2025:** inferred by text match against 2026 cluster profiles

## Data sources

| Years | Source |
|-------|--------|
| 2018–2019 | `Papers/AcceptedPapers.html` |
| 2022–2023 | `accepted_papers.html` |
| 2024–2025 | MeetingTrakr poster sessions |
| 2026 (provisional) | `data/ccn-2026-pending-posters.csv` |

## Local development

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py              # scrape + merge 2026 + assign themes
python scripts/scrape_ccn.py --quick      # 2024–2025 only
python scripts/merge_2026_csv.py          # merge/replace 2026 CSV only
python scripts/build_cluster_viz.py       # rebuild 2026 UMAP JSON
python scripts/assign_research_themes.py  # assign primary/secondary themes
```

Serve the dashboard:

```bash
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

### Google Form topics (optional)

When form responses are ready, edit `data/google_topics.json` and copy to `docs/data/google_topics.json`:

```json
{
  "enabled": true,
  "topics": ["Vision", "Memory"],
  "assignments": { "submission-id": "Vision" }
}
```

## Deployment

Pushes to `main` deploy the static `docs/` folder (GitHub Pages / Vercel). Scraping does **not** run on every push — use the **Scrape CCN Data** GitHub Action or run scripts locally.

### Vercel settings

| Setting | Value |
|---------|--------|
| Framework Preset | Other |
| Build Command | *(empty)* |
| Output Directory | `docs` |

## Repository layout

```
scripts/scrape_ccn.py
scripts/merge_2026_csv.py
scripts/build_cluster_viz.py
scripts/assign_research_themes.py
scripts/ccn_abstract_clustering.ipynb
data/ccn-2026-pending-posters.csv
docs/
  index.html
  js/app.js
  css/style.css
  DASHBOARD.md
  data/submissions.json
  data/embeddings_2026.json
  data/google_topics.json
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
