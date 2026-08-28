"""The pure domain: tag grammar, spec law, and the emulation decision."""

from __future__ import annotations

from pathlib import Path

import pytest

from btm_setup_env.model import (
    GENERIC,
    OS,
    Arch,
    CondaPlatform,
    DenvError,
    Host,
    Native,
    QemuUser,
    RawTag,
    Rosetta,
    Unsupported,
    emulation,
    make_spec,
    parse_tag,
)


class TestTagGrammar:
    def test_a_bare_family_takes_the_generic_flavor(self):
        assert parse_tag("python") == RawTag("python", GENERIC, None)

    def test_a_flavor_is_read_after_the_colon(self):
        assert parse_tag("kotlin:android") == RawTag("kotlin", "android", None)

    def test_a_version_is_read_after_the_at_sign(self):
        assert parse_tag("python@3.12") == RawTag("python", GENERIC, "3.12")

    def test_flavor_and_version_compose(self):
        assert parse_tag("go:cgo@1.22") == RawTag("go", "cgo", "1.22")

    def test_surrounding_space_and_case_are_normalized(self):
        assert parse_tag("  Python@3.12  ") == RawTag("python", GENERIC, "3.12")

    @pytest.mark.parametrize(
        "text", ["", "9lives", "python@", "python:", ":android", "py thon", "a@b@c"]
    )
    def test_malformed_tags_are_refused(self, text):
        with pytest.raises(DenvError, match="malformed tag"):
            parse_tag(text)


class TestSpecLaw:
    def test_an_empty_target_list_is_refused(self):
        with pytest.raises(DenvError, match="no targets given"):
            make_spec([], Path("/p"))


class TestEmulation:
    LINUX_ARM = Host(os=OS.LINUX, arch=Arch.ARM64)
    LINUX_X86 = Host(os=OS.LINUX, arch=Arch.X86_64)
    MAC_ARM = Host(os=OS.MACOS, arch=Arch.ARM64)

    def test_a_matching_platform_needs_no_emulation(self):
        assert isinstance(
            emulation(self.LINUX_ARM, self.LINUX_ARM.conda_platform), Native
        )

    def test_linux_reaches_a_foreign_platform_through_qemu(self):
        assert isinstance(emulation(self.LINUX_ARM, CondaPlatform.LINUX_64), QemuUser)

    def test_apple_silicon_reaches_intel_through_rosetta(self):
        assert isinstance(emulation(self.MAC_ARM, CondaPlatform.OSX_64), Rosetta)

    def test_an_unreachable_platform_says_why(self):
        result = emulation(self.MAC_ARM, CondaPlatform.LINUX_64)
        assert isinstance(result, Unsupported)
        assert "qemu user-mode emulation exists only on linux" in result.reason

    def test_the_decision_is_total_over_every_platform(self):
        """No host and platform pair falls through without an answer."""
        for host in (self.LINUX_ARM, self.LINUX_X86, self.MAC_ARM):
            for platform in CondaPlatform:
                assert emulation(host, platform) is not None
