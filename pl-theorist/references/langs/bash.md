# Bash Profile

## Cost Model

- Native collection is stream of lines (or NUL-delimited records) through
  pipe. Bash arrays flat only: no nesting, no structs; associative arrays
  require bash 4+ (macOS ships bash 3.2 by default).
- Process spawn dominates every other cost. Each command substitution `$()`
  and each external command forks; per-item `$()` inside loop is shell's
  quadratic-allocation disaster.
- Word splitting and glob expansion run after parameter expansion: every
  unquoted expansion is injection and corruption surface. Quoting is parse
  boundary.
- `set -e` has gaps. Suppressed for commands in `if`/`while` conditions,
  left of `&&`/`||`, under `!`; `local x=$(cmd)` masks `cmd`'s failure
  because `local`'s own status wins. Declare and assign on separate lines
  when status matters.
- Pipelines report only last command's status unless `set -o pipefail`; each
  stage runs in subshell, so `cmd | while read ...` cannot mutate parent
  variables.
- Arithmetic `$(( ))` is fixed-width signed integer, wraps silently; no
  floats. Delegate real arithmetic to `awk`.

## Domain Shapes

- Pipelines are point-free composition and native `map`/`filter`/`fold`
  vocabulary: `grep` filters, `sed`/`awk` map, `sort | uniq -c` and `awk`
  accumulators fold, `head -n1` after filter is `find`/`first`, `comm` and
  `join` are set algebra on sorted streams.
- Pure function reads stdin/arguments, writes stdout, returns exit status;
  every global variable write is effect. Function state `local`; constants
  `readonly`.
- Model absence as empty output plus nonzero status, never sentinel string
  like `"null"` or `"none"`.
- `case` is pattern matching over globs; prefer it to `if`/`elif` ladders
  re-testing one string.
- One parse boundary at top: validate arguments and environment with
  `${VAR:?}` and explicit checks, then treat them as trusted for rest of
  script. `${var:?message}` is totality check for required parameters, fails
  loudly at boundary.
- Build argument lists as arrays, expand with `"$@"`/`"${args[@]}"`; never
  assemble command line in flat string.
- Filenames or any value that may contain whitespace or newlines:
  NUL-delimited streams end to end: `find -print0`, `xargs -0`,
  `while IFS= read -r -d ''`.

## Effects

- Start every script with `set -euo pipefail`; treat remaining `set -e` gaps
  as known unsoundness.
- Resource bracket: `trap cleanup EXIT` plus `mktemp`/`mktemp -d` is shell's
  RAII. One accumulating cleanup function; register before acquiring
  resource.
- Idempotency: scripts get re-run. Atomic `mv` onto final path, `mkdir` as
  mutex, write-to-temp-then-rename for any generated file.
- Bounded concurrency: `xargs -P n` (GNU/BSD) or `wait` loop over capped set
  of background jobs; never unbounded `&` fan-out. `wait -n` (bash 4.3+)
  harvests completions as they occur.
- Stdout pure data, diagnostics to stderr, so function stays composable in
  pipeline.

## Teaching Example

<example for="teaching" language="bash">
<![CDATA[
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
]]></example>

Taste: one `awk` process runs filter and fold, where `while read` loop would
fork `stat` per file: n lines through one process. `${1:?}` makes required
argument total at boundary; function is pure (stdin to stdout), so it
composes and tests in isolation. `-printf` is GNU extension; on BSD/macOS
substitute `stat -f` per file or install findutils, and say which you
assumed.

## Cost Guard

1. Replace any loop forking per item (`$()`, `grep`, `stat` inside body)
   with one `awk`/`sed`/`sort` pass over whole stream.
2. Parent-scope state must survive pipeline: feed loop with process
   substitution (`while read ... done < <(cmd)`) instead of piping into it.
3. Fuse long `grep | sed | awk | cut` chains into one `awk` program when
   stage count matters; keep chain when clarity wins and n is small.
4. Bound fan-out with `xargs -P`/capped background jobs.
5. Escape threshold: nested data, error accumulation across items, real
   arithmetic, or any structure beyond flat stream means fallback is another
   language. Say so; never simulate structs with `eval`.

## Validation

ShellCheck non-negotiable; treat its findings as type errors. `bash -n` for
syntax. Test with paths containing spaces and globs, empty input, unset
required variable (proves `${:?}` boundary), failing mid-pipeline stage
(proves `pipefail` semantics). State which shell and coreutils flavor (GNU
versus BSD) script assumes.
