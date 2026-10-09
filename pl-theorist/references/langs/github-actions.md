# GitHub Actions Profile

Typed-ish coordination layer over jobs. FP vocabulary applies at
workflow/job/step level; effect discipline becomes privilege discipline.

## Cost Model

- Each job runs on fresh runner; spin-up (queue, provision, checkout) costs
  tens of seconds to minutes before any work starts. Job is process spawn
  priced in runner-minutes.
- `${{ }}` is textual interpolation performed before step executes. Inside
  `run:` it is unquoted splice into shell script: any attacker-influenced
  context (PR titles and bodies, branch names via `github.head_ref`, commit
  messages, issue text) is untrusted input; interpolating it is `eval` on
  attacker data.
- State dies with runner. Data crosses jobs only through declared `outputs`
  (small strings) and artifacts (files); nothing else survives.
- `pull_request_target` and `workflow_run` execute with secrets and elevated
  token while triggering data is untrusted. Checking out and running
  PR-controlled code there is remote code execution with your token.
- Matrix is cartesian product; cost multiplies. `fail-fast` defaults to
  true, cancelling siblings on first failure, silently converting "test
  everything" into "test until the first break."

## Domain Shapes

- Job as function: consume `needs.<job>.outputs.*`, produce declared
  `outputs`. No hidden coupling through undeclared artifacts or convention.
  `needs:` DAG is applicative structure: independent jobs already run in
  parallel; add edge only for real data dependency.
- Pure step: deterministic given declared inputs. Pin third-party actions to
  full commit SHA with version comment (referential transparency for
  dependencies; tags mutable, SHAs not). Pin toolchain versions from
  lockfile or version file in repository.
- `matrix` is `map` over declared finite domain: embarrassingly parallel
  primitive. Refine domain with `include`/`exclude`, not `if`-skipping cells
  at runtime; build dynamic domains with `fromJSON` on prior job's output.
  Set `fail-fast: false` when every cell's result matters independently
  (error accumulation over fail-fast, chosen deliberately).
- Reusable workflows (`workflow_call`) and composite actions are named
  combinators. `workflow_call` inputs carry `type`, `required`, `default`
  (composite action inputs strings only); validate anything stronger in
  first step: smart-constructor boundary.
- Caching is memoization with stated key law: key names exactly inputs that
  invalidate it (lockfile hashes); `restore-keys` define acceptable
  staleness lattice. Wrong key law is either stale hit (unsound) or
  permanent miss (useless).

## Effects

- Permissions are CI's effect types. Minimal default at workflow level
  (`permissions: {}` or `contents: read`); grant per job only capabilities
  its effects require. Never rely on org/repo default token setting.
- Untrusted context never crosses into shell via `${{ }}`. Route through
  `env:`, reference as quoted shell variable (`"$TITLE"`), so it arrives as
  data.
- Prefer OIDC federation over long-lived cloud secrets; scope secrets to
  `environment`s so only jobs performing deploy effect can read them.
- `pull_request_target`/`workflow_run` are elevated interpreters: never
  check out or execute PR head code in them; consume only event payload you
  have parsed and validated.
- Boundedness explicit: `timeout-minutes` on every job (6-hour default
  ceiling amplifies outages), and `concurrency` group with
  `cancel-in-progress` for workflows where only latest run matters.

## Teaching Example

<example for="teaching" language="yaml">
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
]]></example>

Taste: matrix maps pure build over declared domain in parallel with
independent failures; `permissions` names job's one effect; potentially
attacker-influenced data enters shell exactly once, quoted, as environment
variable; logic is in ShellCheck-able script.

## Cost Guard

1. Fuse jobs into sequential steps of one job when runner spin-up exceeds
   parallelism gain (many short jobs, shared setup); split into jobs when
   cells independent and long.
2. Pass small values as job outputs; artifacts only for real files. Never
   upload workspace to transport one flag.
3. Prune matrix: `exclude` redundant cells; full product of OS x runtime x
   flags rarely all meaningful.
4. Cache with keys derived from lockfiles, restore-keys ordered from exact
   to acceptable; measure hit rate before trusting cache.
5. Escape threshold: nontrivial logic in `run:` strings or `if:` expressions
   moves to script file in repository (testable, lintable, reviewable) or
   small composite action.

## Validation

Run `actionlint` and security scanner such as `zizmor`. No `/setup-env` tag
provisions either; run both through uv, which `/setup-env` already assumes:

<commands for="workflow-lint">
uvx --from actionlint-py actionlint
uvx zizmor .github/workflows
</commands>

`actionlint` ShellChecks embedded `run:` blocks only when `shellcheck` is on
PATH; provision it with `/setup-env provision bash`. Grep workflow set for
missing `permissions`, missing `timeout-minutes`, unpinned third-party
`uses:`, `${{` inside `run:`. Exercise `workflow_call` with invalid input to
prove boundary rejects it. Behavior must be seen to be trusted: trigger
workflow on branch, read run.
