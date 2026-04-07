#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [[ -f ".env.local" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env.local"
  set +a
fi

ensure_python_dependencies() {
  if python - <<'PY' >/dev/null 2>&1
import ads
PY
  then
    return
  fi

  echo "Installing Python dependencies from src/requirements.txt..."
  python -m pip install -r src/requirements.txt
}

build_pdf() {
  mkdir -p compiled

  if command -v tectonic >/dev/null 2>&1; then
    echo "Building academic_cv.pdf with tectonic..."
    tectonic --outdir "${ROOT_DIR}/compiled" "${ROOT_DIR}/latex/academic_cv.tex"
    return
  fi

  if command -v latexmk >/dev/null 2>&1; then
    echo "Building academic_cv.pdf with latexmk..."
    latexmk -pdf -interaction=nonstopmode -outdir="${ROOT_DIR}/compiled" "${ROOT_DIR}/latex/academic_cv.tex"
    return
  fi

  echo "No local LaTeX engine found." >&2
  echo "Install one of these and run again:" >&2
  echo "  brew install tectonic" >&2
  echo "  or install latexmk through MacTeX/TeX Live" >&2
  exit 1
}

if [[ -n "${ADS_DEV_KEY:-}" ]]; then
  ensure_python_dependencies
  echo "Generating live ADS-backed publications section..."
  python src/generate_cv.py
else
  echo "ADS_DEV_KEY is not set; building the fallback CV without live ADS data."
  echo "To enable live ADS data locally, copy misc/.env.local.example to .env.local and paste your ADS token there."
fi

build_pdf

echo "Built ${ROOT_DIR}/compiled/academic_cv.pdf"

if command -v open >/dev/null 2>&1; then
  open compiled/academic_cv.pdf
fi
