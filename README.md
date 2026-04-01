# ADS-Backed GitHub Pages CV

This repo builds a PDF-first academic CV from NASA ADS data and publishes it to GitHub Pages once per day.

## Files

- `academic_cv.tex`: the article-style LaTeX CV layout.
- `cv_config.toml`: display name, optional ORCID ID, ADS aliases, and Google Scholar link.
- `manual_publications.toml`: manual `submitted` entries that ADS cannot keep up to date for you.
- `scripts/generate_cv.py`: fetches ADS records, computes metrics, renders `generated/selected_research.tex`, and builds `site/index.html`.
- `.github/workflows/ads-cv.yml`: scheduled GitHub Actions workflow that regenerates the TeX fragment, builds the PDF, and deploys GitHub Pages.

## Setup

1. Generate an ADS API token and save it as the repository secret `ADS_DEV_KEY`.
2. In `cv_config.toml`, confirm `display_name`, `name_aliases`, and `scholar_url`.
3. If you want the cleanest author matching, keep your ORCID ID in `cv_config.toml` and make sure your papers are claimed in ADS.
4. If you do not want to rely on ORCID, set `orcid_id = ""` and the generator will fall back to ADS author-alias queries.
5. Add or edit any `submitted` items in `manual_publications.toml`.
6. In the GitHub repo settings, set Pages to build from `GitHub Actions`.

## Local use

```bash
pip install -r requirements.txt
export ADS_DEV_KEY=your_ads_token
python scripts/generate_cv.py
```

The generator writes:

- `generated/selected_research.tex`
- `site/index.html`

Then compile the PDF with your LaTeX toolchain:

```bash
latexmk -pdf -interaction=nonstopmode academic_cv.tex
```

## Notes

- The only required secret is `ADS_DEV_KEY`.
- You do not need an ORCID secret. An ORCID ID is public and can live in `cv_config.toml`.
- If ADS returns zero papers, the generator fails unless you run it with `--allow-empty`.
