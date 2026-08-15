"""Pure planner: Spec x Host -> Plan.

The plan is a value: a deterministic, sorted, deduplicated tuple of steps
plus the merged activation delta and the probe set. Planning performs no
effects, so `envctl plan` can print exactly what `provision` would do, and
tests can assert on plans without a network.
"""

from __future__ import annotations

from dataclasses import dataclass

from .catalog import CATALOG, Recipe, conda_bin_dirs
from .model import OS, DenvError, EnvDelta, Host, Layout, Spec, merge_deltas
from .steps import CondaEnv, Step, sort_key


@dataclass(frozen=True, slots=True)
class Plan:
    spec: Spec
    host: Host
    layout: Layout
    steps: tuple[Step, ...]
    env: EnvDelta  # merged, host-resolved delta
    probes: tuple[tuple[str, ...], ...]  # deduplicated, order-stable


def _base_env(layout: Layout, host: Host, spec: Spec) -> EnvDelta:
    """The isolation floor every environment gets: caller state that leaks
    through well-known variables is redirected under the root."""
    vars_: list[tuple[str, str]] = [
        ("DENV_PROJECT", str(spec.project)),
        ("DENV_ROOT", str(layout.root)),
        ("HOME", str(layout.home)),
    ]
    if host.os is OS.WINDOWS:
        vars_ += [
            ("TEMP", str(layout.tmp)),
            ("TMP", str(layout.tmp)),
            ("USERPROFILE", str(layout.home)),
        ]
    else:
        vars_ += [
            ("TMPDIR", str(layout.tmp)),
            ("XDG_CACHE_HOME", str(layout.cache / "xdg")),
            ("XDG_CONFIG_HOME", str(layout.home / ".config")),
            ("XDG_DATA_HOME", str(layout.home / ".local" / "share")),
            ("XDG_STATE_HOME", str(layout.home / ".local" / "state")),
        ]
    return EnvDelta(
        vars=tuple(vars_),
        path=(layout.shims,),
        unset=frozenset(
            {"CONDA_DEFAULT_ENV", "CONDA_PREFIX", "CONDA_SHLVL", "VIRTUAL_ENV"}
        ),
    )


def make_plan(spec: Spec, host: Host, layout: Layout) -> Plan:
    recipes: list[tuple[Recipe, str | None]] = [
        (CATALOG[t.key], t.version) for t in spec.targets
    ]

    # Gather steps. Recipes validate host support here, so an impossible
    # (target, host) pair dies before any effect runs.
    gathered: list[Step] = []
    for recipe, version in recipes:
        gathered.extend(recipe.requirements(host, version))

    # Law: one conda prefix, one create call. Merge every CondaEnv bound for
    # the same prefix into a single step with the union of its packages.
    by_prefix: dict[str, CondaEnv] = {}
    rest: list[Step] = []
    for step in gathered:
        if not isinstance(step, CondaEnv):
            rest.append(step)
            continue
        platform = step.platform or host.conda_platform
        prior = by_prefix.get(step.prefix_rel)
        if prior is not None and prior.platform != platform:
            raise DenvError(
                f"prefix {step.prefix_rel} claimed for two "
                f"platforms: {prior.platform.value} and "
                f"{platform.value}"
            )
        packages = set(prior.packages if prior else ()) | set(step.packages)
        by_prefix[step.prefix_rel] = CondaEnv(
            step.prefix_rel, platform, tuple(sorted(packages))
        )

    steps = tuple(sorted(set(rest) | set(by_prefix.values()), key=sort_key))

    # The environment is the base floor, then each recipe's delta in target
    # order, then the conda host bin directories when a host prefix exists.
    deltas = [_base_env(layout, host, spec)]
    deltas += [recipe.env(layout, host) for recipe, _ in recipes]
    if "conda/host" in by_prefix:
        # conda packages' own wrapper scripts resolve ${CONDA_PREFIX}, so an
        # activated environment must define it; it points inside the root.
        deltas.append(
            EnvDelta(
                vars=(("CONDA_PREFIX", str(layout.conda_host)),),
                path=conda_bin_dirs(layout, host),
            )
        )
    env = merge_deltas(deltas)

    probes: list[tuple[str, ...]] = []
    for recipe, _ in recipes:
        for probe in recipe.probes:
            if probe not in probes:
                probes.append(probe)

    return Plan(spec, host, layout, steps, env, tuple(probes))
