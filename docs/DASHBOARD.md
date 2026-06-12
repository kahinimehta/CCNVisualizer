# Submission Visualizer — Dashboard Guide

Interactive dashboard for CCN poster and paper archives (2018–2026), styled with CCN brand colors (navy, pink, blue, green) in a card-based layout.

**Live site:** https://ccn-visualizer.vercel.app/

## Core concept: research themes

Every submission is assigned:

| Field | Role |
|-------|------|
| `primary_theme` | One of 10 embedding research themes — drives **all** charts, filters, and counts |
| `secondary_topics` | Up to 3 additional theme tags — shown in the secondary-topics cloud and paper metadata only |

### The 10 research themes

1. Cognition and Memory Systems
2. Decision and Metacognition
3. Naturalistic Brain Encoding
4. Neural Population Dynamics
5. Reinforcement Learning
6. LLMs and Reasoning
7. Language Neuroscience
8. Neural Network Theory
9. Computer Vision Models
10. Visual Cortex Models

**2026** submissions use exact UMAP/KMeans cluster labels from `embeddings_2026.json`. **Earlier years** are inferred by matching title, abstract, and topic text against 2026 cluster profiles (`scripts/assign_research_themes.py`).

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Header · Year / Research theme dropdown · Search             │
│ KPI cards · Year chips                                      │
├──────────────────────────────┬──────────────────────────────┤
│ Submissions over time        │ Research theme ranking       │
├──────────────────────────────┴──────────────────────────────┤
│ Research themes over time (annual + cumulative lines)        │
│ ├─ Total by research theme │ Year-over-year change         │
├──────────────────────────────┬──────────────────────────────┤
│ Abstract embedding map       │ Primary themes (donut)       │
│ Matching submissions         │ Secondary topics (cloud)     │
│                              │ Theme breakdown (bars)       │
└──────────────────────────────┴──────────────────────────────┘
```

## Filters

All visualizations respect the active filter state:

- **Year** — single year or all years
- **Research theme** — dropdown lists primary themes with counts; filters to submissions where `primary_theme` matches
- **Search** — title, authors, primary theme, secondary topics, topic area

Clicking a theme on any chart (ranking bars, donut, UMAP legend, embedding points, sidebar bars) applies the same research-theme filter.

## Components

| Component | Data source | Notes |
|-----------|-------------|-------|
| Submissions over time | All filtered submissions | Count by year |
| Research theme ranking | `primary_theme` | Horizontal bars, full theme names |
| Research themes over time | `primary_theme` × year | Solid = annual count; dashed = cumulative |
| Total by research theme | `primary_theme` | All-time totals in filter |
| Year-over-year change | `primary_theme` | Single bar per theme for latest year pair |
| Abstract embedding map | 2026 UMAP coordinates | Click to filter by primary theme |
| Matching submissions | Filtered list | Shows primary + secondary tags |
| Primary research themes | `primary_theme` | Donut chart |
| Secondary topics | `secondary_topics` | Word cloud (informational, not a filter) |
| Theme breakdown | `primary_theme` | Sidebar bar chart |

## Data pipeline

```bash
python scripts/scrape_ccn.py           # scrape archives + merge 2026 CSV
python scripts/build_cluster_viz.py    # 2026 UMAP JSON
python scripts/assign_research_themes.py  # primary_theme + secondary_topics on every row
```

Or run the **Scrape CCN Data** GitHub Action (runs all three steps).

### Updating 2026

1. Replace `data/ccn-2026-pending-posters.csv`
2. Re-run merge + cluster build + theme assignment

### Google Form topics (future)

When form data is ready, set `docs/data/google_topics.json` with `enabled: true`. Form assignments can override `primary_theme` at runtime.

## Files

| Path | Purpose |
|------|---------|
| `docs/index.html` | Dashboard markup |
| `docs/js/app.js` | Charts, filters, theme logic |
| `docs/css/style.css` | CCN styling |
| `docs/data/submissions.json` | Submissions with `primary_theme` / `secondary_topics` |
| `docs/data/embeddings_2026.json` | 2026 UMAP points and cluster names |
| `docs/data/google_topics.json` | Optional form-based overrides |
