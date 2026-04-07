# Marianne CV Scholar Pipeline

This folder preserves Marianne Cowherd's existing LaTeX CV layout while generating the publications section from Google Scholar plus a checked-in manual override file.

## Files

- `main.tex`: Marianne's CV template and non-publication content.
- `cv.cls`: the existing CV class file.
- `src/cv_config.toml`: Scholar profile metadata, author aliases, and optional excluded Scholar titles.
- `src/manual_publications.toml`: unpublished entries plus published-paper overrides needed to preserve the current CV text exactly.
- `src/generate_cv.py`: fetches Scholar records, applies overrides, writes `generated/publications.tex`, and writes `compiled/index.html`.
- `src/build_local_cv.sh`: creates a local `.venv`, installs dependencies, regenerates the publications fragment, and builds the PDF.
- `misc/build_cv.command`: Finder-friendly wrapper for the build script.

## Local Use

Run:

```bash
./src/build_local_cv.sh
```

or double-click:

```text
misc/build_cv.command
```

The build script creates a local virtual environment in `.venv`, installs the `scholarly` dependency there, regenerates the publications fragment, and builds `compiled/main.pdf`.

To regenerate just the Scholar-derived publication list without compiling the PDF:

```bash
./.venv/bin/python src/generate_cv.py
```

To run the tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## GitHub Actions

- `.github/workflows/update-cv.yml` runs once per day and can also be triggered manually.
- It uses the same `src/build_local_cv.sh` script as the local workflow, then commits updated generated assets back to the repository.

## Notes

- No API key is required.
- The build now requires a fresh live Scholar fetch and fails immediately on Scholar errors instead of retrying or reusing older publications data.
- The generator uses `scholarly` with a free proxy and pins `httpx==0.27.2`, because newer `httpx` releases break `scholarly`'s proxy setup.
- The publications section keeps the current CV wording where overrides exist, adds the rest of Marianne's Scholar works automatically, and keeps the current `submitted` / `in revision` items as manual entries.
