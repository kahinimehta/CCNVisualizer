# CCN Visualizer — guide

Interactive dashboard for CCN poster and paper archives (2017–2026). The live site loads **one file**: `docs/data/abstracts.csv` (mirrored at `data/abstracts.csv` after each build).

## Pipeline

```
ccneuro.org archives
        │
        ▼  scrape.py
  submissions.json
        │
        ▼  build.py
        ├─ drop [GAC update] posters
        ├─ Anthropic Claude → assigned_topics (primary + secondaries)
        ├─ TF-IDF + UMAP → umap_x / umap_y (layout only)
        └─ abstracts.csv
        │
        ▼  dashboard (docs/)
```

| Script | Output |
|--------|--------|
| `scrape.py` | `data/submissions.json` |
| `build.py` | themes, map coords, `data/abstracts.csv` + `docs/data/abstracts.csv` |
| `shared.py` | keyword cleanup, GAC filter, embedding text |

### Rebuild

```bash
pip install -r requirements.txt
cp .env.example .env          # ANTHROPIC_API_KEY (never commit)
python scripts/scrape.py --merge-2026
python scripts/build.py         # classify + UMAP + CSV
```

Useful flags: `--skip-classify` (UMAP/CSV only), `--classify-limit N` (smoke test), `--classify-refresh` (re-classify all), `--merge-2026` (2026 CSV only). If classification stops midway, run `build.py` again to resume from `data/llm_theme_cache.json` — not `--classify-refresh`.

CI/workflows need the `ANTHROPIC_API_KEY` repository secret.

## What the dashboard uses

Runtime source: **`docs/data/abstracts.csv`** only. No API calls, no JSON at load time.

| Column | Role |
|--------|------|
| `year`, `title`, `author`, `authors` | Identity |
| `keywords` | Cleaned author/content keywords |
| `assigned_topics` | 14 themes, pipe-separated (` \| `), primary first |
| `abstract` | Search only |
| `umap_x`, `umap_y` | Embedding map position |
| `source_url`, `poster_number` | Links |

Build-only artifacts (not loaded by the browser): `data/submissions.json`, `data/embeddings_all.json`, `data/google_topics.json`.

## Research themes (14)

The 14 primary research themes were predetermined. They come from responses to the [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) Google Form, as well as manual oversight of the clustering process. **Everything else** is not used; legacy labels are migrated at build time.

Reinforcement learning · Motor control & planning · Naturalistic encoding/decoding · Neural population geometry & dynamics · Decision-making and metacognition · Vision · Perception · Language/auditory neuroscience · AI, LLM, & Neural Networks · Memory · Social cognition & theory of mind · Attention & cognitive control / executive function · Clinical / computational psychiatry · Methods and theory

Names/colors: `docs/js/app.js` (`GOOGLE_FORM_TOPICS`). Override names at build time via `data/google_topics.json`.

## How themes are assigned

**Anthropic Claude** (`claude-opus-4-6` by default) reads title, abstract, keywords, and optional track. Returns one **primary** and up to four **secondaries**. Cached in `data/llm_theme_cache.json` (gitignored).

This is separate from the embedding map — themes are **not** from TF-IDF or cosine similarity.

## Embedding map (UMAP)

Map coordinates are for visualization only:

1. Weighted text (title ×2, abstract ×3, keywords ×1) via `shared.py`
2. TF-IDF → **UMAP** (`n_neighbors=15`, `min_dist=0.12`, cosine distance between TF-IDF vectors)
3. Written to CSV as `umap_x`, `umap_y`

Similar abstracts cluster together; dot **color** is the Claude-assigned **primary** topic.

## Dashboard panels

| Panel | CSV fields |
|-------|------------|
| KPIs | row count, years, themes |
| Submissions over time | `year` |
| Theme ranking | `assigned_topics` |
| Year-over-year change | `assigned_topics` by year |
| Embedding map | `umap_x`, `umap_y`, `assigned_topics` |
| Matching submissions | `title`, `author`, `year`, `assigned_topics`, `source_url` |

Filters: year, theme (matches any assigned topic), full-text search. On phone, chart labels are slightly larger; UMAP taps pick the nearest dot.

## Local preview

```bash
python -m http.server 8080 --directory docs
```

Open http://localhost:8080
