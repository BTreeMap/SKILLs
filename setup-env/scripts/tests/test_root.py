"""What stands at an environment root, and what a fresh one starts from."""

from __future__ import annotations

import json

import pytest

from btm_setup_env.model import DenvError, Layout
from btm_setup_env.shell.root import (
    Manifest,
    Provisioned,
    Unprovisioned,
    manifest_of,
    read_root,
)


@pytest.fixture
def layout(tmp_path) -> Layout:
    return Layout(tmp_path)


def written(layout: Layout, **fields: object) -> None:
    layout.manifest.parent.mkdir(parents=True, exist_ok=True)
    layout.manifest.write_text(json.dumps(fields), encoding="utf-8")


class TestReadRoot:
    def test_nothing_there_is_unprovisioned(self, layout):
        assert read_root(layout) == Unprovisioned()

    def test_a_manifest_naming_a_project_is_provisioned(self, layout):
        written(layout, project="/w/app", spec=["python"], host="linux-64")
        root = read_root(layout)
        assert isinstance(root, Provisioned)
        assert root.manifest.project == "/w/app"
        assert root.manifest.spec == ("python",)

    def test_a_manifest_naming_no_project_is_unprovisioned(self, layout):
        """The empty manifest used to be the stand-in for absence, so this is
        the case the sum has to keep answering the same way."""
        written(layout, spec=["python"])
        assert read_root(layout) == Unprovisioned()

    def test_an_unreadable_manifest_is_not_absence(self, layout):
        """Reading it as absent would tell an agent to reinstall a root that
        is already there."""
        layout.manifest.parent.mkdir(parents=True, exist_ok=True)
        layout.manifest.write_text("{not json", encoding="utf-8")
        with pytest.raises(DenvError, match="unreadable"):
            read_root(layout)

    def test_a_field_a_later_version_added_is_read_anyway(self, layout):
        written(layout, project="/w/app", invented_next_year=1)
        assert isinstance(read_root(layout), Provisioned)


class TestManifestOf:
    def test_a_fresh_root_starts_from_an_empty_manifest(self):
        assert manifest_of(Unprovisioned()) == Manifest()

    def test_an_existing_root_builds_on_what_it_recorded(self):
        held = Manifest(project="/w/app", uv_python="3.12")
        assert manifest_of(Provisioned(held)) is held
