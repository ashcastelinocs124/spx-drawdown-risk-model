#!/usr/bin/env bash
# Rebuild every result from the downloaded inputs, then copy them to outputs/.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DATA="${1:-$HERE/data}"
py() { python3 -I "$HERE/scripts/$1" "$DATA" "${@:2}"; }

py build.py                 # gap index (4 platform topics) + market outcomes + tests
py build.py --no-foreign    # original 3-topic index, for comparison
py export.py                # dashboard tables
py control.py               # divided vs unified government x gap
py postelection.py          # 1/3/6 months after each election
py vix_test.py              # monthly VIX tests
py legislative.py           # platform gap vs what Congress did (slow: reads all member votes)
py extras.py                # recent-decade windows, VIX tables, split detail, correlations

mkdir -p "$HERE/outputs/three_topic"
cp "$DATA"/work/*.csv "$DATA"/work/results.json "$HERE/outputs/"
cp "$DATA"/work/three_topic/results.json "$HERE/outputs/three_topic/"
echo "Outputs written to $HERE/outputs"
