#!/bin/bash
set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

"${SCRIPT_DIR}/build.sh"
status=$?

if [ "${status}" -eq 0 ]; then
  echo
  echo "CV build finished."
  echo "PDF: ${SCRIPT_DIR}/academic_cv.local.pdf"
else
  echo
  echo "CV build failed with status ${status}."
fi

read -r -p "Press Enter to close..."
exit "${status}"
