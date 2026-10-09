---
name: setup-env
description: >-
  Provisions a project's development toolchain in userspace: no sudo, no
  docker, nothing assumed but uv, all under one disposable root that leaves
  HOME and caches untouched. Tags such as python@3.12, kotlin:android, or
  rust name what a project needs; tools built for another CPU architecture
  still run. Use when a project must be built, tested, or linted on a
  machine lacking its toolchains, without root or docker, or when several
  languages must coexist reproducibly.
license: MIT
compatibility: >-
  uv on PATH, network access, and a full SKILLs repository checkout. Linux
  and macos on x86_64/arm64 are first class; windows x86_64 is best effort
  (haskell, bash, c, cpp unavailable there). Roughly 1-7 GB under the
  environment root, depending on targets. The first run builds the `.venv`
  at the checkout root that every skill's scripts share, about 225 MB.
metadata:
  argument-hint: "[provision|design|status|shim|clean|list] [tags...]"
---

# Setup Env

One command provisions everything a project needs into one disposable root:
run it, source the printed activation script, build. Re-run to repair.

## Registry

| Name | Path |
| --- | --- |
| `cli` | [scripts/src/btm_setup_env/cli.py](scripts/src/btm_setup_env/cli.py) |
| `model` | [scripts/src/btm_setup_env/model.py](scripts/src/btm_setup_env/model.py) |
| `steps` | [scripts/src/btm_setup_env/steps.py](scripts/src/btm_setup_env/steps.py) |
| `catalog` | [scripts/src/btm_setup_env/catalog.py](scripts/src/btm_setup_env/catalog.py) |
| `plan` | [scripts/src/btm_setup_env/plan.py](scripts/src/btm_setup_env/plan.py) |
| `render` | [scripts/src/btm_setup_env/render.py](scripts/src/btm_setup_env/render.py) |
| `execute` | [scripts/src/btm_setup_env/shell/execute.py](scripts/src/btm_setup_env/shell/execute.py) |
| `targets` | [references/targets.md](references/targets.md) |
| `extending` | [references/extending.md](references/extending.md) |

Load `targets` before choosing a tag beyond the obvious or pinning a
version; load `extending` only to add or change a recipe. Invoke the command
and read its output; read source only for user-instructed troubleshooting.

## Redirects

- CI images, system packages, and deployment: use the project's own tooling;
  this root serves local builds and tests

## Choose Tags

Name as tags only the languages the project uses. The grammar is
`family[:flavor][@version]`: family picks a toolchain, flavor picks what it
builds for, version pins it. An unpinned version resolves to the newest
available build; `<root>/manifest.json` records the chosen versions. `list`
prints every known tag. Toolchains pinned by the project (gradlew,
package.json, Cargo.toml) stay authoritative.

## Provision

<commands for="setup">

```bash
env -u VIRTUAL_ENV uv run --project "$(realpath <skill-dir>/scripts)" btm-setup-env provision <tags> --project <project-root>
```

</commands>

Every verb is named outright; a bare tag list is rejected. The examples
below abbreviate the invocation above as `btm-setup-env`. `--project`
defaults to the nearest ancestor of the working directory containing
`.git`. The environment root is derived from the project path, under the
system temp dir; override the base with `DENV_HOME`, or the exact root with
`--root` or `DENV_ROOT`, the flag winning. A root under the temp dir is ephemeral: after a
reboot, re-run provision.

<commands for="examples">

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
btm-setup-env design haskell csharp
```

</commands>

Each verb writes one JSON record to stdout and nothing else; progress and
warnings go to stderr as `signal:` lines. Expected: exit 0 and `ok` true. A failed
probe still exits 0, with `ok` false and a `next` line naming the repair;
exit 1 means an argument needs fixing, never that a toolchain is broken.

Every verb except `list` takes `--project` and `--root`.

| Verb | Record on stdout | Refuses |
| --- | --- | --- |
| `provision <tags>` | `ok`, `root`, `activate_sh`, `activate_ps1`, `env`, `probes` (one per probe: `command`, `ok`, `output`), and `next` when a probe failed | A conflict listed under Guarantees |
| `design <tags>` | `root`, `steps`, `env`, `path`, `probes`; nothing is installed | As `provision` |
| `status` | what `provision` emits, with the probes re-run | A root with no environment |
| `shim <binary> [--platform P]` | `shim`: the wrapper path; `P` is one of `linux-64` (default), `linux-aarch64`, `osx-64`, `osx-arm64`, `win-64` | A missing binary, a platform this host runs natively, a host with no emulation |
| `clean` | `removed`, `bytes_freed` | A root carrying no manifest this tool wrote, and `--all` |
| `list` | `targets`: one row of `tag`, `summary`, `version` each | Nothing |

## Activate And Work

Once activated, every command is identical on every supported host:

<commands for="activate">

```bash
. <root>/activate.sh        # POSIX shells; activate.ps1 on windows
```

</commands>

Activation redirects HOME, so git identity and ssh keys are absent inside an
activated shell. Build and test there; commit from a normal shell.

## Guarantees

- Exact toolset: the environment contains the union of what the named tags
  require and nothing else.
- Conflicts are errors before effects: two versions of one toolchain, an
  unknown tag, a version handed to a versionless target, or a target
  impossible on this host all fail during planning with a precise message,
  never mid-download.
- Idempotent: an interrupted or failed run is repaired by re-running the
  same command. `provision` with a different tag set reshapes the conda
  prefix to exactly that set but leaves stale publisher downloads under
  `<root>/tools`; run `clean` and re-provision for a byte-exact minimal
  root.

## Isolation

Every mutable path lives under the root: HOME, TMPDIR, XDG dirs, and each
toolchain's cache and config variables are redirected by the activation
script. The project checkout is written only when a build tool demands a
generated, ignored file (`local.properties` for Android). Nothing reads the
caller's HOME, dotfiles, or global toolchains; nothing writes outside the
root and the project.

Falsifier: run a build through `env -i` carrying only the activation
script. A pass proves independence from caller state.

<checklist for="isolation">

```bash
env -i /bin/sh -c '. <root>/activate.sh && cd <project> && <build-command>'
```

</checklist>

## Foreign-Architecture Binaries

Some publishers ship a build tool for exactly one platform:

| Host | Foreign linux-x86_64 binary runs via |
| --- | --- |
| linux/x86_64 | direct execution |
| linux/arm64 | qemu user-mode emulation against a conda-forge sysroot |
| macos/arm64 | Rosetta 2 for osx-64 binaries, transparently |
| windows | unsupported: emulation is a linux mechanism |

- macos/arm64 Android builds need Rosetta 2 once:
  `softwareupdate --install-rosetta --agree-to-license`.
- Emulated tools run slower: minutes for a full Android resource pipeline
  where native takes seconds. Correctness is unaffected.
- To run any other foreign binary a build needs, wrap it with `shim` and
  call the returned wrapper path.

## Gotchas

- A bare ubuntu:24.04 image with uv works: uv is the only assumption.
- Never hand-install into `<root>/conda/host` with a second call: the
  prefix create step replaces the whole prefix.
