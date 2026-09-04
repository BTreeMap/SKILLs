# GitHub Actions Cost Model

A typed-ish coordination layer over jobs. The FP vocabulary applies at the
workflow/job/step level, and the effect discipline becomes privilege
discipline.

## Disclosed Constraints

- Each job runs on a fresh runner; spin-up (queue, provision, checkout) costs
  tens of seconds to minutes before any work starts. A job is a process spawn
  priced in runner-minutes.
- `${{ }}` is textual interpolation performed before the step executes.
  Inside `run:` it is unquoted splice into a shell script: any
  attacker-influenced context (PR titles and bodies, branch names via
  `github.head_ref`, commit messages, issue text) is untrusted input, and
  interpolating it is `eval` on attacker data.
- State dies with the runner. Data crosses jobs only through declared
  `outputs` (small strings) and artifacts (files); nothing else survives.
- `pull_request_target` and `workflow_run` execute with secrets and an
  elevated token while the triggering data is untrusted. Checking out and
  running PR-controlled code there is remote code execution with your token.
- A matrix is a cartesian product; its cost multiplies. `fail-fast` defaults
  to true, cancelling siblings on first failure, which silently converts
  "test everything" into "test until the first break."

## Preferred FP Shapes

- Job as function: consume `needs.<job>.outputs.*`, produce declared
  `outputs`. No hidden coupling through undeclared artifacts or convention.
  The `needs:` DAG is applicative structure: independent jobs already run in
  parallel; add an edge only for a real data dependency.
- Pure step: deterministic given declared inputs. Pin third-party actions to
  a full commit SHA with a version comment (referential transparency for
  dependencies; tags are mutable, SHAs are not). Pin toolchain versions from
  a lockfile or version file in the repository.
- `matrix` is `map` over a declared finite domain: the embarrassingly
  parallel primitive. Refine the domain with `include`/`exclude` instead of
  `if`-skipping cells at runtime; build dynamic domains with `fromJSON` on a
  prior job's output. Set `fail-fast: false` when every cell's result matters
  independently (error accumulation over fail-fast, chosen deliberately).
- Reusable workflows (`workflow_call`) and composite actions are the named
  combinators. `workflow_call` inputs carry `type`, `required`, and
  `default` (composite action inputs are strings only); validate anything
  stronger in the first step: that is the smart-constructor boundary.
- Boundedness is explicit: `timeout-minutes` on every job (the 6-hour default
  ceiling amplifies outages), and a
  `concurrency` group with `cancel-in-progress` for workflows where only the
  latest run matters.
- Caching is memoization with a stated key law: the key names exactly the
  inputs that invalidate it (lockfile hashes), `restore-keys` define the
  acceptable staleness lattice. A wrong key law is either a stale hit
  (unsound) or a permanent miss (useless).

## Domain and Effect Constraints

- Permissions are the effect types of CI. Set a minimal default at workflow
  level (`permissions: {}` or `contents: read`) and grant per job only the
  capabilities its effects require. Never rely on the org/repo default token
  setting; declare explicitly.
- Untrusted context never crosses into a shell via `${{ }}`. Route it through
  `env:` and reference it as a quoted shell variable (`"$TITLE"`), so it
  arrives as data.
- Prefer OIDC federation over long-lived cloud secrets; scope secrets to
  `environment`s so only the jobs performing the deploy effect can read them.
- Treat `pull_request_target`/`workflow_run` as elevated interpreters: never
  check out or execute PR head code in them; consume only the event payload
  you have parsed and validated.

## Teaching Example

<teaching-example language="yaml">
<![CDATA[
on:
  workflow_call:
    inputs:
      targets:               # declared finite domain, JSON array of strings
        type: string
        required: true

permissions: {}              # no ambient capabilities; jobs ask for their own

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read         # the only effect this job performs
    strategy:
      fail-fast: false       # every target's result matters independently
      matrix:
        target: ${{ fromJSON(inputs.targets) }}   # map over the domain
    steps:
      - uses: actions/checkout@<full-commit-sha>  # resolve and pin; tags drift
      - name: Build one target
        env:
          TARGET: ${{ matrix.target }}            # data crosses as env, not splice
        run: ./ci/build.sh "$TARGET"
]]></teaching-example>

Taste: the matrix maps a pure build over a declared domain in parallel with
independent failures; `permissions` names the job's one effect; potentially
attacker-influenced data enters the shell exactly once, quoted, as an
environment variable; the logic is in a ShellCheck-able script.

## Cost Guard

1. Fuse jobs into sequential steps of one job when runner spin-up exceeds the
   parallelism gain (many short jobs, shared setup); split into jobs when
   cells are independent and long.
2. Pass small values as job outputs; reserve artifacts for real files. Do not
   upload a workspace to transport one flag.
3. Prune the matrix: `exclude` redundant cells; a full product of OS x
   runtime x flags is rarely all meaningful.
4. Cache with keys derived from lockfiles and restore-keys ordered from exact
   to acceptable; measure hit rate before trusting the cache to be a win.
5. Escape threshold: nontrivial logic in `run:` strings or `if:` expressions
   moves to a script file in the repository (testable, lintable, reviewable)
   or a small composite action. YAML coordinates, scripts compute.

## Validation Focus

Run `actionlint` (it also ShellChecks embedded `run:` blocks) and a security
scanner such as `zizmor`. Grep the workflow set for missing `permissions`,
missing `timeout-minutes`, unpinned third-party `uses:`, and `${{` inside
`run:`. Exercise a `workflow_call` with an invalid input to prove the
boundary rejects it. Where behavior must be seen to be trusted, trigger the
workflow on a branch and read the run.
