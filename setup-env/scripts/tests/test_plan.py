"""The pure planner: Spec x Host -> Plan.

Planning performs no effects, so every law below is checkable without a
network, a toolchain, or a filesystem. These are the invariants provisioning
relies on before it starts deleting and downloading anything.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from btm_setup_env.catalog import CATALOG, Recipe
from btm_setup_env.model import (
    GENERIC,
    OS,
    Arch,
    CondaPlatform,
    DenvError,
    EnvDelta,
    Host,
    Layout,
    Target,
    make_spec,
)
from btm_setup_env.plan import make_plan
from btm_setup_env.steps import CondaEnv, stage_of

LINUX = Host(OS.LINUX, Arch.X86_64)
MAC = Host(OS.MACOS, Arch.ARM64)
WINDOWS = Host(OS.WINDOWS, Arch.X86_64)


def planned(*families: str, host: Host = LINUX, root: str = "/denv/root"):
    spec = make_spec(
        [Target((family, GENERIC), None) for family in families], Path("/proj")
    )
    return make_plan(spec, host, Layout(Path(root)))


def env_of(plan) -> dict[str, str]:
    return dict(plan.env.vars)


class TestPurity:
    def test_planning_twice_yields_an_equal_plan(self):
        """The plan is a value, which is what lets `plan` print exactly what
        `provision` would do."""
        assert planned("python", "go") == planned("python", "go")

    def test_target_order_does_not_change_the_plan(self):
        assert planned("go", "python").steps == planned("python", "go").steps


class TestCondaPrefixMerge:
    """micromamba create replaces a prefix rather than adding to it, so two
    creates against one prefix would silently drop the first one's packages.
    The planner merges them; a second create is unrepresentable in a valid
    plan, and these are the checks that keep it that way."""

    def prefixes(self, plan) -> list[str]:
        return [s.prefix_rel for s in plan.steps if isinstance(s, CondaEnv)]

    def test_one_prefix_appears_at_most_once(self):
        plan = planned("c", "cpp", "cmake", "ninja")
        assert len(self.prefixes(plan)) == len(set(self.prefixes(plan)))

    def test_packages_bound_for_one_prefix_are_unioned(self):
        alone = planned("cmake")
        together = planned("cmake", "ninja")
        host_alone = next(
            s for s in alone.steps if isinstance(s, CondaEnv) and s.prefix_rel
        )
        host_together = next(
            s
            for s in together.steps
            if isinstance(s, CondaEnv) and s.prefix_rel == host_alone.prefix_rel
        )
        assert set(host_alone.packages) < set(host_together.packages)

    def test_merged_packages_stay_sorted(self):
        for step in planned("c", "cpp", "cmake", "ninja").steps:
            if isinstance(step, CondaEnv):
                assert list(step.packages) == sorted(step.packages)


class TestStepOrder:
    def test_steps_are_non_decreasing_in_stage(self):
        """A shim over a toolchain that does not exist yet is the failure this
        ordering prevents."""
        stages = [stage_of(s) for s in planned("python", "c", "cmake").steps]
        assert stages == sorted(stages)

    def test_a_repeated_target_adds_no_step(self):
        """make_spec already refuses a duplicate key, so equal steps arriving
        from two different recipes are what deduplication has to catch."""
        assert len(set(planned("c", "cpp").steps)) == len(planned("c", "cpp").steps)


class TestIsolationFloor:
    """Caller state that leaks through well-known variables is the whole
    reason the root exists; each of these is a way out of it."""

    def test_home_is_redirected_under_the_root(self):
        assert env_of(planned("python"))["HOME"].startswith("/denv/root")

    def test_the_project_and_root_are_announced(self):
        env = env_of(planned("python"))
        assert env["DENV_PROJECT"] == "/proj"
        assert env["DENV_ROOT"] == "/denv/root"

    @pytest.mark.parametrize(
        "leak", ["VIRTUAL_ENV", "CONDA_PREFIX", "CONDA_DEFAULT_ENV", "CONDA_SHLVL"]
    )
    def test_an_ambient_activation_is_unset(self, leak):
        assert leak in planned("python").env.unset

    @pytest.mark.parametrize(
        "variable", ["TMPDIR", "XDG_CACHE_HOME", "XDG_CONFIG_HOME", "XDG_STATE_HOME"]
    )
    def test_posix_caches_land_under_the_root(self, variable):
        assert env_of(planned("python", host=LINUX))[variable].startswith("/denv/root")

    @pytest.mark.parametrize("variable", ["TEMP", "TMP", "USERPROFILE"])
    def test_windows_uses_its_own_variables(self, variable):
        assert env_of(planned("python", host=WINDOWS))[variable].startswith(
            "/denv/root"
        )

    def test_windows_does_not_carry_the_posix_names(self):
        assert "XDG_CACHE_HOME" not in env_of(planned("python", host=WINDOWS))

    def test_the_shims_directory_is_on_the_path(self):
        assert planned("python").layout.shims in planned("python").env.path


class TestProbes:
    def test_probes_keep_first_occurrence_order_without_repeats(self):
        probes = planned("c", "cpp", "cmake").probes
        assert len(probes) == len(set(probes))
        assert probes[0] in planned("c").probes


class TestConflict:
    """No catalog entry pairs conflict today, so this guard protects a future
    edit rather than a live path. Two recipes are injected to prove it fires;
    without that the branch is dead code nobody would notice breaking."""

    def recipe(self, name: str, platform: CondaPlatform):
        return Recipe(
            key=(name, GENERIC),
            summary=name,
            version_doc=None,
            requirements=lambda host, v: (CondaEnv("conda/host", platform, (name,)),),
            env=lambda layout, host: EnvDelta(),
            probes=(),
        )

    def test_one_prefix_claimed_for_two_platforms_is_refused(self, monkeypatch):
        for name, platform in (
            ("alpha", CondaPlatform.LINUX_64),
            ("beta", CondaPlatform.LINUX_AARCH64),
        ):
            monkeypatch.setitem(CATALOG, (name, GENERIC), self.recipe(name, platform))
        spec = make_spec(
            [Target(("alpha", GENERIC), None), Target(("beta", GENERIC), None)],
            Path("/proj"),
        )
        with pytest.raises(DenvError, match="claimed for two"):
            make_plan(spec, LINUX, Layout(Path("/denv/root")))

    def test_one_prefix_at_one_platform_merges_instead(self, monkeypatch):
        for name in ("alpha", "beta"):
            monkeypatch.setitem(
                CATALOG, (name, GENERIC), self.recipe(name, CondaPlatform.LINUX_64)
            )
        spec = make_spec(
            [Target(("alpha", GENERIC), None), Target(("beta", GENERIC), None)],
            Path("/proj"),
        )
        plan = make_plan(spec, LINUX, Layout(Path("/denv/root")))
        [merged] = [s for s in plan.steps if isinstance(s, CondaEnv)]
        assert merged.packages == ("alpha", "beta")
