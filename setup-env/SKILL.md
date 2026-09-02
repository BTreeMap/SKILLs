---
name: setup-env
description: >-
  Provisions an isolated, per-project development environment entirely in
  userspace: no sudo, no docker, no global installs, assuming only uv on
  PATH. A typed target algebra (family[:flavor][@version] tags such as
  python@3.12, kotlin:android, go:cgo, rust, typescript, haskell) selects
  exactly the toolchains a project needs; micromamba supplies conda-forge
  packages, uv supplies CPython, publishers supply what only they ship, and
  qemu user-mode emulation runs foreign-architecture binaries (Google's
  x86_64-only aapt2 on arm64) behind transparent shims. Emits an activation
  script that redirects HOME, caches, and toolchain variables under one
  disposable root. Use when an agent must build, test, or lint a project on
  a machine lacking its toolchains, when root or docker is unavailable, when
  arm64 must run amd64-only build tools, or when several languages must
  coexist in one reproducible environment. Do not use for CI runner images,
  system package administration, or deploying services.
license: MIT
compatibility: >-
  uv on PATH, network access, and a full SKILLs repository checkout: the
  provisioner is a uv workspace member under the skill's scripts/ directory,
  and everything else is fetched. Linux and macos on x86_64/arm64 are first
  class; windows x86_64 is best effort (haskell, bash, c, cpp unavailable
  there). Roughly 1-6 GB under the environment root, depending on targets.
metadata:
  argument-hint: "[provision|plan|status|shim|destroy|list] [tags...]"
---

# Setup Env

One command provisions everything a project needs into one disposable
root: run it, source the printed activation script, build. Re-running is
safe and is the repair action: every step checks its postcondition and
skips completed work.

## Registry

| Name | Path |
| --- | --- |
| `cli` | [scripts/src/btm_setup_env/cli.py](scripts/src/btm_setup_env/cli.py) |
| `model` | [scripts/src/btm_setup_env/model.py](scripts/src/btm_setup_env/model.py) |
| `steps` | [scripts/src/btm_setup_env/steps.py](scripts/src/btm_setup_env/steps.py) |
| `catalog` | [scripts/src/btm_setup_env/catalog.py](scripts/src/btm_setup_env/catalog.py) |
| `plan` | [scripts/src/btm_setup_env/plan.py](scripts/src/btm_setup_env/plan.py) |
| `render` | [scripts/src/btm_setup_env/render.py](scripts/src/btm_setup_env/render.py) |
| `effects` | [scripts/src/btm_setup_env/effects.py](scripts/src/btm_setup_env/effects.py) |
| `targets` | [references/targets.md](references/targets.md) |
| `extending` | [references/extending.md](references/extending.md) |

The console command `btm-setup-env` is the entry point; the registered
module names are the member's internals. Read `targets` before choosing
tags beyond the obvious; read `extending` only to add or change a recipe.
The command surface is the handoff point: invoke it and read its output;
source reading belongs to user-instructed troubleshooting.

## Procedure

Name as tags only the languages the project uses. The grammar is
`family[:flavor][@version]`: family picks a toolchain, flavor picks what it
builds for, version pins it. `list` prints every known tag.

<setup_command>

```bash
env -u VIRTUAL_ENV uv run --project "$(realpath <skill-dir>/scripts)" btm-setup-env provision <tags> --project <project-root>
```

</setup_command>

`--project` defaults to the nearest ancestor of the working directory
containing `.git`. The environment root is derived from the project path
(override the base with `DENV_HOME`, or the exact root with `DENV_ROOT` or
`--root`). Pass `--json` for machine-readable output.

<example_invocations>

```bash
# A python + go + typescript monorepo, python pinned
btm-setup-env provision python@3.12 go typescript

# Android work on any host, including arm64; API level as the version
btm-setup-env provision kotlin:android@35

# Generic kotlin (JVM), or kotlin compiled to native binaries
btm-setup-env provision kotlin
btm-setup-env provision kotlin:native

# Systems work: cgo needs a C toolchain, so it is a flavor
btm-setup-env provision go:cgo rust cmake

# Preview the plan without executing anything
btm-setup-env plan haskell csharp
```

</example_invocations>

Expected: `Environment ready under <root>`, one `ok` probe line per
toolchain, exit 0. Then activate and work; every command is identical on
every supported host:

```bash
. <root>/activate.sh        # POSIX shells; activate.ps1 on windows
```

Verify later with `status`, wrap a stray foreign-architecture binary with
`shim <binary>`, delete the root with `destroy`.

## The Interface Is The Whole Contract

- Exact toolset: the environment contains the union of what the named tags
  require and nothing else, installed by one solver call per prefix.
- Conflicts are errors before effects: two versions of one toolchain, an
  unknown tag, or a target impossible on this host all fail during planning
  with a precise message, never mid-download.
- Idempotent: an interrupted or failed run is repaired by re-running the
  same command. `provision` with a different tag set reshapes the
  environment to exactly that set.
- Versions left unpinned resolve to the newest conda-forge build; the
  chosen versions are recorded in `<root>/manifest.json`.

## Isolation Invariant

Every mutable path lives under the root: HOME, TMPDIR, XDG dirs, and each
toolchain's cache and config variables are redirected by the activation
script. The project checkout is written only when a build tool demands a
generated, ignored file (`local.properties` for Android). Nothing reads the
caller's HOME, dotfiles, or global toolchains; nothing writes outside the
root and the project.

Falsifier: run a build through `env -i` carrying only the activation
script. A pass proves independence from caller state.

<isolation_check>

```bash
env -i /bin/sh -c '. <root>/activate.sh && cd <project> && <build-command>'
```

</isolation_check>

## The Architecture Fact

Some publishers ship a tool for exactly one platform; Google ships linux
aapt2 as x86_64 only, and every Android resource task runs it. How a host
reaches a foreign binary is a total function of (host, needed platform),
decided in one place (`model`) and answered by first-class variants:

| Host | Foreign linux-x86_64 binary runs via |
| --- | --- |
| linux/x86_64 | direct execution |
| linux/arm64 | qemu user-mode emulation against a conda-forge sysroot |
| macos/arm64 | Rosetta 2 for osx-64 binaries, transparently |
| windows | unsupported: emulation is a linux mechanism |

Nothing downstream branches on architecture: the emulated tool is one
executable at one path, registered where its consumer looks (aapt2 through
`android.aapt2FromMavenOverride` in the isolated `gradle.properties`), and
its wrapper writes nothing to stdout because callers speak daemon protocols
over those pipes.

## Gotchas

- uv is the only assumption. A bare ubuntu:24.04 image with uv works: the
  scripts fetch TLS roots via certifi, download with Python itself, and
  never call curl, git, tar, or unzip binaries.
- Activation redirects HOME, so git identity and ssh keys are absent inside
  an activated shell. Build and test there; commit from a normal shell.
- micromamba `create` replaces a prefix. The planner therefore merges all
  host packages into one create call; never hand-install into
  `<root>/conda/host` with a second call.
- Toolchains pinned by the project (gradlew, package.json, Cargo.toml)
  stay authoritative: the android recipes deliberately install no gradle
  and no kotlin, because a second copy on PATH only confuses diagnosis.
- Emulated tools run slower: minutes for a full Android resource pipeline
  where native takes seconds. Correctness is unaffected.
- The root is ephemeral by design (under the system temp dir unless
  `DENV_HOME` says otherwise). After a reboot, re-run provision.
- Narrowing the tag set reshapes the conda prefix exactly but leaves stale
  publisher downloads under `<root>/tools`; run `destroy` and re-provision
  for a byte-exact minimal root.
- Recipes were validated end to end on linux (both architectures); macos
  and windows follow the same code paths with best-effort edges, and
  re-running provision is the repair action.
- macos/arm64 Android builds need Rosetta 2 once:
  `softwareupdate --install-rosetta --agree-to-license`.
