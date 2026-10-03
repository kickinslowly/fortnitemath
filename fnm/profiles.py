"""Render profiles (PROTOCOL §7). Baked text is canonical; emitters apply a profile."""
from __future__ import annotations

import copy
import re

PROFILES = ("unicode", "ascii")

_SUPER = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_DIGIT_EXP = re.compile(r"\^(\d+)")
ASCII_MAP = {
    "×": "*", "÷": "/", "−": "-", "≤": "<=", "≥": ">=",
    "≠": "!=", "√": "sqrt", "π": "pi",
}


def render(text: str, profile: str) -> str:
    if profile == "unicode":
        # Only a run of digits directly after ^ becomes superscript; 2^(1 + 1) stays.
        return _DIGIT_EXP.sub(lambda m: m.group(1).translate(_SUPER), text)
    if profile == "ascii":
        for k, v in ASCII_MAP.items():
            text = text.replace(k, v)
        return text
    raise ValueError(f"unknown profile {profile!r} (expected one of {PROFILES})")


def apply_profile(baked: dict, profile: str) -> dict:
    """Deep copy of a baked cartridge with the profile applied to every display string."""
    out = copy.deepcopy(baked)
    for k in ("title", "subtitle"):
        if k in out:
            out[k] = render(out[k], profile)
    for t in out.get("tiers", []):
        for k in ("name", "description"):
            if k in t:
                t[k] = render(t[k], profile)
    for m in (out.get("misconceptions") or {}).values():
        for k in ("student", "teacher"):
            if k in m:
                m[k] = render(m[k], profile)
    for it in out.get("items", []):
        it["prompt"] = render(it["prompt"], profile)
        it["choices"] = [render(c, profile) for c in it["choices"]]
        it["explanation"] = render(it["explanation"], profile)
    out["render_profile"] = profile
    return out
