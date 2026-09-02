# Bash Cost Model

## Disclosed Constraints

- The native collection is the stream of lines (or NUL-delimited records)
  through a pipe. Bash arrays are flat only: no
  nesting, no structs; associative arrays require bash 4+ (macOS ships bash
  3.2 by default).
- Process spawn dominates every other cost. Each command substitution `$()`
  and each external command forks; a per-item `$()` inside a loop is the
  quadratic-allocation disaster of shell. One `awk` pass beats a thousand
  forks.
- Word splitting and glob expansion run after parameter expansion: every
  unquoted expansion is an injection and corruption surface. Quoting is the
  parse boundary.
- `set -e` has gaps. It is suppressed for commands in `if`/`while`
  conditions, on the left of `&&`/`||`, and under `!`; and
  `local x=$(cmd)` masks `cmd`'s failure because `local`'s own status wins.
  Declare and assign on separate lines when the status matters.
- Pipelines report only the last command's status unless `set -o pipefail`;
  each pipeline stage runs in a subshell, so `cmd | while read ...` cannot
  mutate parent variables.
- Arithmetic `$(( ))` is fixed-width signed integer and wraps silently; there
  are no floats. Delegate real arithmetic to `awk`.

## Preferred FP Shapes

- Pipelines are point-free composition and the native `map`/`filter`/`fold`
  vocabulary: `grep` filters, `sed`/`awk` map, `sort | uniq -c` and `awk`
  accumulators fold, `head -n1` after a filter is `find`/`first`, `comm` and
  `join` are set algebra on sorted streams.
- A pure function reads stdin/arguments and writes stdout, returning an exit
  status; treat every global variable write as an effect. Declare function
  state `local`; declare constants `readonly`.
- Start every script with `set -euo pipefail` and treat the remaining `set -e`
  gaps as known unsoundness.
- Model absence as empty output plus a nonzero status, never as a sentinel
  string like `"null"` or `"none"`.
- `case` is pattern matching over globs; prefer it to `if`/`elif` ladders that
  re-test one string. `${var:?message}` is the totality check for required
  parameters and fails loudly at the boundary.
- Build argument lists as arrays and expand with `"$@"`/`"${args[@]}"`; never
  assemble a command line in a flat string.
- For filenames or any value that may contain whitespace or newlines, use
  NUL-delimited streams end to end: `find -print0`, `xargs -0`,
  `while IFS= read -r -d ''`.

## Domain and Effect Constraints

- One parse boundary at the top: validate arguments and environment with
  `${VAR:?}` and explicit checks, then treat them as trusted for the rest of
  the script. Reject early, once.
- Resource bracket: `trap cleanup EXIT` plus `mktemp`/`mktemp -d` is the RAII
  of shell. One accumulating cleanup function; register it before acquiring
  the resource.
- Idempotency: scripts get re-run. Use atomic `mv` onto the final path,
  `mkdir` as a mutex, and write-to-temp-then-rename for any generated file.
- Bounded concurrency: `xargs -P n` (GNU/BSD) or a `wait` loop over a capped
  set of background jobs; never unbounded `&` fan-out. `wait -n` (bash 4.3+)
  harvests completions as they occur.
- Keep stdout pure data and route diagnostics to stderr, so the function
  stays composable in a pipeline.

## Teaching Example

<teaching_example language="bash"><![CDATA[
#!/usr/bin/env bash
set -euo pipefail

# Pure fold: stdin is "bytes<TAB>path" records; stdout is one number.
total_large_log_mib() {
  awk -F'\t' '$1 > 1048576 && $2 ~ /\.log$/ { sum += $1 }
              END { printf "%.1f\n", sum / 1048576 }'
}

main() {
  local dir="${1:?usage: $0 <dir>}"
  # GNU find emits the records; the filter-map-fold runs in ONE process.
  find "$dir" -type f -printf '%s\t%p\n' | total_large_log_mib
}

main "$@"
]]></teaching_example>

Taste: one `awk` process runs the filter and fold, where a `while read` loop
would fork `stat` per file: n lines through one process. `${1:?}` makes the required argument total at the boundary; the
function is pure (stdin to stdout), so it composes and tests in isolation.
`-printf` is a GNU extension; on BSD/macOS substitute `stat -f` per file or
install findutils, and say which you assumed.

## Cost Guard

1. Replace any loop that forks per item (`$()`, `grep`, `stat` inside the
   body) with one `awk`/`sed`/`sort` pass over the whole stream.
2. If parent-scope state must survive a pipeline, feed the loop with process
   substitution (`while read ... done < <(cmd)`) instead of piping into it.
3. Fuse long `grep | sed | awk | cut` chains into one `awk` program when the
   stage count matters; keep the chain when clarity wins and n is small.
4. Bound fan-out with `xargs -P`/capped background jobs.
5. Escape threshold: nested data, error accumulation across items, real
   arithmetic, or any structure beyond a flat stream means the fallback is
   another language. Say so; never simulate structs with `eval`.

## Validation Focus

ShellCheck is non-negotiable; treat its findings as type errors. `bash -n`
for syntax. Test with paths containing spaces and globs, empty input, an
unset required variable (to prove the `${:?}` boundary), and a failing
mid-pipeline stage (to prove `pipefail` semantics). State which shell and
which coreutils flavor (GNU versus BSD) the script assumes.
