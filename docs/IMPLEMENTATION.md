# Dashboard implementation

Technical reference for the CCN Visualizer data pipeline and dashboard.

## Architecture

The browser loads **one file**: `abstracts.csv`. Theme names and colors are hardcoded in `app.js` as `GOOGLE_FORM_TOPICS`.

```
CCN archives + 2026 CSV
        │
        ▼  scrape.py
  submissions.json
        │
        ▼  build.py
        ├── filter GAC update posters
        ├── Anthropic Claude → primary + secondary assigned_topics
        ├── UMAP (TF-IDF text → 2D coordinates)
        └── abstracts.csv
        │
        ▼  dashboard (docs/)
   reads abstracts.csv only
```

## Scripts

| Script | Role |
|--------|------|
| `scrape.py` | Scrape CCN archives, merge 2026 CSV, refresh keywords → `submissions.json` |
| `build.py` | Anthropic theme classification, UMAP, CSV export |
| `shared.py` | Shared keyword cleanup, mojibake repair, embedding text, GAC exclusion |

### Excluded content

**GAC update posters** (Generative Adversarial Collaboration follow-ups, e.g. 2024 titles starting with `[GAC update]`) are dropped in `scrape.py` and again in `build.py`. They are not counted in charts or the submission list.

### scrape.py flags

- `--merge-2026` — merge provisional 2026 poster CSV
- `--refresh-keywords` — re-extract keywords from HTML/PDF on existing JSON
- `--add-2017` — re-scrape 2017 proceedings and merge
- `--years` / `--quick` — limit scrape scope

### build.py flags

- `--merge-2026` — merge 2026 CSV before building
- `--classify-limit N` — only call Anthropic for first N uncached submissions
- `--classify-refresh` — ignore LLM cache
- `--skip-classify` — skip Anthropic; reuse existing `assigned_topics` in JSON (UMAP + CSV only)

Shared config: **`data/google_topics.json`** — optional override for the 14 theme names at build time.

## Theme assignment (Anthropic Claude)

Default model: **`claude-opus-4-6`** (override with `ANTHROPIC_MODEL`).

For each submission, Claude receives title, abstract, keywords, and optional conference track. It returns JSON:

```json
{"primary_theme": "...", "secondary_topics": ["...", "..."]}
```

Rules encoded in the system prompt:

- Exactly **one primary** — best-fit category from the 14 allowed topics
- **0–4 secondaries** — all other clearly applicable categories
- No catch-all category; invalid or legacy `Everything else` labels are migrated at build time

Results are cached in **`data/llm_theme_cache.json`** (gitignored). Re-runs only API-call submission IDs not in cache.

If classification stops midway, run `python scripts/build.py` again to resume from cache. Use `--classify-refresh` only when you want to discard cached labels and re-classify everything.

### API key

Never commit keys. Use `.env` locally (`ANTHROPIC_API_KEY`) or a repository secret in CI.

## UMAP map coordinates

Independent of theme labels. `build.py` projects submissions into 2D for the dashboard map:

1. Weighted text via `submission_embedding_text()` in `shared.py` (title ×2, abstract ×3, keywords ×1)
2. TF-IDF vectorization + **UMAP** (`n_neighbors=15`, `min_dist=0.12`, cosine metric)
3. Coordinates written to `data/embeddings_all.json` and merged into `abstracts.csv` as `umap_x`, `umap_y`

The map shows semantic neighborhoods — similar language clusters together regardless of assigned theme.

## CSV schema

`abstracts.csv` columns:

| Column | Description |
|--------|-------------|
| `id`, `year`, `title`, `author`, `authors` | Identity |
| `keywords` | Cleaned author/content keywords |
| `assigned_topics` | Primary first, then secondaries (` \| ` delimiter) |
| `abstract` | Full abstract text |
| `umap_x`, `umap_y` | Map coordinates |
| `source_url`, `poster_number` | Links / poster IDs |

## Dashboard behavior

- Dot **color** = primary topic (`assigned_topics[0]`)
- Click/tap a dot → scroll to submission, show all assigned topics
- Theme filter matches any value in `assigned_topics`
- **Phone layout** (<640px): chart axis and theme labels use slightly larger type; UMAP uses nearest-point tap (small hit radius) so dense dots are easier to select accurately

## Dependencies

| Script | Packages |
|--------|----------|
| `scrape.py` | `requests`, `beautifulsoup4`, `lxml`, `pypdf` |
| `build.py` | `numpy`, `scikit-learn`, `umap-learn`, `anthropic`, `python-dotenv` |

Install all: `pip install -r requirements.txt`
