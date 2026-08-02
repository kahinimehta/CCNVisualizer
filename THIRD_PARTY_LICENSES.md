# Third-Party Licenses

This project uses the following open-source libraries and services.

## JavaScript libraries (loaded via CDN)

### D3.js v7.9.0
- **License:** ISC License
- **Source:** https://github.com/d3/d3
- **Usage:** Line charts, bar charts, UMAP scatter plot, tooltips, and chart interactions in the dashboard

### jsPDF v2.5.2
- **License:** MIT License
- **Source:** https://github.com/parallax/jsPDF
- **Usage:** Lazy-loaded when exporting the current filter’s chart plots as a downloadable PDF

### Open Sans (Google Fonts)
- **License:** SIL Open Font License 1.1
- **Source:** https://fonts.google.com/specimen/Open+Sans
- **Usage:** UI typography

## Python dependencies (build pipeline only)

Used by scripts in `scripts/` to scrape archives, classify themes (Anthropic API), compute UMAP coordinates, and build the CSV. Not loaded by the static dashboard.

| Package | License | Source |
|---------|---------|--------|
| requests | Apache License 2.0 | https://github.com/psf/requests |
| Beautiful Soup 4 | MIT License | https://www.crummy.com/software/BeautifulSoup/ |
| lxml | BSD 3-Clause License | https://lxml.de/ |
| numpy | BSD 3-Clause License | https://numpy.org/ |
| scikit-learn | BSD 3-Clause License | https://scikit-learn.org/ |
| umap-learn | BSD 3-Clause License | https://github.com/lmcinnes/umap |
| pypdf | BSD 3-Clause License | https://github.com/py-pdf/pypdf |
| anthropic | MIT License | https://github.com/anthropics/anthropic-sdk-python |
| python-dotenv | BSD 3-Clause License | https://github.com/theskumar/python-dotenv |

Install for the pipeline: `pip install -r requirements.txt`

### Anthropic API (theme classification)

Theme labels are assigned at build time via the [Anthropic API](https://www.anthropic.com/) (Claude). Usage is subject to [Anthropic's terms of service](https://www.anthropic.com/legal/consumer-terms). API keys are never committed to the repository.

## Data

### CCN conference archives
- **Source:** https://ccneuro.org and year-specific conference sites (2017–2026)
- **Usage:** Publicly listed poster/paper metadata (titles, authors, abstracts, keywords, topics)
- **Note:** CCN submission content remains the property of respective authors. This project aggregates publicly available archive listings for academic visualization. Refer to each conference site's terms and author copyrights for reuse of paper content.

### CCN 2026 Activity Preferences (Google Form)
- **Source:** https://docs.google.com/forms/d/1c-ZR7PkUNDVeRmncAK2nmdKA5ZwuZ8opTr8Brl-WOJI/viewform
- **Usage:** Canonical list of 14 research theme names (`data/google_topics.json`; UI colors in `docs/js/app.js`)
- **Note:** See [docs/GUIDE.md](docs/GUIDE.md) for theme taxonomy and assignment.

## Trademarks

"Cognitive Computational Neuroscience" (CCN) and the CCN logo/branding are used descriptively to identify the conference data source. This project is not officially affiliated with CCN unless otherwise stated by the conference organizers.
