#!/usr/bin/env bash
cd "$(dirname "$0")/.."
run() { printf '$ %s\n' "$*"; "$@"; printf '[exit %s]\n\n' "$?"; }
echo "# 1. A rubric that selects on a protected attribute cannot be frozen"
run python3 scripts/rubric_lint.py examples/rubric-biased.json
run python3 scripts/rubric_lint.py examples/rubric-good.json
echo "# 2. Career arithmetic done by code: overlap counted once, gaps reported as questions, vague dates listed as unknown"
run python3 scripts/career_facts.py examples/positions.json --as-of 2026-01
echo "# 3. Hidden instructions inside a resume are shown to a human; the score is never changed"
run python3 scripts/injection_scan.py examples/resume-injected.txt
run python3 scripts/injection_scan.py examples/resume-clean.txt
