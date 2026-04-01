# ADS-Backed GitHub Pages CV

This folder now has the plumbing for a PDF-first academic CV that rebuilds from NASA ADS once per day and publishes to GitHub Pages.

## What is in the repo

- `academic_cv.tex`: your main LaTeX source, still the canonical CV layout.
- `cv.cls`: a minimal class file that supports the macros and environments used by `academic_cv.tex`.
- `cv_config.toml`: ADS/ORCID configuration, name aliases, and per-bibcode section overrides.
- `manual_publications.toml`: manual entries for `Submitted` and `In prep` items that ADS will not keep current for you.
- `scripts/generate_cv.py`: fetches ADS records, computes metrics, renders `generated/*.tex`, and builds `site/index.html`.
- `.github/workflows/ads-cv.yml`: daily GitHub Actions workflow that regenerates the TeX fragments, builds the PDF, and deploys GitHub Pages.

## One-time setup

1. Put this directory in a GitHub repository and push it.
2. In ADS, generate an API token and save it as a repository secret named `ADS_DEV_KEY`.
3. In ADS, connect your ORCID profile and claim your papers. ADS documents that new ORCID claims can take up to 24 hours to become searchable.
4. Verify `orcid_id` and `name_aliases` in `cv_config.toml`. The file is prefilled for Isaac Malsky, but you should confirm it before relying on the build.
5. Add any future `Submitted` or `In prep` papers to `manual_publications.toml`.
6. In GitHub Pages settings, choose `GitHub Actions` as the build and deployment source.

## Local use

Install the Python dependency and run the generator:

```bash
pip install -r requirements.txt
export ADS_DEV_KEY=your_ads_token
python scripts/generate_cv.py
```

The generator writes:

- `generated/metrics.tex`
- `generated/publications.tex`
- `site/index.html`

Then compile the PDF with your preferred LaTeX toolchain. For example:

```bash
latexmk -pdf -interaction=nonstopmode academic_cv.tex
```

## How the automation works

- ADS records are fetched using the official `ads` Python package.
- Publications are bucketed by your author position:
  - position 1 -> `First Author`
  - positions 2 through 4 -> `Second, Third or Fourth Author`
  - position 5+ -> `Contributing Author`
- `section_overrides` in `cv_config.toml` can override that default per bibcode.
- The GitHub Pages landing page shows the latest ADS metrics and embeds the generated PDF.

## Notes

- The workflow cron is in UTC.
- `generated/` and `site/` are intentionally ignored so CI can regenerate them cleanly on each run.
- If ADS returns zero papers, the generator fails unless you run it with `--allow-empty`.
# CV
