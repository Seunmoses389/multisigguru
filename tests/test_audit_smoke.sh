#!/bin/bash
set -e
SCRIPT="scripts/audit.sh"
bash "$SCRIPT" --help >/dev/null
if ! command -v cast >/dev/null 2>&1; then
  if bash "$SCRIPT" --safe 0xabc 2>&1 | grep -q "cast.*not found"; then
    echo "OK: cast-missing error clear"
  else
    echo "FAIL"; exit 1
  fi
else
  bash "$SCRIPT --demo" | grep -q "SCORE" && echo "OK: demo works"
fi
echo "All smoke tests passed."
