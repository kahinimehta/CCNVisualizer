# CCN Visualizer

Interactive keyword and topic visualizations for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives.

**Live site:** [https://kahinimehta.github.io/ccnvisualizer/](https://kahinimehta.github.io/ccnvisualizer/)

## What it does

- Scrapes CCN archives from `2018.ccneuro.org` through `2025.ccneuro.org`
- Collects poster/paper titles, authors, abstracts, keywords, and topic areas
- Builds an interactive dashboard with:
  - Keyword cloud (click to filter)
  - Top keyword bar chart
  - Submissions by year
  - Topic area distribution
  - Keyword co-occurrence network (draggable)
  - Searchable submission list

## Data sources

| Years | Source |
|-------|--------|
| 2018–2019 | `Papers/AcceptedPapers.html` |
| 2022–2023 | `accepted_papers.html` |
| 2024–2025 | MeetingTrakr poster sessions (`poster-sessions/?view=all`) |

2026 submissions are not yet available on the CCN site. The scraper can be re-run after they are published.

## Local development

```bash
pip install -r scripts/requirements.txt
python scripts/scrape_ccn.py          # full scrape (all years)
python scripts/scrape_ccn.py --quick  # 2024–2025 only
```

Serve the dashboard locally:

```bash
python -m http.server 8080 --directory docs
```

Open [http://localhost:8080](http://localhost:8080).

## GitHub Pages

The site is deployed from the `docs/` folder via GitHub Actions (`.github/workflows/scrape-and-deploy.yml`). The workflow:

1. Scrapes the latest CCN archive data
2. Writes `docs/data/submissions.json`
3. Deploys to GitHub Pages

To enable Pages manually: **Settings → Pages → Build and deployment → GitHub Actions**.

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
scripts/scrape_ccn.py   # Archive scraper
docs/                   # GitHub Pages site
  index.html
  js/app.js
  css/style.css
  data/submissions.json # Generated dataset
data/submissions.json   # Copy of dataset for local use
```

## License

Data is sourced from publicly available CCN conference archives. Code in this repository is provided for academic exploration and visualization.
