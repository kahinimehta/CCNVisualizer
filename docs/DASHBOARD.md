# Submission Visualizer — Dashboard Guide

Interactive dashboard for CCN poster and paper archives (2018–2026), styled with CCN brand colors (navy, pink, blue, green) in a card-based layout.

**Live site:** https://ccn-visualizer.vercel.app/

## Core concept: research themes

Every submission is assigned:

| Field | Role |
|-------|------|
| `primary_theme` | One of 10 embedding research themes — drives **all** charts, filters, and counts |
| `secondary_topics` | Up to 3 additional theme tags — shown in the secondary-topics cloud and paper metadata only |

### The 12 research themes (Google Form Q1)

From [CCN 2026 Activity Preferences](https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform) — meetup topic affiliation:

1. RL, motor control & planning
2. Naturalistic encoding/decoding
3. Neural population geometry & dynamics
4. Decision-making and metacognition
5. Vision
6. Language/auditory neuroscience
7. LLMs, reasoning, interpretability
8. Memory
9. Social cognition & theory of mind
10. Attention & cognitive control / executive function
11. Clinical / computational psychiatry
12. Methods, theory & everything else

**2026** submissions map embedding clusters → Google topics. **Earlier years** are inferred by text match. Embedding cluster names may appear as **secondary topics**.

## Layout

Single-column stack, max-width **1080px**, centered — fills a laptop screen without stretching ultra-wide on large monitors. On mobile, filters and KPI cards reflow to 1–2 columns.

```
┌──────────────────────────────────────┐
│ Header · filters · KPIs · year chips │
├──────────────────────────────────────┤
│ Submissions over time                │
│ Research theme ranking             │
│ Research themes over time          │
│   └ totals · year-over-year        │
│ Abstract embedding map             │
│ Matching submissions               │
│ Primary themes · Secondary · Bars  │
└──────────────────────────────────────┘
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
