# Targets

The authoritative tag list lives in `catalog` and prints via `btm-setup-env list`;
this file adds the judgment calls the one-line summaries omit. Aliases:
`js`/`node`, `ts`, `py`, `golang`, `c++`, `cs`/`dotnet`, `sh`/`shell`, and
bare `android` for `java:android`.

## Per-Target Notes

| Tag | Supplier | Worth knowing |
| --- | --- | --- |
| `python` | uv | Managed CPython plus a seeded venv; `UV_PYTHON_PREFERENCE=only-managed` keeps a host python from leaking in. uv itself is linked into the root so it survives activation. |
| `javascript` | conda-forge | nodejs + npm; npm cache redirected. Global installs land in the prefix, which is writable and disposable. |
| `typescript` | conda-forge | nodejs + the tsc compiler as a conda package; no npm involvement at provision time. |
| `go` | conda-forge | `GOTOOLCHAIN=local` pins the running toolchain; GOPATH and build cache live under the root. |
| `go:cgo` | conda-forge | Adds the C toolchain and exports `CGO_ENABLED=1` and `CC`. A flavor because it changes the toolchain, not the source. |
| `rust` | conda-forge | rustc + cargo + a C toolchain, because a rustc that cannot link is not a toolchain. `CARGO_HOME` under the root. |
| `c`, `cpp` | conda-forge | `c-compiler`/`cxx-compiler` metapackages resolve to gcc on linux, clang on macos. `CC`/`CXX` point at fixed-name shims, so plans never mention a compiler triple. Not on windows (MSVC needs its own activation). |
| `java` | conda-forge | A JDK; `JAVA_HOME` points inside the prefix at `lib/jvm`, never at the prefix itself. |
| `kotlin` | conda-forge | kotlinc for generic JVM work; the solver brings a JDK, one solve keeps them consistent. |
| `kotlin:android`, `java:android` | Google + conda-forge | JDK + cmdline-tools + platform, build-tools, platform-tools for the API level given as `@version`. Deliberately installs no gradle and no kotlin: the project's gradlew and plugins are authoritative. Writes `sdk.dir` into `local.properties` only when the project has gradle files. On linux/arm64, provisions the emulated aapt2 described in `SKILL.md`. |
| `kotlin:native` | JetBrains + conda-forge | Prebuilt Kotlin/Native plus a JDK; `KONAN_DATA_DIR` under the root. Closed host set (linux-64, osx-64, osx-arm64, win-64): JetBrains publishes no linux/arm64 host prebuilt, and the error says so. |
| `gradle`, `maven`, `cmake`, `ninja` | conda-forge | Standalone build tools for projects without a committed wrapper. Prefer the project's gradlew when one exists. |
| `csharp` | conda-forge | .NET SDK; the conda package ships no bin wrapper, so the recipe exports `DOTNET_ROOT` and puts it on PATH. Telemetry opted out. |
| `haskell` | haskell.org + conda-forge | ghcup drives ghc + cabal into the root; conda supplies curl, tar, xz, gmp, ncurses, and a C toolchain that GHC needs to configure and link. Best effort: budget roughly 7 GB and minutes of unpacking. `LD_LIBRARY_PATH` is set to the prefix's lib, scoped to environments that requested haskell. Not on windows. |
| `bash` | conda-forge | bash + shellcheck + shfmt (packaged as `go-shfmt`). Not on windows. |

## Version Semantics

`@version` is recipe-defined and documented per row in `btm-setup-env list`:
conda-supplied targets take a conda version spec (`java@21`, `go@1.23`),
`python` takes a uv interpreter spec, android flavors take an API level
(`kotlin:android@35` installs `platforms;android-35` + matching
build-tools), `kotlin:native` takes a JetBrains release. Targets without a
version axis (`c`, `cpp`) reject one at parse time.

## Footprints

Rough per-target root sizes, dominated by downloads: python or typescript
0.3 GB; go, rust, or a JVM 0.5-1 GB; android 2 GB (plus 0.5 GB for the
emulated toolchain on arm64); haskell 7 GB. Sizes add sublinearly within
one conda prefix.
