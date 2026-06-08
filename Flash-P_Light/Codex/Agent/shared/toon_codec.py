"""
Tiny TOON codec for FLASH-P **Light** — flat uniform-record arrays only.

TOON (Token-Oriented Object Notation) declares the columns ONCE in a header and writes
each record as a delimited row, removing the per-record keys that bloat JSON. We use it
only for the *flat, uniform, scalar* arrays (curated_edges, perturbation_dataset,
validation results, sensitivity grids, candidate papers). Nested/free-text files stay JSON.

Format (one table):

    name[N]{col1,col2,col3}:
    <tab-sep row 1>
    <tab-sep row 2>
    ... (N rows)

Design choices that make this SAFE:
  * **Tab-delimited.** A comma corrupts values like ``otsA (TPS overexpression, high T6P)``;
    tabs never occur in this data. ``encode`` REFUSES (raises ``ToonUnsafe``) if any value
    contains the delimiter or a newline, so the caller can fall back to JSON for that file.
  * **Pydantic is the type authority.** ``decode`` returns light-typed scalars (int/float/
    bool/str); feed the dicts to the Pydantic models for final coercion/validation.
  * **Length header.** ``decode`` checks the row count matches ``[N]`` (catches truncation).

This module has no third-party dependency. Run ``python toon_codec.py`` for the self-test.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

DELIM = "\t"
_HEADER_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)\[(?P<n>\d+)\]\{(?P<cols>[^}]*)\}:\s*$")


class ToonError(ValueError):
    """Malformed TOON text."""


class ToonUnsafe(ValueError):
    """A value collides with the delimiter — caller should fall back to JSON."""


def _cell(v: Any) -> str:
    return "" if v is None else str(v)


def _parse_scalar(s: str) -> Any:
    if s == "":
        return ""
    if s == "True":
        return True
    if s == "False":
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d*\.\d+", s):
        return float(s)
    return s


def encode(name: str, columns: Sequence[str], rows: Sequence[Sequence[Any]],
           delim: str = DELIM) -> str:
    """Encode a flat table. Raises ``ToonUnsafe`` if any value contains the delimiter."""
    lines = [f"{name}[{len(rows)}]{{{','.join(columns)}}}:"]
    for r in rows:
        cells = [_cell(v) for v in r]
        for c in cells:
            if delim in c or "\n" in c:
                raise ToonUnsafe(f"value contains delimiter/newline: {c!r}")
        lines.append(delim.join(cells))
    return "\n".join(lines)


def encode_records(name: str, columns: Sequence[str], records: Sequence[Dict[str, Any]],
                   delim: str = DELIM) -> str:
    """Encode a list of dicts, pulling ``columns`` in order from each record."""
    rows = [[rec.get(c) for c in columns] for rec in records]
    return encode(name, columns, rows, delim)


def is_toon(text: str) -> bool:
    """True if ``text`` looks like a TOON table (vs JSON)."""
    return bool(_HEADER_RE.match(text.lstrip().splitlines()[0])) if text.strip() else False


def decode(text: str, delim: str = DELIM) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """Decode a TOON table → (name, columns, [record dict, ...]) with light typing."""
    lines = text.splitlines()
    if not lines:
        raise ToonError("empty TOON text")
    m = _HEADER_RE.match(lines[0].strip())
    if not m:
        raise ToonError(f"bad TOON header: {lines[0]!r}")
    name = m["name"]
    columns = [c for c in m["cols"].split(",") if c != ""]
    body = [ln for ln in lines[1:] if ln.strip() != ""]
    records: List[Dict[str, Any]] = []
    for ln in body:
        values = ln.split(delim)
        if len(values) != len(columns):
            raise ToonError(
                f"row has {len(values)} cells, expected {len(columns)}: {ln!r}"
            )
        records.append({c: _parse_scalar(v) for c, v in zip(columns, values)})
    declared = int(m["n"])
    if len(records) != declared:
        raise ToonError(f"row count {len(records)} != declared [{declared}]")
    return name, columns, records


def try_encode_records(name: str, columns: Sequence[str],
                       records: Sequence[Dict[str, Any]], delim: str = DELIM):
    """Encode, or return ``None`` on a delimiter collision (signal: keep JSON)."""
    try:
        return encode_records(name, columns, records, delim)
    except ToonUnsafe:
        return None


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample = [
        {"eid": "E001", "s": "ABA", "t": "Auxin", "x": -1, "d": ""},
        {"eid": "E002", "s": "ABA", "t": "HB21", "x": 1, "d": "10.1073/pnas.1613199114"},
        {"eid": "E003", "s": "BRC1", "t": "Shoot_Branching", "x": -1, "d": "10.1105/tpc.106.048934"},
    ]
    cols = ["eid", "s", "t", "x", "d"]
    text = encode_records("edges", cols, sample)
    name, decoded_cols, back = decode(text)
    assert name == "edges" and decoded_cols == cols, (name, decoded_cols)
    assert back == sample, f"round-trip mismatch:\n{sample}\n{back}"
    # delimiter-collision detection -> caller falls back to JSON
    unsafe = [{"id": "T1", "g": "otsA (TPS overexpression, high T6P)"}]
    assert try_encode_records("P", ["id", "g"], unsafe, delim=",") is None
    assert try_encode_records("P", ["id", "g"], unsafe, delim="\t") is not None
    print("toon_codec self-test: OK")
    print("--- sample TOON ---")
    print(text)
