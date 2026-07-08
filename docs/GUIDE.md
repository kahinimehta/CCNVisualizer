# CCN Visualizer — guide

[README](../README.md) · **Live:** https://ccn-visualizer.vercel.app/

The dashboard loads `docs/data/abstracts.csv` (mirrored to `data/abstracts.csv` after each build).

## Pipeline

```
scrape.py  →  submissions.json  →  build.py  →  abstracts.csv  →  docs/
```

| Step | What it does |
|------|----------------|
| **scrape.py** | Pulls 2017–2026 from ccneuro.org archives. 2026 uses the MeetingTrakr search listing on `2026.ccneuro.org` (poster number, title, presenter, topic area). Abstracts are carried forward from prior `submissions.json` when detail pages are unavailable. |
| **build.py** | Drops `[GAC update]` posters; Anthropic Claude assigns `assigned_topics`; TF-IDF + UMAP writes map coordinates; exports CSV. |
| **Deploy** | Push `main` → Vercel serves `docs/`. Commit `docs/data/abstracts.csv` after rebuilds. |

### Commands

```bash
pip install -r requirements.txt
cp .env.example .env
python scripts/scrape.py
python scripts/build.py
python -m http.server 8080 --directory docs
```

Useful `build.py` flags: `--skip-classify` (UMAP/CSV only), `--repair-only` (text cleanup, no API/UMAP), `--classify-limit N`, `--classify-refresh`.

**GitHub Actions** (need `ANTHROPIC_API_KEY`): **Scrape CCN Data** (full/partial rescrape + build), **Update 2026 Data** (rescrape 2026 + build).

Production data was manually cleaned before deployment (text repair, theme spot-checks).

## Themes, keys, and filters

- **14 themes** from the [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) Google Form. Claude assigns dominant + secondary topics at build time (cached as `year:id` in `data/llm_theme_cache.json`).
- **Paper keys:** `year:id` — CCN reuses numeric IDs across years; never key by bare `id` alone.
- **List filter:** matches any assigned topic (dominant or secondary).
- **UMAP map:** dot color and highlight use the dominant topic only (`assigned_topics[0]`).

Build-only artifacts (not loaded in the browser): `data/submissions.json`, `data/embeddings_all.json`, `data/google_topics.json`, `data/llm_theme_cache.json` (gitignored).
