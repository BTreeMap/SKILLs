"""Env deltas compose as a monoid, and render to shell scripts that quote."""

from __future__ import annotations

from pathlib import Path

import pytest

from btm_setup_env.model import OS, Arch, DenvError, EnvDelta, Host
from btm_setup_env.render import realize, render_ps1, render_sh

LINUX = Host(os=OS.LINUX, arch=Arch.X86_64)
WINDOWS = Host(os=OS.WINDOWS, arch=Arch.X86_64)


class TestDeltaMonoid:
    """`__add__` folds deltas, so it needs an identity and associativity."""

    def test_the_empty_delta_is_a_left_identity(self):
        one = EnvDelta(vars=(("K", "v"),))
        assert EnvDelta() + one == one

    def test_the_empty_delta_is_a_right_identity(self):
        one = EnvDelta(vars=(("K", "v"),))
        assert one + EnvDelta() == one

    def test_composition_is_associative(self):
        a = EnvDelta(vars=(("A", "1"),), path=(Path("/a"),))
        b = EnvDelta(vars=(("B", "2"),), path=(Path("/b"),))
        c = EnvDelta(vars=(("C", "3"),), path=(Path("/c"),))
        assert (a + b) + c == a + (b + c)

    def test_two_recipes_disagreeing_on_one_variable_is_refused(self):
        """Silent overwrite would make the winning recipe depend on fold order."""
        first = EnvDelta(vars=(("K", "old"),))
        second = EnvDelta(vars=(("K", "new"),))
        with pytest.raises(DenvError, match="recipes disagree"):
            first + second

    def test_agreeing_recipes_merge_without_complaint(self):
        same = EnvDelta(vars=(("K", "v"),))
        assert dict(realize(same + same, LINUX))["K"] == "v"


class TestPosixRendering:
    def test_a_variable_is_exported(self):
        script = render_sh(EnvDelta(vars=(("HOME", "/tmp/root"),)), LINUX)
        assert "HOME" in script and "/tmp/root" in script

    def test_a_path_entry_appears_in_the_script(self):
        script = render_sh(EnvDelta(path=(Path("/tmp/bin"),)), LINUX)
        assert "/tmp/bin" in script and "PATH" in script

    def test_an_empty_delta_still_renders_a_usable_script(self):
        assert render_sh(EnvDelta(), LINUX).strip()

    def test_a_value_with_spaces_is_quoted(self):
        script = render_sh(EnvDelta(vars=(("K", "two words"),)), LINUX)
        assert "'two words'" in script or '"two words"' in script

    def test_an_unset_variable_is_unset(self):
        script = render_sh(EnvDelta(unset=frozenset({"GONE"})), LINUX)
        assert "GONE" in script


class TestPowerShellRendering:
    def test_a_variable_reaches_the_environment_scope(self):
        script = render_ps1(EnvDelta(vars=(("K", "v"),)), WINDOWS)
        assert "env:" in script.lower() and "K" in script

    def test_a_path_entry_appears(self):
        script = render_ps1(EnvDelta(path=(Path("C:/bin"),)), WINDOWS)
        assert "C:/bin" in script or "C:\\bin" in script

    def test_a_single_quote_in_a_value_is_escaped(self):
        script = render_ps1(EnvDelta(vars=(("K", "it's"),)), WINDOWS)
        assert "''" in script

    def test_an_empty_delta_still_renders(self):
        assert render_ps1(EnvDelta(), WINDOWS).strip()


class TestRealize:
    def test_realize_reports_the_variables_a_delta_sets(self):
        assert dict(realize(EnvDelta(vars=(("K", "v"),)), LINUX))["K"] == "v"

    @pytest.mark.parametrize("host", [LINUX, WINDOWS])
    def test_realize_is_total_across_hosts(self, host):
        assert isinstance(realize(EnvDelta(vars=(("K", "v"),)), host), dict)
