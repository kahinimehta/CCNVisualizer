# CCN Visualizer — guide

Technical reference for the pipeline, data, and dashboard. **Entry point:** [README](../README.md) · **Live site:** https://ccn-visualizer.vercel.app/

Runtime loads one file: `docs/data/abstracts.csv` (mirrored at `data/abstracts.csv` after each build).

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
| `shared.py` | keyword cleanup, GAC filter, embedding text, `year:id` row keys |

### Rebuild & flags

Basic setup: [README](../README.md). Useful `build.py` flags:

| Flag | Purpose |
|------|---------|
| `--skip-classify` | UMAP/CSV only; keep existing `assigned_topics` |
| `--classify-limit N` | Smoke test (first N uncached rows) |
| `--classify-refresh` | Re-classify all (avoid after cache migration) |
| `--merge-2026` | Merge `data/ccn-2026-pending-posters.csv` before build |

If classification stops midway, run `build.py` again to resume from `data/llm_theme_cache.json`.

**Deploy:** push to `main` → Vercel serves `docs/`. Data changes must be committed separately (local rebuild or GitHub Actions below).

**GitHub Actions** (require `ANTHROPIC_API_KEY` secret):

| Workflow | When to use |
|----------|-------------|
| **Update 2026 Data** | Routine 2026 CSV merge + build |
| **Scrape CCN Data** | Full or partial archive re-scrape + build |

## CSV columns

| Column | Dashboard use |
|--------|----------------|
| `year`, `title`, `author`, `authors` | Identity, list, links |
| `keywords` | Search |
| `assigned_topics` | Theme filter & charts (pipe-separated, primary first); **not shown as tags in the list UI** |
| `abstract` | Search |
| `umap_x`, `umap_y` | Embedding map |
| `source_url`, `poster_number` | Links |

Build-only (not loaded in browser): `data/submissions.json`, `data/embeddings_all.json`, `data/google_topics.json`, `data/llm_theme_cache.json` (gitignored).

## Research themes (14)

Predetermined from the [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) Google Form and manual clustering oversight. **Everything else** is migrated away at build time.

Names/colors: `docs/js/app.js` (`GOOGLE_FORM_TOPICS`); override names via `data/google_topics.json`.

## Theme assignment (build time)

**Anthropic Claude** (`claude-opus-4-6` default) reads title, abstract, keywords, and optional track → one primary + up to four secondaries. Cached under **`year:id`** keys in `data/llm_theme_cache.json` (CCN reuses numeric ids across years).

Legacy id-only caches migrate automatically on the next build (~538 collision rows re-classified, not a full refresh). Separate from UMAP — themes are not from TF-IDF.

## UMAP map (build time)

Weighted text (title ×2, abstract ×3, keywords ×1) → TF-IDF → UMAP (`n_neighbors=15`, `min_dist=0.12`, cosine distance) → `umap_x`, `umap_y`. Layout only; dot color in the UI is the primary topic.

## Dashboard behavior

### Theme filter (two behaviors)

| Surface | Matches |
|---------|---------|
| **Matching submissions list** | Theme anywhere — primary **or** secondary |
| **UMAP map** | Dot **color** and **highlight** by **primary topic only** |

Click/tap a UMAP dot sets the shared theme filter to that dot’s **primary** topic. The list then shows all papers tagged with that theme anywhere; the map brightens dots whose primary matches. Topic labels are not displayed on list cards (only in CSV/search/charts).

Other filters: year, full-text search (title, author, abstract, keywords, assigned topics).

### Panels

| Panel | Data |
|-------|------|
| KPIs | counts, years, themes |
| Submissions over time | `year` |
| Theme ranking / YoY change | `assigned_topics` (any occurrence); default comparison **2017 → 2026** |
| Embedding map | `umap_x`, `umap_y`, primary color from `assigned_topics[0]` |
| Matching submissions | `title`, `year`, `authors`, `source_url` |

Phone: larger chart labels; UMAP uses nearest-point tap; a tooltip-style label appears centered on the map after filtering (hidden when you scroll past the map).

## Local preview

```bash
python -m http.server 8080 --directory docs
```
