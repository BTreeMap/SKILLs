---
name: setup-env
description: >-
  Installs a project's development toolchain in userspace: no sudo, no
  docker, nothing assumed but uv, all under one disposable root leaving HOME
  and caches untouched. Tags such as python@3.12, kotlin:android, or rust
  name what project needs; tools built for another CPU architecture still
  run. Use when a project must be built, tested, or linted on a machine
  lacking its toolchains, without root or docker, or when several languages
  must coexist reproducibly.
license: MIT
compatibility: >-
  uv on PATH, network access, and a full SKILLs repository checkout. Linux
  and macos on x86_64/arm64 are first class; windows x86_64 is best effort
  (haskell, bash, c, cpp unavailable there). Roughly 1-7 GB under the
  environment root, depending on targets. The first run builds the `.venv`
  at the checkout root that every skill's scripts share, about 225 MB.
metadata:
  argument-hint: "[install|design|status|shim|clean|list] [tags...]"
---

# Setup Env

One command installs everything project needs into one disposable root: run
it, source printed activation script, build. Re-run to repair.

## Registry

| Name | Path |
| --- | --- |
| `catalog` | [scripts/src/btm_setup_env/catalog.py](scripts/src/btm_setup_env/catalog.py) |
| `cli` | [scripts/src/btm_setup_env/cli.py](scripts/src/btm_setup_env/cli.py) |
| `execute` | [scripts/src/btm_setup_env/shell/execute.py](scripts/src/btm_setup_env/shell/execute.py) |
| `extending` | [references/extending.md](references/extending.md) |
| `model` | [scripts/src/btm_setup_env/model.py](scripts/src/btm_setup_env/model.py) |
| `plan` | [scripts/src/btm_setup_env/plan.py](scripts/src/btm_setup_env/plan.py) |
| `render` | [scripts/src/btm_setup_env/render.py](scripts/src/btm_setup_env/render.py) |
| `steps` | [scripts/src/btm_setup_env/steps.py](scripts/src/btm_setup_env/steps.py) |
| `targets` | [references/targets.md](references/targets.md) |

Load `targets` before choosing tag beyond the obvious or pinning version;
load `extending` only to add or change recipe. Invoke command, read its
output; read source only for user-instructed troubleshooting.

## Redirects

- CI images, system packages, and deployment: use the project's own tooling;
  this root serves local builds and tests

## Choose Tags

Name as tags only languages project uses. Grammar is
`family[:flavor][@version]`: family picks toolchain, flavor picks what it
builds for, version pins it. Unpinned version resolves to newest available
build; `<root>/manifest.json` records chosen versions. `list` prints every
known tag. Toolchains pinned by project (gradlew, package.json, Cargo.toml)
stay authoritative.

## Install

Bind command to `R` once per shell; re-bind after reset; `realpath` and both
`env -u` flags required:

<commands for="setup">

```bash
R="env -u VIRTUAL_ENV -u UV_PROJECT_ENVIRONMENT uv run --project $(realpath <skill-root>/scripts) btm-setup-env"
$R install <tags> --project <project-root>
```

</commands>

Every verb named outright; bare tag list is rejected. Examples below
abbreviate `$R` as `btm-setup-env`. `--project` defaults to nearest ancestor
of working directory containing `.git`. Environment root derived from
project path, under system temp dir; override base with `DENV_HOME`, or
exact root with `--root` or `DENV_ROOT`, flag winning. Root under temp dir
is ephemeral: after reboot, re-run install.

<commands for="examples">

```bash
# A python + go + typescript monorepo, python pinned
btm-setup-env install python@3.12 go typescript

# Android work on any host, including arm64; API level as the version
btm-setup-env install kotlin:android@35

# Generic kotlin (JVM), or kotlin compiled to native binaries
btm-setup-env install kotlin
btm-setup-env install kotlin:native

# Systems work: cgo needs a C toolchain, so it is a flavor
btm-setup-env install go:cgo rust cmake

# Preview the plan without executing anything
btm-setup-env design haskell csharp
```

</commands>

Each verb writes one JSON record to stdout, nothing else; progress and
warnings go to stderr as `signal:` lines. Expected: exit 0 and `ok` true.
Failed test still exits 0, with `ok` false and `next` line naming repair;
exit 1 means argument needs fixing, never that toolchain is broken.

Every verb except `list` takes `--project` and `--root`.

| Verb | Record on stdout | Refuses |
| --- | --- | --- |
| `install <tags>` | `ok`, `root`, `activate_sh`, `activate_ps1`, `env`, `tests` (one per test: `command`, `ok`, `output`), and `next` when a test failed | A conflict listed under Guarantees |
| `design <tags>` | `root`, `steps`, `env`, `path`, `tests`; nothing is installed | As `install` |
| `status` | what `install` emits, with the tests re-run | A root with no environment |
| `shim <binary> [--platform P]` | `shim`: the wrapper path; `P` is one of `linux-64` (default), `linux-aarch64`, `osx-64`, `osx-arm64`, `win-64` | A missing binary, a platform this host runs natively, a host with no emulation |
| `clean` | `removed`, `bytes_freed` | A root carrying no manifest this tool wrote, and `--all` |
| `list` | `targets`: one row of `tag`, `summary`, `version` each | Nothing |

## Activate And Work

Once activated, every command identical on every supported host:

<commands for="activate">

```bash
. <root>/activate.sh        # POSIX shells; activate.ps1 on windows
```

</commands>

Activation redirects HOME, so git identity and ssh keys are absent inside
activated shell. Build and test there; commit from normal shell.

## Guarantees

- Exact toolset: environment contains union of what named tags require and
  nothing else.
- Conflicts are errors before effects: two versions of one toolchain,
  unknown tag, version handed to versionless target, or target impossible on
  this host all fail during planning with precise message, never
  mid-download.
- Idempotent: interrupted or failed run is repaired by re-running same
  command. `install` with different tag set reshapes conda prefix to exactly
  that set but leaves stale publisher downloads under `<root>/tools`; run
  `clean` and re-install for byte-exact minimal root.

## Isolation

Every mutable path lives under root: HOME, TMPDIR, XDG dirs, each
toolchain's cache and config variables redirected by activation script.
Project checkout written only when build tool demands generated, ignored
file (`local.properties` for Android). Nothing reads caller's HOME,
dotfiles, or global toolchains; nothing writes outside root and project.

Falsifier: run build through `env -i` carrying only activation script. Pass
proves independence from caller state.

<checklist for="isolation">

```bash
env -i /bin/sh -c '. <root>/activate.sh && cd <project> && <build-command>'
```

</checklist>

## Foreign-Architecture Binaries

Some publishers ship build tool for exactly one platform:

| Host | Foreign linux-x86_64 binary runs via |
| --- | --- |
| linux/x86_64 | direct execution |
| linux/arm64 | qemu user-mode emulation against a conda-forge sysroot |
| macos/arm64 | Rosetta 2 for osx-64 binaries, transparently |
| windows | unsupported: emulation is a linux mechanism |

- macos/arm64 Android builds need Rosetta 2 once:
  `softwareupdate --install-rosetta --agree-to-license`.
- Emulated tools run slower: minutes for full Android resource pipeline
  where native takes seconds. Correctness unaffected.
- To run any other foreign binary a build needs, wrap it with `shim`, call
  returned wrapper path.

## Gotchas

- Bare ubuntu:24.04 image with uv works: uv is only assumption.
- Never hand-install into `<root>/conda/host` with second call: prefix
  create step replaces whole prefix.
