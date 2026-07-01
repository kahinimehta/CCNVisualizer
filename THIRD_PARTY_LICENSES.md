# Third-Party Licenses

This project uses the following open-source libraries and services.

## JavaScript libraries (loaded via CDN)

### D3.js v7.9.0
- **License:** ISC License
- **Source:** https://github.com/d3/d3
- **Usage:** Line charts, bar charts, UMAP scatter plot, tooltips, and chart interactions in the dashboard

### Open Sans (Google Fonts)
- **License:** SIL Open Font License 1.1
- **Source:** https://fonts.google.com/specimen/Open+Sans
- **Usage:** UI typography

## Python dependencies (build pipeline only)

Used by scripts in `scripts/` to scrape archives, assign themes, and build the CSV. Not loaded by the static dashboard.

| Package | License | Source |
|---------|---------|--------|
| requests | Apache License 2.0 | https://github.com/psf/requests |
| Beautiful Soup 4 | MIT License | https://www.crummy.com/software/BeautifulSoup/ |
| lxml | BSD 3-Clause License | https://lxml.de/ |
| numpy | BSD 3-Clause License | https://numpy.org/ |
| scikit-learn | BSD 3-Clause License | https://scikit-learn.org/ |
| umap-learn | BSD 3-Clause License | https://github.com/lmcinnes/umap |
| pypdf | BSD 3-Clause License | https://github.com/py-pdf/pypdf |

See `scripts/requirements.txt` for pinned versions.

## Data

### CCN conference archives
- **Source:** https://ccneuro.org and year-specific sites (e.g. `2024.ccneuro.org`); provisional 2026 data from `data/ccn-2026-pending-posters.csv`
- **Usage:** Publicly listed poster/paper metadata (titles, authors, abstracts, keywords, topics)
- **Note:** CCN submission content remains the property of respective authors. This project aggregates publicly available archive listings for academic visualization. Refer to each conference site's terms and author copyrights for reuse of paper content.

### CCN 2026 Activity Preferences (Google Form)
- **Source:** https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform
- **Usage:** Canonical list of 12 primary research theme names (`data/google_topics.json` at build time; hardcoded in `docs/js/app.js` for UI colors)
- **Note:** Only the published form question 1 topic options are used — no response or analytics data.

## Trademarks

"Cognitive Computational Neuroscience" (CCN) and the CCN logo/branding are used descriptively to identify the conference data source. This project is not officially affiliated with CCN unless otherwise stated by the conference organizers.
