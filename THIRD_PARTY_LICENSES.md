# Third-Party Licenses

This project uses the following open-source libraries and services.

## JavaScript libraries (loaded via CDN)

### D3.js v7.9.0
- **License:** ISC License
- **Source:** https://github.com/d3/d3
- **Usage:** Line/bar/donut charts, UMAP scatter plot, data binding

### d3-cloud v1.2.7
- **License:** BSD 3-Clause License
- **Source:** https://github.com/jasondavies/d3-cloud
- **Usage:** Secondary topics word cloud layout

## Fonts

### Open Sans (Google Fonts)
- **License:** SIL Open Font License 1.1
- **Source:** https://fonts.google.com/specimen/Open+Sans
- **Usage:** UI typography

## Python dependencies (scraper only)

### requests
- **License:** Apache License 2.0
- **Source:** https://github.com/psf/requests

### Beautiful Soup 4
- **License:** MIT License
- **Source:** https://www.crummy.com/software/BeautifulSoup/

### lxml
- **License:** BSD 3-Clause License
- **Source:** https://lxml.de/

## Data

### CCN conference archives
- **Source:** https://ccneuro.org and year-specific sites (e.g. `2024.ccneuro.org`); provisional 2026 data from `data/ccn-2026-pending-posters.csv`
- **Usage:** Publicly listed poster/paper metadata (titles, authors, abstracts, keywords, topics)
- **Note:** CCN submission content remains the property of respective authors. This project aggregates publicly available archive listings for academic visualization. Refer to each conference site's terms and author copyrights for reuse of paper content.

### CCN 2026 Activity Preferences (Google Form)
- **Source:** https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform
- **Usage:** Canonical list of 12 primary research themes (`data/google_topics.json`)
- **Note:** Form responses are optional; attendee preference counts may be added to `response_counts` when available.

## Trademarks

"Cognitive Computational Neuroscience" (CCN) and the CCN logo/branding are used descriptively to identify the conference data source. This project is not officially affiliated with CCN unless otherwise stated by the conference organizers.
