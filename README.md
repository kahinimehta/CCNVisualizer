# Submission Visualizer

Interactive keyword and topic visualizations for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives.

**Live site:** [https://kahinimehta.github.io/CCNVisualizer/](https://kahinimehta.github.io/CCNVisualizer/) · [Vercel](https://vercel.com) compatible

Dashboard UI uses a card-based layout inspired by modern analytics dashboards, styled with CCN brand colors (navy, pink, blue, green).

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
scripts/scrape_ccn.py   # Archive scraper
docs/                   # GitHub Pages site
  index.html
  js/app.js
  css/style.css
  data/submissions.json # Generated dataset
data/submissions.json   # Copy of dataset for local use
```

## Licenses

- **Project code:** [MIT License](LICENSE)
- **Dependencies:** [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)
- **In-app attributions:** [docs/licenses.html](docs/licenses.html)
- **Data:** CCN archive metadata from publicly available conference sites; submission content belongs to respective authors.
