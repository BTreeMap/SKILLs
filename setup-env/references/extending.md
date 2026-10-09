# Extending

Maintainer file: not loaded during normal runs. Read it to add target,
change recipe, or understand why code is shaped as it is.

## Architecture

Strict one-directional layering; each module names its concern in its
docstring:

    model -> steps -> catalog -> plan -> render/execute -> cli

Everything through `plan` is pure: `btm-setup-env design` prints exactly
what `provision` would do, no network, no filesystem writes; that property
is the test seam. `execute` and rest of shell package hold every effect;
`cli` only parses and reports.

## Laws

1. Closed domain. Hosts, conda platforms, plan steps, catalog keys are
   closed sets, so every conflict `SKILL.md` lists under Guarantees fails
   during planning, before any effect, with message naming fix.
2. One prefix, one create. micromamba `create` replaces a prefix. Planner
   merges every host-bound package list into single `CondaEnv` step per
   prefix; executors never install into existing prefix. Standalone shim
   path unions against manifest for same reason.
3. Env merge is checked monoid. Recipes contribute `EnvDelta` values;
   duplicate variables must agree, PATH entries dedupe preserving first
   occurrence. One merged delta rendered to activate.sh, activate.ps1, probe
   process environment, so what verification proved is what activation
   grants.
4. Emulation is total and central. `emulation(host, platform)` in `model` is
   only place architecture reachability is decided, as total function of
   (host, needed platform). Recipes match on its variants; nothing
   downstream inspects `uname` or branches on architecture. Emulated tool is
   one executable at one path, registered where its consumer looks; its
   wrapper writes nothing to stdout.
5. Idempotence by postcondition. Every executor checks completion state
   (manifest entry plus on-disk evidence) before working, downloads to
   partial name, then renames.
6. Determinism. Plans sort by (stage, type, repr); package sets sort before
   comparison; nothing reads clocks or randomness. Equal inputs yield equal
   plans and byte-equal activation scripts.

## Adding A Target

1. Choose key. New toolchain: new family. Same toolchain aimed at different
   platform or ABI: new flavor of existing family. Never encode version in
   name.
2. Pick suppliers in order: conda-forge if it packages tool well (verify
   with `micromamba search -c conda-forge --platform <each>` on all five
   platforms); publisher otherwise, pinned by version and sha256 when
   publisher offers no digest sidecar; never curl-pipe-sh installer.
3. Write `Recipe` in `catalog`: requirements as existing step values when
   possible (new step type in `steps` plus one executor in `execute` only
   for new machinery), env as `EnvDelta` of redirections under root, at
   least one probe per user-visible tool. Reject unsupported hosts inside
   `requirements` with message naming alternative.
4. Redirect every cache or config variable tool honors (its HOME-dwelling
   dotdir already covered by HOME redirect). Tool's wrapper scripts expect
   variable normal activation would set: export it in recipe (never run
   foreign activation code); CONDA_PREFIX and DOTNET_ROOT cases in `plan`
   and `catalog` are precedents.
5. Update `targets` (per-target row and footprint) and, when change touches
   invariants, `SKILL.md`.

## Testing Protocol

On at least one linux host, ideally both architectures:

- `btm-setup-env design <tag>`: steps and env look right, twice for
  determinism.
- `btm-setup-env provision <tag>`: record's `ok` true, every probe passes;
  re-run completes in under a second changing nothing.
- Isolation falsifier from `SKILL.md`: `env -i` shell sourcing activate.sh
  compiles and runs hello program end to end, link steps included; compiler
  that cannot link passes --version probes and still fails users.
- `btm-setup-env provision` with tag removed: conda prefix reshapes to
  smaller set.
- `btm-setup-env clean`, then fresh provision from nothing.

Record in `targets` what was validated per platform; claim nothing untested.
