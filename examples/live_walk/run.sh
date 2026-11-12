#!/usr/bin/env bash
# Live walk: ingest the November 7, 2026 walk of public October releases into a library
# that held the October 3 state, and show the ripple. Runs on a scratch copy; the committed
# example files are never modified. Run from the repository root:
#
#     bash examples/live_walk/run.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp -R "$HERE/library" "$WORK/library"
LIB="$WORK/library"

# Run a command, show it, and require one of the expected exit codes.
step() {
    local expect="$1"; shift
    echo
    echo "\$ $*"
    set +e
    "$@"
    local rc=$?
    set -e
    echo "[exit $rc]"
    case " $expect " in
        *" $rc "*) ;;
        *) echo "unexpected exit code $rc (expected: $expect)"; exit 1 ;;
    esac
}

echo "## 1. Before: the library as of the October 3 walk"
step "0" gsps views --library "$LIB" --as-of 2026-11-12 --dry

echo
echo "## 2. Ingest the November 7 walk (two walks are refused on purpose)"
step "1" gsps ingest --library "$LIB" --walks "$HERE/walks_20261107.csv" \
    --tokens "$HERE/TOKENS.csv" --on 2026-11-12

echo
echo "## 3. After: citations to revised values are now Behind"
step "0" gsps views --library "$LIB" --as-of 2026-11-12 --dry

echo
echo "## 4. Impact of the September revision"
step "0" gsps impact --library "$LIB" --anchor LAB-012 --tokens "$HERE/TOKENS.csv"

echo
echo "## 5. Fill report for the brief: which values on the page are now dirty"
step "1" gsps fill-report --library "$LIB" --tokens "$HERE/TOKENS.csv" \
    --page "$HERE/page_v1.md" --doc-version v1

echo
echo "## 6. The estimate no longer reproduces from its revised inputs"
step "1" gsps recompute --method "(LAB-010 + LAB-012) / 2" --stated "81,000" \
    --input "LAB-010=186,000" --input "LAB-012=60,000"

echo
echo "## 7. Vocabulary and integrity on the new version"
step "0 1" gsps vocab-check --library "$LIB"

echo
echo "## Files written by the ingest (scratch copy)"
(cd "$LIB" && find . -type f | sort)
