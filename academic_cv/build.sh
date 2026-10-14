#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_PDF_PATH="${ROOT_DIR}/academic_cv/academic_cv.local.pdf"
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

  echo "Installing Python dependencies from academic_cv/pipeline/requirements.txt..."
  python -m pip install -r academic_cv/pipeline/requirements.txt
}

build_pdf() {
  mkdir -p "$(dirname "${LOCAL_PDF_PATH}")"
  local build_dir
  build_dir="$(mktemp -d "${TMPDIR:-/tmp}/academic-cv-build.XXXXXX")"

  if command -v tectonic >/dev/null 2>&1; then
    echo "Building academic_cv.local.pdf with tectonic..."
    tectonic --outdir "${build_dir}" "${ROOT_DIR}/academic_cv/academic_cv.tex"
    cp "${build_dir}/academic_cv.pdf" "${LOCAL_PDF_PATH}"
    rm -rf "${build_dir}"
    return
  fi

  if command -v latexmk >/dev/null 2>&1; then
    echo "Building academic_cv.local.pdf with latexmk..."
    latexmk -pdf -interaction=nonstopmode -outdir="${build_dir}" "${ROOT_DIR}/academic_cv/academic_cv.tex"
    cp "${build_dir}/academic_cv.pdf" "${LOCAL_PDF_PATH}"
    rm -rf "${build_dir}"
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
  python academic_cv/pipeline/generate_cv.py
else
  echo "ADS_DEV_KEY is not set; building the fallback CV without live ADS data."
  echo "To enable live ADS data locally, copy academic_cv/pipeline/.env.local.example to .env.local and paste your ADS token there."
  # Refuse to bake stale publication data into a PDF unless explicitly allowed.
  stamp="academic_cv/generated/.generated_at"
  max_age_days=7
  age_days=""
  if [[ -f "${stamp}" ]]; then
    age_days="$(python3 -c 'import sys, datetime; print((datetime.date.today() - datetime.date.fromisoformat(open(sys.argv[1]).read().strip())).days)' "${stamp}")"
    echo "Cached publication fragments were generated ${age_days} day(s) ago."
  else
    echo "Cached publication fragments carry no generation date."
  fi
  if [[ -z "${age_days}" || "${age_days}" -gt "${max_age_days}" ]]; then
    if [[ "${ALLOW_STALE_CV:-}" == "1" ]]; then
      echo "ALLOW_STALE_CV=1 is set; building anyway. The publication list and metrics may be out of date."
    else
      echo "error: refusing to build from stale publication data (older than ${max_age_days} days, or undated)." >&2
      echo "       Add ADS_DEV_KEY to .env.local for live data, or run: ALLOW_STALE_CV=1 $0" >&2
      exit 1
    fi
  fi
fi

build_pdf

echo "Built ${LOCAL_PDF_PATH}"

if command -v open >/dev/null 2>&1; then
  open "${LOCAL_PDF_PATH}"
fi
