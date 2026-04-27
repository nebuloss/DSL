#!/usr/bin/env bash
set -euo pipefail

EXAMPLES_DIR="$(cd "$(dirname "$0")" && pwd)"

verbose=0
if [[ "${1:-}" == "-v" || "${1:-}" == "--verbose" ]]; then
    verbose=1
fi

pass=0
fail=0
failed_files=()

for script in "$EXAMPLES_DIR"/*.py; do
    name="$(basename "$script")"
    printf '%-40s ' "$name"
    output=$(python "$script" 2>&1) && status=0 || status=$?
    if [[ $status -eq 0 ]]; then
        echo "OK"
        pass=$((pass + 1))
    else
        echo "FAIL"
        fail=$((fail + 1))
        failed_files+=("$name")
    fi
    if [[ $verbose -eq 1 || $status -ne 0 ]]; then
        echo "$output" | sed 's/^/    /'
        echo
    fi
done

echo "Results: $pass passed, $fail failed"

if [[ $fail -gt 0 ]]; then
    exit 1
fi
