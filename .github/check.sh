#!/usr/bin/env bash
# The check chain: every fixer, then every assertion, in one order.
#
# Contributors run it before a commit (BACKLOG.md section 5); the gate
# workflow's assertion step runs it on every push to main.
#
#   .github/check.sh               stop at the first failing check
#   .github/check.sh --keep-going  run every check, fail if any failed
#
# A passing check prints its name and the last line of its output. A failing
# check prints its name and full output. Exit 0 if all checks passed, 1 if
# any failed, or 2 for incorrect usage.
#
# Runs from the repository root wherever it is invoked. RUFF_VERSION, when
# set (the gate workflow sets it), runs that exact ruff build through uvx;
# otherwise the ruff on PATH runs. Assumes bash 4 and GNU grep (`-P`).
set -euo pipefail

keep_going=false
case "${1-}" in
  '') ;;
  --keep-going) keep_going=true ;;
  *)
    echo "usage: $0 [--keep-going]" >&2
    exit 2
    ;;
esac

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

ruff=(ruff)
if [[ -n ${RUFF_VERSION-} ]]; then
  ruff=(uvx "ruff@${RUFF_VERSION}")
fi

log=$(mktemp)
trap 'rm -f -- "$log"' EXIT

# One function per check, run in the order `checks` names them. Fixers run
# first, so the assertions judge the repaired tree. A function runs as an
# `if` condition, where `set -e` is off, so each is one command or checks
# its own statuses.
check_format() { "${ruff[@]}" format .; }
check_lint() { "${ruff[@]}" check --fix .; }
check_tests() { uv run --all-packages pytest -q -m 'not network'; }
check_types() { uv run --all-packages mypy; }
check_gate() { uv run --project .github/gate btm-repo-gate fix; }
check_lock() { uv lock --check; }

# An em-dash (U+2014) or en-dash (U+2013) in Markdown or Python, outside any
# virtualenv and the humanize style file that quotes them. grep exits 1 when
# nothing matches; 2 is an error, which fails the check rather than passing
# it silently.
check_dashes() {
  local hits status=0
  hits=$(grep -rnP --exclude-dir=.venv --exclude-dir=worktrees --include='*.md' --include='*.py' \
    '\x{2014}|\x{2013}' .) || status=$?
  if ((status > 1)); then
    return "$status"
  fi
  hits=$(grep -v '^\./humanize/references/style\.md:' <<<"$hits" || true)
  if [[ -n $hits ]]; then
    printf '%s\n' "$hits"
    echo "Replace the em or en dashes listed above with plain punctuation."
    return 1
  fi
  echo "No em or en dashes found."
}

checks=(format lint tests types gate lock dashes)

failed=0
for name in "${checks[@]}"; do
  case "$name" in
    format) label="Ruff formatting" ;;
    lint) label="Ruff lint" ;;
    tests) label="Tests (no live APIs)" ;;
    types) label="Type check (mypy)" ;;
    gate) label="Repository conventions" ;;
    lock) label="uv lockfile" ;;
    dashes) label="Dash check" ;;
  esac
  if "check_$name" >"$log" 2>&1; then
    printf 'PASS %s: %s\n' "$label" "$(grep -v '^[[:space:]]*$' "$log" | tail -n 1 || true)"
    continue
  fi
  echo "FAIL $label"
  cat -- "$log"
  failed=1
  if [[ $keep_going == false ]]; then
    exit 1
  fi
done
exit "$failed"
