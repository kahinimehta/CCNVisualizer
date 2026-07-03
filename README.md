# CCN Visualizer

Interactive dashboard for poster and paper submissions across the [Cognitive Computational Neuroscience (CCN)](https://ccneuro.org) conference archives (2017–2026).

**Live site:** https://ccn-visualizer.vercel.app/

**Documentation:** [docs/DASHBOARD.md](docs/DASHBOARD.md) · [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)

## Pipeline

```
scrape.py  →  submissions.json  →  build.py  →  abstracts.csv  →  dashboard
   │                                    │
   scrape CCN archives                  ├─ Anthropic Claude (themes)
                                        ├─ UMAP (map coordinates)
                                        └─ abstracts.csv export
```

1. **`scripts/scrape.py`** — scrape CCN archives → `data/submissions.json` (excludes `[GAC update]` posters)
2. **`scripts/build.py`** — classify themes with **Anthropic Claude**, compute UMAP, write `abstracts.csv` (also filters GAC updates)
3. **Dashboard** — reads `docs/data/abstracts.csv` only (static site in `docs/`)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY (never commit .env)
```

## Updating data

### Full rebuild

```bash
python scripts/scrape.py --merge-2026
python scripts/scrape.py --refresh-keywords   # optional
python scripts/build.py
```

### 2026-only update

Replace `data/ccn-2026-pending-posters.csv`, then:

```bash
python scripts/build.py --merge-2026
```

### Anthropic API key (required for `build.py`)

| Where | How |
|-------|-----|
| **Local** | `cp .env.example .env` → set `ANTHROPIC_API_KEY` (`.env` is gitignored) |
| **GitHub Actions** | Repository secret `ANTHROPIC_API_KEY` |
| **Cloud agent** | Environment secret / `.env` on the machine |

Optional env vars:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-opus-4-6` | Model for theme classification |
| `LLM_THEME_STRICT` | off | Exit on first classification failure |

Build flags:

```bash
python scripts/build.py                          # classify + UMAP + CSV
python scripts/build.py --classify-limit 5       # smoke test (5 API calls)
python scripts/build.py --classify-refresh       # ignore cache, re-classify
python scripts/build.py --skip-classify          # UMAP + CSV only (reuse existing topics)
```

Classifications are cached in `data/llm_theme_cache.json` (gitignored). Re-runs only API-call new submission IDs. If a full classify run stops midway, resume with plain `python scripts/build.py` — do **not** use `--classify-refresh` unless you intend to re-pay for every submission.

**Cost note:** ~2,965 submissions ≈ one API call each on a full classify. Check [Anthropic pricing](https://www.anthropic.com/pricing) before a full run.

## Research themes

14 topics from [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform), question 1 (excluding the form’s “Everything else” option). Names in `data/google_topics.json`; colors in `docs/js/app.js`.

Claude assigns **one primary** theme plus **all other applicable** secondaries per submission.

## Local development

```bash
python -m http.server 8080 --directory docs
```

Open http://localhost:8080

## Repository layout

```
scripts/
  scrape.py          # Step 1: scrape → submissions.json
  build.py           # Step 2: Anthropic themes + UMAP + abstracts.csv
  shared.py          # Text cleanup, GAC exclusion, embedding text helpers
data/
  submissions.json      # Scraped records (intermediate)
  embeddings_all.json   # Optional UMAP debug artifact (not used by dashboard)
  llm_theme_cache.json  # Anthropic cache (gitignored)
  abstracts.csv           # Local mirror of dashboard CSV
docs/
  data/abstracts.csv    # Dashboard runtime source of truth
  js/app.js          # GOOGLE_FORM_TOPICS + colors
.env.example         # Template for ANTHROPIC_API_KEY
requirements.txt
```

## Deployment

Pushes to `main` deploy the static `docs/` folder (GitHub Pages / Vercel). Build pipeline runs separately (locally or in CI with `ANTHROPIC_API_KEY`).
