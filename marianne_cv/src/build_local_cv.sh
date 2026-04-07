#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"
GENERATOR_ARGS=("$@")

ensure_python() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Creating local virtual environment..."
    python3 -m venv "${VENV_DIR}"
  fi

  echo "Syncing Python dependencies from src/requirements.txt..."
  "${PIP_BIN}" install -r "${ROOT_DIR}/src/requirements.txt"
}

build_pdf() {
  mkdir -p "${ROOT_DIR}/compiled"

  if command -v tectonic >/dev/null 2>&1; then
    echo "Building main.pdf with tectonic..."
    tectonic --outdir "${ROOT_DIR}/compiled" "${ROOT_DIR}/main.tex"
    return
  fi

  if command -v latexmk >/dev/null 2>&1; then
    echo "Building main.pdf with latexmk..."
    latexmk -pdf -interaction=nonstopmode -outdir="${ROOT_DIR}/compiled" "${ROOT_DIR}/main.tex"
    return
  fi

  echo "No local LaTeX engine found." >&2
  echo "Install one of these and run again:" >&2
  echo "  brew install tectonic" >&2
  echo "  or install latexmk through MacTeX/TeX Live" >&2
  exit 1
}

cd "${ROOT_DIR}"
ensure_python

echo "Generating Scholar-backed publications section..."
if [[ "${#GENERATOR_ARGS[@]}" -gt 0 ]]; then
  "${PYTHON_BIN}" src/generate_cv.py "${GENERATOR_ARGS[@]}" 2> >(sed 's/^error: /Scholar refresh failed: /' >&2)
else
  "${PYTHON_BIN}" src/generate_cv.py 2> >(sed 's/^error: /Scholar refresh failed: /' >&2)
fi

build_pdf

echo "Built ${ROOT_DIR}/compiled/main.pdf"

if command -v open >/dev/null 2>&1; then
  open "${ROOT_DIR}/compiled/main.pdf"
fi
