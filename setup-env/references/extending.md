# Extending

Maintainer file: not loaded during normal runs. Read it to add a target,
change a recipe, or understand why the code is shaped as it is.

## Architecture

Strict one-directional layering; each module names its concern in its
docstring:

    model -> steps -> catalog -> plan -> render/effects -> cli

Everything through `plan` is pure: `btm-setup-env plan` prints exactly what
`provision` would do, with no network and no filesystem writes; that
property is the test seam. `effects` is the only module that performs
I/O; `cli` only parses and reports.

## Laws

The invariants the design enforces; a change that weakens one is wrong even
when it appears to work:

1. Closed domain. Hosts, conda platforms, plan steps, and catalog keys are
   closed sets. An unknown tag, an impossible (target, host) pair, or a
   version handed to a versionless recipe fails during planning with a
   message naming the fix; no effect has run yet.
2. One prefix, one create. micromamba `create` replaces a prefix. The
   planner merges every host-bound package list into a single `CondaEnv`
   step per prefix; executors never install into an existing prefix. The
   standalone shim path unions against the manifest for the same reason.
3. Env merge is a checked monoid. Recipes contribute `EnvDelta` values;
   duplicate variables must agree, PATH entries dedupe preserving first
   occurrence. One merged delta is rendered to activate.sh, activate.ps1,
   and the probe process environment, so what verification proved is what
   activation grants.
4. Emulation is total and central. `emulation(host, platform)` in `model`
   is the only place architecture reachability is decided; recipes match on
   its variants and never inspect `uname` themselves.
5. Idempotence by postcondition. Every executor checks completion state
   (manifest entry plus on-disk evidence) before working, downloads to a
   partial name and renames, and re-running provision is the documented
   repair for any interruption.
6. Determinism. Plans sort by (stage, type, repr); package sets sort
   before comparison; nothing reads clocks or randomness. Equal inputs
   yield equal plans and byte-equal activation scripts.

## Adding A Target

1. Choose the key. New toolchain: new family. Same toolchain aimed at a
   different platform or ABI: new flavor of an existing family. Never
   encode a version in the name.
2. Pick suppliers in order: conda-forge if it packages the tool well
   (verify with `micromamba search -c conda-forge --platform <each>` on
   all five platforms); the publisher
   otherwise, pinned by version and sha256 when the publisher offers no
   digest sidecar; never a curl-pipe-sh installer.
3. Write the `Recipe` in `catalog`: requirements as existing step values
   when possible (a new step type in `steps` plus one executor in
   `effects` only for new machinery), env as an
   `EnvDelta` of redirections under the root, at least one probe per
   user-visible tool. Reject unsupported hosts inside `requirements` with
   a message naming the alternative.
4. Redirect every cache or config variable the tool honors (its HOME-dwelling
   dotdir is already covered by the HOME redirect). If the tool's wrapper
   scripts expect a variable a normal activation would set, export it in the
   recipe (never run foreign activation code); the CONDA_PREFIX and
   DOTNET_ROOT cases in `plan` and `catalog` are the precedents.
5. Update `targets` (the per-target notes and footprint) and, when the
   change touches invariants, `SKILL.md`.

## Testing Protocol

On at least one linux host, ideally both architectures:

- `btm-setup-env plan <tag>`: steps and env look right, twice for determinism.
- `btm-setup-env provision <tag>`: exit 0, probes ok; re-run completes in under a
  second changing nothing.
- The falsifier from `SKILL.md`: an `env -i` shell sourcing activate.sh
  compiles and runs a hello program end to end (link steps included; a
  compiler that cannot link passes --version probes and still fails users).
- `btm-setup-env provision` with the tag removed: the conda prefix reshapes to
  the smaller set.
- `btm-setup-env destroy`, then a fresh provision from nothing.

Record in `targets` what was validated per platform; claim nothing
untested.
