"""Ken French daily factor files: FF5 and momentum, stored as events of the
symbol `_factors`, in decimal; the date is both event and knowledge time."""

from __future__ import annotations

import io
import zipfile

import numpy as np

from btm_corekit import Model, UpstreamError, get_bytes
from btm_finance.data.sources import client
from btm_finance.data.tables import EventRows, Loaded, concat_events, days, texts

BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = (
    "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip",
    "F-F_Momentum_Factor_daily_CSV.zip",
)
SYMBOL = "_factors"
FIELDS = {
    "mkt-rf": "mkt_rf",
    "smb": "smb",
    "hml": "hml",
    "rmw": "rmw",
    "cma": "cma",
    "rf": "rf",
    "mom": "mom",
}
MISSING = (-99.99, -999.0)
CAP = 64 * 1024 * 1024
DATE_DIGITS = 8


class FrenchConfig(Model):
    """No settings yet; an empty object is accepted."""


def unzipped(data: bytes, where: str) -> str:
    """The one CSV inside a French zip, as text."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if len(names) != 1:
                raise UpstreamError(f"{where} holds {len(names)} CSV files, not 1")
            return archive.read(names[0]).decode("latin-1")
    except zipfile.BadZipFile as err:
        raise UpstreamError(f"{where} is no zip archive: {err}") from err


def parse(text: str, where: str) -> EventRows:
    """The first table: a header line starting with a comma, then rows
    `YYYYMMDD, v1, ...` in percent, until the first other line."""
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.lstrip().startswith(",")), None
    )
    if start is None:
        raise UpstreamError(f"{where} has no header line; the file layout changed")
    header = [cell.strip().lower() for cell in lines[start].split(",")[1:]]
    unknown = [name for name in header if name not in FIELDS]
    if unknown:
        raise UpstreamError(f"{where} has unknown column(s) {', '.join(unknown)}")
    stamps: list[str] = []
    values: list[list[float]] = []
    for line in lines[start + 1 :]:
        cells = [cell.strip() for cell in line.split(",")]
        stamp = cells[0]
        if len(stamp) != DATE_DIGITS or not stamp.isdigit():
            break
        if len(cells) != len(header) + 1:
            raise UpstreamError(f"{where} row {stamp} has {len(cells) - 1} values")
        stamps.append(f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:]}")
        try:
            values.append([float(cell) for cell in cells[1:]])
        except ValueError:
            raise UpstreamError(f"{where} row {stamp} holds a non-number") from None
    on = days(stamps, where)
    grid = np.asarray(values, dtype=np.float64).reshape(len(stamps), len(header))
    parts: list[EventRows] = []
    for column, name in enumerate(header):
        raw = grid[:, column]
        keep = ~np.isin(raw, MISSING)
        count = int(keep.sum())
        parts.append(
            EventRows(
                texts([SYMBOL] * count),
                texts([FIELDS[name]] * count),
                on[keep],
                on[keep],
                raw[keep] / 100.0,
            )
        )
    found = concat_events(parts)
    if found is None:
        raise UpstreamError(f"{where} has no factor columns")
    return found


def fetch(config: FrenchConfig) -> Loaded:
    del config
    parts = []
    for name in FILES:
        url = BASE + name
        parts.append(parse(unzipped(get_bytes(client(), url, CAP), url), url))
    return Loaded(None, concat_events(parts))
