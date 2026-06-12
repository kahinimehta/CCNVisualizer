# Submission Visualizer

Interactive keyword and topic visualizations for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives.

**Live site:** [https://https://ccn-visualizer.vercel.app/](https://ccn-visualizer.vercel.app/)
Dashboard UI uses a card-based layout inspired by modern analytics dashboards, styled with CCN brand colors (navy, pink, blue, green).

## What it does

- Scrapes CCN archives from `2018.ccneuro.org` through `2025.ccneuro.org`
- Merges provisional **2026** pending posters from `data/ccn-2026-pending-posters.csv`
- Collects poster/paper titles, authors, abstracts, keywords, and topic areas
- Builds an interactive dashboard with:
  - Keyword cloud (click to filter)
  - Top keyword bar chart
  - Submissions by year
  - Topic area distribution
  - Topics over time (token method; Google Form topics when configured)
  - Largest year-over-year topic shifts
  - 2026 abstract embedding map (UMAP + cluster themes from collaborator pipeline)
  - Searchable submission list

## Data sources

| Years | Source |
|-------|--------|
| 2018–2019 | `Papers/AcceptedPapers.html` |
| 2022–2023 | `accepted_papers.html` |
| 2024–2025 | MeetingTrakr poster sessions (`poster-sessions/?view=all`) |

| 2026 (provisional) | `data/ccn-2026-pending-posters.csv` — merged after scrape; replace file and re-run when updated |

2026 is not yet published on the CCN archive site. Drop in an updated CSV and re-run the merge script (see below).

## Local development

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py          # full scrape (all years) + 2026 CSV merge
python scripts/scrape_ccn.py --quick  # 2024–2025 only
python scripts/merge_2026_csv.py      # merge/replace 2026 CSV only
python scripts/build_cluster_viz.py   # rebuild 2026 UMAP embedding JSON
```

### Google Form topics (optional)

When form responses are ready, edit `data/google_topics.json` and copy to `docs/data/google_topics.json`:

```json
{
  "enabled": true,
  "topics": ["Vision", "Memory", "..."],
  "assignments": { "submission-id": "Vision" }
}
```

Set `enabled: true` once assignments are populated. Until then the dashboard uses the token/topic-area method.

Serve the dashboard locally:

```bash
python -m http.server 8080 --directory docs
```

Open [http://localhost:8080](http://localhost:8080).

## GitHub Pages

Pushes to `main` deploy the committed `docs/` folder as-is (no scraping). To enable Pages: **Settings → Pages → Build and deployment → GitHub Actions**.

### Refresh data (manual only)

Scraping does **not** run on every push. To update submission data:

1. **Locally:** `python scripts/scrape_ccn.py` then commit `data/submissions.json` and `docs/data/submissions.json`
2. **GitHub Actions:** Run the **Scrape CCN Data** workflow (`Actions → Scrape CCN Data → Run workflow`). This commits updated JSON to `main`, which triggers a redeploy.

To deploy without scraping, run **Deploy GitHub Pages** with the scrape option unchecked, or just push UI-only changes to `main`.

## Vercel

This project is a **static site** in `docs/` (not Angular/React). The repo includes `vercel.json` so Vercel serves that folder directly with no build step.

1. Import the GitHub repo in [Vercel](https://vercel.com)
2. Confirm **Framework Preset** is **Other** (or let `vercel.json` override it)
3. Deploy

If a deploy fails with `ng build` exit 127, Vercel guessed the wrong framework. Either merge the `vercel.json` from this repo, or set these in the Vercel project **Settings → Build & Development**:

| Setting | Value |
|---------|--------|
| Framework Preset | Other |
| Build Command | *(empty)* |
| Output Directory | `docs` |
| Install Command | *(empty)* |

## Repository layout

```
scripts/scrape_ccn.py              # Archive scraper
scripts/merge_2026_csv.py          # Merge provisional 2026 CSV
scripts/build_cluster_viz.py       # 2026 embedding UMAP export
scripts/ccn_abstract_clustering.ipynb  # Collaborator clustering notebook
data/ccn-2026-pending-posters.csv  # Provisional 2026 data (replaceable)
data/google_topics.json            # Google Form topic config (pending)
docs/                              # GitHub Pages site
  index.html
  js/app.js
  css/style.css
  data/submissions.json            # Generated dataset
  data/embeddings_2026.json        # 2026 UMAP cluster points
data/submissions.json              # Copy of dataset for local use
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
- **Data:** CCN archive metadata from publicly available conference sites; submission content belongs to respective authors.
