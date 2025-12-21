from __future__ import annotations

import json
from pathlib import Path

from typing import Any


_RUBRIC_CACHE: dict[str, dict] = {}


def _rubric_base() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "rubrics"


def _normalize_track(track: str | None) -> str:
    t = (track or "").strip().lower()
    if not t:
        return "swe_intern"
    if t not in ("swe_intern", "swe_engineer", "behavioral"):
        return "swe_intern"
    return t


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def load_rubric(track: str | None) -> dict | None:
    key = _normalize_track(track)
    if key in _RUBRIC_CACHE:
        return _RUBRIC_CACHE[key]

    base = _rubric_base()
    path = base / f"{key}_rubric.json"
    data = _load_json(path)
    if data is None and key != "swe_intern":
        data = _load_json(base / "swe_intern_rubric.json")
        key = "swe_intern"

    if data:
        _RUBRIC_CACHE[key] = data
    return data


def rubric_to_text(rubric: dict | None) -> str:
    if not rubric:
        return ""

    lines: list[str] = []
    title = str(rubric.get("title") or "").strip()
    if title:
        lines.append(f"Rubric title: {title}")

    dims = rubric.get("dimensions", [])
    if isinstance(dims, list):
        for dim in dims:
            if not isinstance(dim, dict):
                continue
            name = str(dim.get("name") or "").strip()
            desc = str(dim.get("description") or "").strip()
            if not name:
                continue
            lines.append(f"Dimension: {name} (0-10)")
            if desc:
                lines.append(f"Description: {desc}")
            levels = dim.get("levels", [])
            if isinstance(levels, list):
                for level in levels:
                    if not isinstance(level, dict):
                        continue
                    range_label = str(level.get("range") or "").strip()
                    level_desc = str(level.get("description") or "").strip()
                    if range_label and level_desc:
                        lines.append(f"{range_label}: {level_desc}")
            lines.append("")

    overall = str(rubric.get("overall_scoring") or "").strip()
    if overall:
        lines.append(f"Overall scoring: {overall}")

    return "\n".join(lines).strip()


def build_rubric_context(track: str | None, include_behavioral: bool = False) -> str:
    parts: list[str] = []
    main = load_rubric(track)
    main_text = rubric_to_text(main)
    if main_text:
        parts.append(main_text)

    if include_behavioral:
        behavioral = load_rubric("behavioral")
        behavioral_text = rubric_to_text(behavioral)
        if behavioral_text:
            parts.append("Behavioral addendum:\n" + behavioral_text)

    return "\n\n".join(parts).strip()
