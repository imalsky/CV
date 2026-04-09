# ADS-Backed CV

This repo builds an academic CV PDF from NASA ADS data daily via GitHub Actions.

## Files

- `latex/academic_cv.tex`: the LaTeX CV layout.
- `src/cv_config.toml`: display name, optional ORCID ID, and ADS aliases.
- `src/manual_publications.toml`: manual `submitted` entries that ADS cannot keep up to date for you.
- `src/generate_cv.py`: fetches ADS records, computes metrics, and renders `latex/generated/publications.tex`.
- `.github/workflows/ads-cv.yml`: scheduled GitHub Actions workflow that regenerates the TeX fragment and builds the PDF.

## Setup

1. Generate an ADS API token and save it as the repository secret `ADS_DEV_KEY`.
2. In `src/cv_config.toml`, confirm `display_name` and `name_aliases`.
3. If you want the cleanest author matching, keep your ORCID ID in `src/cv_config.toml` and make sure your papers are claimed in ADS.
4. If you do not want to rely on ORCID, set `orcid_id = ""` and the generator will fall back to ADS author-alias queries.
5. Add or edit any `submitted` items in `src/manual_publications.toml`.

## Local use

The easiest local options are:

```bash
./src/build_local_cv.sh
```

or double-click:

```text
misc/build_cv.command
```

If you want live ADS data locally, create a `.env.local` file first:

```bash
cp misc/.env.local.example .env.local
```

Then edit `.env.local` and paste your ADS token as the value of `ADS_DEV_KEY`.

You can still run the underlying steps manually:

```bash
pip install -r src/requirements.txt
export ADS_DEV_KEY=your_ads_token
python src/generate_cv.py
```

The generator writes `latex/generated/publications.tex`.

Then compile the PDF with your LaTeX toolchain:

```bash
latexmk -pdf -interaction=nonstopmode -outdir=compiled latex/academic_cv.tex
```

## Notes

- The only required secret is `ADS_DEV_KEY`.
- You do not need an ORCID secret. An ORCID ID is public and can live in `src/cv_config.toml`.
- If ADS returns zero papers, the generator fails unless you run it with `--allow-empty`.
- If `ADS_DEV_KEY` is not set locally, the helper script still builds a PDF using the checked-in `latex/generated/publications.tex` fragment.
