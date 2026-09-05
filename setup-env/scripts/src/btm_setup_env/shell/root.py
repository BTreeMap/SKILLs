"""The environment root: what it records about itself, and reading it back.

The manifest is the root's own account of the project and tags it holds.
Every executor writes through one context, so status and provision cannot
disagree about what is installed."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import certifi
from pydantic import ConfigDict
from pydantic import Field as PydanticField

from btm_corekit import (
    Model,
    dump,
    parse_model,
)
from btm_setup_env.model import (
    OS,
    DenvError,
    Host,
    Layout,
)


class Manifest(Model):
    """What a provisioned root records about itself. One reading, so status
    and the executors cannot disagree about which project it belongs to; an
    older manifest missing a field is read, not rejected."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    project: str = ""
    spec: tuple[str, ...] = ()
    host: str = ""
    conda: dict[str, tuple[str, ...]] = PydanticField(default_factory=dict)
    uv_python: str | None = None


@dataclass
class Ctx:
    layout: Layout
    host: Host
    manifest: Manifest = field(default_factory=Manifest)

    @property
    def mamba(self) -> Path:
        name = "micromamba.exe" if self.host.os is OS.WINDOWS else "micromamba"
        return self.layout.mamba_bin.with_name(name)

    def tool_env(self, **extra: str) -> dict[str, str]:
        env = dict(os.environ)
        env.update(
            HOME=str(self.layout.home),
            TMPDIR=str(self.layout.tmp),
            SSL_CERT_FILE=certifi.where(),
            MAMBA_ROOT_PREFIX=str(self.layout.mamba_root),
        )
        env.update(extra)
        return env

    def record(self, **changes: object) -> None:
        self.manifest = self.manifest.with_(**changes)

    def save_manifest(self) -> None:
        path = self.layout.manifest
        partial = path.with_name(path.name + ".partial")
        partial.write_text(json.dumps(dump(self.manifest), indent=2, sort_keys=True))
        os.replace(partial, path)


@dataclass(frozen=True, slots=True)
class Unprovisioned:
    """No manifest here, or one naming no project. Either way this tool made
    nothing at this root."""


@dataclass(frozen=True, slots=True)
class Provisioned:
    manifest: Manifest


Root = Unprovisioned | Provisioned


def read_root(layout: Layout) -> Root:
    """What stands at this root. A root with no manifest was never
    provisioned; one that fails to parse is not the same thing, so it errors
    instead of reading as absent and forcing a reinstall."""
    try:
        raw = layout.manifest.read_text()
    except OSError:
        return Unprovisioned()
    try:
        manifest = parse_model(Manifest, json.loads(raw), str(layout.manifest))
    except ValueError as err:
        raise DenvError(f"unreadable {layout.manifest}: {err}") from err
    return Provisioned(manifest) if manifest.project else Unprovisioned()


def manifest_of(root: Root) -> Manifest:
    """The manifest to build on. A fresh root starts from an empty one, which
    is a beginning rather than a stand-in for absence."""
    match root:
        case Provisioned(manifest):
            return manifest
        case Unprovisioned():
            return Manifest()


def ensure_dirs(layout: Layout) -> None:
    for directory in (
        layout.root,
        layout.downloads,
        layout.home,
        layout.tmp,
        layout.cache,
        layout.shims,
        layout.home / ".config",
    ):
        directory.mkdir(parents=True, exist_ok=True)
