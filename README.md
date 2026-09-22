# CV

Academic CV built from NASA ADS data. GitHub Actions regenerates the
publication list and rebuilds the PDF daily.

[Latest compiled CV (PDF)](academic_cv/academic_cv.pdf)

## Layout

```
academic_cv/
  academic_cv.tex     LaTeX layout
  academic_cv.pdf     published PDF (auto-built + committed daily by CI)
  build.sh            local build (fetches citations, then compiles)
  build_cv.command    double-click launcher for build.sh
  generated/          auto-generated publication fragments (git-ignored)
  pipeline/           the citation-pulling code
    generate_cv.py        fetch ADS records, compute metrics, render fragments
    cv_config.toml        display name, ORCID, ADS aliases
    manual_publications.toml  in-review entries ADS can't track yet
    requirements.txt
    .env.local.example
    tests/
```

All PDFs are git-ignored except the published `academic_cv/academic_cv.pdf`.

## Building locally

```bash
./academic_cv/build.sh
```

or double-click `academic_cv/build_cv.command`. This compiles in a throwaway
temp dir and writes only `academic_cv/academic_cv.local.pdf` (git-ignored), so
no `.aux/.log/.fls` clutter accumulates. Needs `tectonic` (preferred) or
`latexmk`.

### Live ADS data locally (optional)

Without an ADS token the CV builds from whatever fragments are already in
`academic_cv/generated/` (left over from a previous run; CI regenerates them on
every build). To pull fresh citations yourself:

```bash
cp academic_cv/pipeline/.env.local.example .env.local   # at the repo root
# then paste your ADS token as ADS_DEV_KEY
```

`academic_cv/build.sh` sources `.env.local`, installs deps, and regenerates the
fragments before compiling. You can also run the pipeline directly:

```bash
pip install -r academic_cv/pipeline/requirements.txt
export ADS_DEV_KEY=your_ads_token
python academic_cv/pipeline/generate_cv.py   # writes academic_cv/generated/*.tex
```

## The ADS pipeline

`academic_cv/pipeline/generate_cv.py` queries ADS, computes metrics (h-index,
citations, first-author count), and renders `publications.tex` + `software.tex`
into `academic_cv/generated/`.

- Configure in `cv_config.toml`: `display_name`, `name_aliases`, and an optional
  public `orcid_id` (recommended for clean author matching; leave blank to fall
  back to alias queries).
- Add papers ADS can't track yet to `manual_publications.toml` (`review_state` is
  `submitted`, `in_review`, or `accepted`; zero counts are omitted from the summary line).
- The only secret needed is the `ADS_DEV_KEY` repository secret (used by CI).
- If ADS returns zero papers the generator fails unless run with `--allow-empty`.

`.github/workflows/ads-cv.yml` runs the tests, regenerates the fragments, builds
the PDF, and commits `academic_cv/academic_cv.pdf` on a daily schedule.

## Tests

```bash
python -m unittest discover -s academic_cv/pipeline/tests
```
