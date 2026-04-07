#!/bin/bash
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

"${ROOT_DIR}/src/build_local_cv.sh"
status=$?

if [ "${status}" -eq 0 ]; then
  echo
  echo "CV build finished."
  echo "PDF: ${ROOT_DIR}/compiled/academic_cv.pdf"
else
  echo
  echo "CV build failed with status ${status}."
fi

read -r -p "Press Enter to close..."
exit "${status}"
