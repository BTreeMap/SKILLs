"""Rules over synthetic trees: each convention checked against a built tree."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from btm_repo_gate.cli import find_root, repair_to_fixpoint
from btm_repo_gate.repairs import _relative_target
from btm_repo_gate.rules import audit
from btm_repo_gate.snapshot import snapshot

SKILL = """---
name: {name}
description: >-
  Does a thing worth naming. Use when the user asks for that thing.
license: MIT
---

# Title

Body.
"""


@pytest.fixture
def repo(tmp_path):
    """A minimal tree the gate recognizes: manifests, AGENTS.md, one skill."""
    (tmp_path / ".claude-plugin").mkdir()
    (tmp_path / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "btm-skills", "plugins": []}), encoding="utf-8"
    )
    (tmp_path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": "btm-skills"}), encoding="utf-8"
    )
    (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    kernel = tmp_path / ".corekit" / "src" / "btm_corekit"
    kernel.mkdir(parents=True)
    # The guarded set is read off this file, so the rule and the kernel
    # cannot disagree about what the kernel defines.
    (kernel / "identifiers.py").write_text(
        "def mint(words):\n    return 1\n\n\ndef resolve(ref, ids):\n"
        "    return ref\n\n\nclass Exact:\n    pass\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Readme\n", encoding="utf-8")
    skill = tmp_path / "alpha"
    skill.mkdir()
    (skill / "SKILL.md").write_text(SKILL.format(name="alpha"), encoding="utf-8")
    return tmp_path


def rules_hit(root) -> set[str]:
    return {finding.rule for finding in audit(snapshot(root))}


class TestFindRoot:
    def test_the_marketplace_manifest_marks_the_root(self, repo):
        assert find_root(repo) == repo

    def test_a_nested_directory_still_finds_it(self, repo):
        assert find_root(repo / "alpha") == repo

    def test_a_tree_without_the_manifest_is_refused(self, tmp_path):
        with pytest.raises(SystemExit, match="not a skills repository"):
            find_root(tmp_path)


# Escaped because this file is scanned for the forbidden character.
EM_DASH = "\u2014"


class TestEmDash:
    def test_an_em_dash_anywhere_is_a_finding(self, repo):
        (repo / "alpha" / "SKILL.md").write_text(
            SKILL.format(name="alpha").replace("Body.", f"Body {EM_DASH} more."),
            encoding="utf-8",
        )
        assert "em-dash" in rules_hit(repo)

    def test_a_clean_tree_reports_no_em_dash(self, repo):
        assert "em-dash" not in rules_hit(repo)


class TestFrontmatter:
    def test_a_name_disagreeing_with_its_directory_is_a_finding(self, repo):
        (repo / "alpha" / "SKILL.md").write_text(
            SKILL.format(name="beta"), encoding="utf-8"
        )
        assert "frontmatter" in rules_hit(repo)

    def test_a_missing_license_is_a_finding(self, repo):
        text = SKILL.format(name="alpha").replace("license: MIT\n", "")
        (repo / "alpha" / "SKILL.md").write_text(text, encoding="utf-8")
        assert "frontmatter" in rules_hit(repo)

    def test_an_overlong_description_is_a_finding(self, repo):
        text = SKILL.format(name="alpha").replace(
            "Does a thing worth naming.", "x" * 1100
        )
        (repo / "alpha" / "SKILL.md").write_text(text, encoding="utf-8")
        assert "frontmatter" in rules_hit(repo)


class TestSkillLayout:
    def test_a_directory_without_a_skill_file_is_a_finding(self, repo):
        (repo / "orphan").mkdir()
        (repo / "orphan" / "notes.md").write_text("text\n", encoding="utf-8")
        assert "skill-layout" in rules_hit(repo)


class TestAliases:
    def test_a_missing_hub_alias_is_repaired(self, repo):
        _, remaining = repair_to_fixpoint(repo)
        assert (repo / "skills" / "alpha").is_symlink()
        assert not [f for f in remaining if f.repair is not None]

    def test_the_hub_alias_points_at_the_skill(self, repo):
        repair_to_fixpoint(repo)
        link = repo / "skills" / "alpha"
        assert link.resolve() == (repo / "alpha").resolve()

    def test_an_alias_for_a_removed_skill_is_swept(self, repo):
        repair_to_fixpoint(repo)
        shutil.rmtree(repo / "alpha")
        repair_to_fixpoint(repo)
        assert not (repo / "skills" / "alpha").exists()

    def test_repairs_reach_a_fixpoint(self, repo):
        repair_to_fixpoint(repo)
        applied, _ = repair_to_fixpoint(repo)
        assert applied == []


class TestRelativeTarget:
    def test_a_hub_alias_targets_its_sibling(self):
        assert _relative_target(Path("skills/alpha"), Path("alpha")) == "../alpha"

    def test_a_self_link_is_a_defect(self):
        with pytest.raises(AssertionError, match="self-link"):
            _relative_target(Path("skills"), Path("skills"))


def write_member(skill: Path, name: str, dependencies: str = "") -> Path:
    """A conforming member: manifest and code under `<skill>/scripts/`."""
    member = skill / "scripts"
    member.mkdir(exist_ok=True)
    (member / "pyproject.toml").write_text(
        f'[project]\nname = "btm-{name}"\ndependencies = [{dependencies}]\n',
        encoding="utf-8",
    )
    return member


class TestKernel:
    def test_a_consumer_redefining_a_kernel_symbol_is_a_finding(self, repo):
        member = write_member(repo / "alpha", "alpha", '"btm-corekit"')
        (member / "code.py").write_text("def mint(words):\n    return 1\n", "utf-8")
        assert "kernel" in rules_hit(repo)

    def test_a_non_consumer_may_define_the_same_name(self, repo):
        """A name collision outside a consumer is not a smuggled kernel copy."""
        member = write_member(repo / "alpha", "alpha")
        (member / "code.py").write_text(
            "def resolve(x):\n    return x\n", encoding="utf-8"
        )
        assert "kernel" not in rules_hit(repo)

    def test_the_guarded_set_is_read_off_the_kernel(self, repo):
        """A symbol added to the kernel is guarded without editing this rule."""
        kernel = repo / ".corekit" / "src" / "btm_corekit" / "identifiers.py"
        kernel.write_text(
            kernel.read_text() + "\n\ndef minted_today(x):\n    return x\n"
        )
        member = write_member(repo / "alpha", "alpha", '"btm-corekit"')
        (member / "code.py").write_text(
            "def minted_today(x):\n    return x\n", encoding="utf-8"
        )
        assert "kernel" in rules_hit(repo)

    def test_a_private_kernel_helper_is_not_guarded(self, repo):
        """Underscored names are the kernel's own business."""
        kernel = repo / ".corekit" / "src" / "btm_corekit" / "identifiers.py"
        kernel.write_text(kernel.read_text() + "\n\ndef _private(x):\n    return x\n")
        member = write_member(repo / "alpha", "alpha", '"btm-corekit"')
        (member / "code.py").write_text("def _private(x):\n    return x\n", "utf-8")
        assert "kernel" not in rules_hit(repo)

    def test_a_legacy_kernel_symlink_is_swept(self, repo):
        (repo / "alpha" / ".corekit").symlink_to("../.corekit")
        repair_to_fixpoint(repo)
        assert not (repo / "alpha" / ".corekit").is_symlink()


class TestMemberLayout:
    def test_a_conforming_member_is_no_finding(self, repo):
        member = write_member(repo / "alpha", "alpha")
        (member / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
        assert "member-layout" not in rules_hit(repo)

    def test_python_outside_the_member_is_a_finding(self, repo):
        (repo / "alpha" / "loose.py").write_text("VALUE = 1\n", encoding="utf-8")
        assert "member-layout" in rules_hit(repo)

    def test_member_code_without_a_manifest_is_a_finding(self, repo):
        member = repo / "alpha" / "scripts"
        member.mkdir()
        (member / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
        assert "member-layout" in rules_hit(repo)

    def test_a_manifest_at_the_skill_root_is_a_finding(self, repo):
        (repo / "alpha" / "pyproject.toml").write_text(
            '[project]\nname = "btm-alpha"\n', encoding="utf-8"
        )
        assert "member-layout" in rules_hit(repo)
