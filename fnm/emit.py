"""Emitters (PROTOCOL §7): Verse cartridge slot and emulator carts.js."""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from fnm import PROTOCOL_MAJOR, TOOLCHAIN
from fnm.cart import REPO_ROOT, cart_dir, list_ids, load_baked
from fnm.maps import (SLOT_DIR, SLOT_TXT, SLOT_VERSE, list_map_ids, load_map, maps_dir,
                      reduce_item, validate_all_maps, write_profile)
from fnm.profiles import apply_profile
from fnm.validate import protocol_major

ARITH_TEXT = "Check your arithmetic."
CARTS_JS = Path("emulator") / "carts.js"

# Verse string-literal escapes. Source: The Book of Verse (Epic Games, linked from
# dev.epicgames.com "Verse Language Book of Verse Reference"), docs/01_expressions.md
# "Character literals" table and docs/02_primitives.md "Character escape sequences" table, and
# its conformance test Tests/Literals/String.versetest which asserts each escape equals the raw
# code point. Mandatory: { } (interpolation delimiters; raw braces are a syntax error), " and \.
# Also escaped (confirmed valid escapes, raw would be legal too): ' < > & # ~, and \t \n \r.
# Any other control / format character has no confirmed escape and is rejected. Non-ASCII
# printable characters are written raw in UTF-8 (the conformance tests contain raw UTF-8
# literals such as "Sarah (שרה)").
VERSE_ESCAPES = {
    "\\": "\\\\", '"': '\\"', "{": "\\{", "}": "\\}",
    "'": "\\'", "<": "\\<", ">": "\\>", "&": "\\&", "#": "\\#", "~": "\\~",
    "\t": "\\t", "\n": "\\n", "\r": "\\r",
}


def verse_escape(s: str) -> str:
    out = []
    for c in s:
        if c in VERSE_ESCAPES:
            out.append(VERSE_ESCAPES[c])
        elif unicodedata.category(c) in ("Cc", "Cf", "Cs", "Co", "Cn", "Zl", "Zp"):
            raise ValueError(f"character U+{ord(c):04X} has no confirmed Verse escape: {s!r}")
        else:
            out.append(c)
    return "".join(out)


def vstr(s: str) -> str:
    return '"' + verse_escape(s) + '"'


def varr(values) -> str:
    return "array{" + ", ".join(values) + "}"


def _check_major(baked: dict):
    if protocol_major(baked.get("protocol")) != PROTOCOL_MAJOR:
        raise ValueError(f"{baked.get('id')}: protocol {baked.get('protocol')!r} does not match "
                         f"toolchain major fnm-cart/{PROTOCOL_MAJOR}; refusing to emit")


def feedback(item: dict, catalog: dict) -> list:
    out = []
    for i, m in enumerate(item["misconceptions"]):
        if i == item["answer"]:
            out.append("")
        elif m == "ARITH":
            out.append(ARITH_TEXT)
        else:
            out.append(catalog[m]["student"])
    return out


def verse_function_name(cid: str) -> str:
    """PROTOCOL 7: `FnmCartridge_` + the id with `-` -> `_`."""
    return "FnmCartridge_" + cid.replace("-", "_")


def picker_order(bakeds: list) -> list:
    """PROTOCOL 6b order: grade ascending (numeric when every non-empty grade is a whole number, else as
    strings; cartridges with no grade last), then title, then id. Mirrors emulator/app.js groupByGrade."""
    grades = [str(b.get("grade") or "").strip() for b in bakeds]
    numeric = all(re.fullmatch(r"\d+", g) for g in grades if g)

    def key(b):
        g = str(b.get("grade") or "").strip()
        return (1 if g == "" else 0, int(g) if (g and numeric) else 0, "" if numeric else g,
                str(b.get("title", "")), b["id"])

    return sorted(bakeds, key=key)


def cartridge_literal(baked: dict, profile: str, max_choices: int) -> list:
    """Lines of one `FnmCartridge_<id>():fnm_cartridge = fnm_cartridge{ ... }` definition (PROTOCOL 7, 8)."""
    _check_major(baked)
    b = apply_profile(baked, profile)
    b["items"] = [reduce_item(it, max_choices) for it in b["items"]]
    cat = b.get("misconceptions") or {}
    lines = [
        f"{verse_function_name(b['id'])}():fnm_cartridge = fnm_cartridge{{",
        f"    Protocol := {vstr(b['protocol'])},",
        f"    Id := {vstr(b['id'])},",
        f"    Version := {vstr(b['version'])},",
        f"    Title := {vstr(b['title'])},",
        f"    Subtitle := {vstr(b['subtitle'])},",
        f"    Grade := {vstr(str(b.get('grade') or ''))},",
        "    Tiers := array{",
    ]
    tiers = b["tiers"]
    for i, t in enumerate(tiers):
        sep = "," if i < len(tiers) - 1 else ""
        lines.append(f"        fnm_tier{{Tier := {int(t['tier'])}, Name := {vstr(t['name'])}, "
                     f"Description := {vstr(t['description'])}}}{sep}")
    lines.append("    },")
    lines.append("    Items := array{")
    items = b["items"]
    for i, it in enumerate(items):
        sep = "," if i < len(items) - 1 else ""
        lines.append(
            f"        fnm_item{{Id := {vstr(it['id'])}, Tier := {int(it['tier'])}, "
            f"Prompt := {vstr(it['prompt'])}, "
            f"Choices := {varr(vstr(c) for c in it['choices'])}, "
            f"Answer := {int(it['answer'])}, "
            f"Feedback := {varr(vstr(f) for f in feedback(it, cat))}, "
            f"Explanation := {vstr(it['explanation'])}}}{sep}")
    lines.append("    }")
    lines.append("}")
    return lines


def verse_source(bakeds, profile: str = "unicode", max_choices: int = 4,
                 map_id: str | None = None) -> str:
    """The slot file (PROTOCOL 7): one function per baked cartridge plus the FnmCartridges() registry in
    picker order. `bakeds` is a list of baked dicts (a single dict is accepted)."""
    if isinstance(bakeds, dict):
        bakeds = [bakeds]
    if not bakeds:
        raise ValueError("no baked cartridges to emit")
    ordered = picker_order(bakeds)
    for b in ordered:
        _check_major(b)
    names = [verse_function_name(b["id"]) for b in ordered]
    if len(set(names)) != len(names):
        raise ValueError(f"cartridge ids collide as Verse names: {names}")
    total = sum(len(b["items"]) for b in ordered)
    lines = [
        "# GENERATED by fnm \u2014 do not edit",
        "# cartridges: " + ", ".join(f"{b['id']} {b['version']}" for b in ordered) + f"  profile: {profile}",
        f"# map: {map_id or '-'}  max_choices: {max_choices}  protocol: {ordered[0]['protocol']}  "
        f"toolchain: {TOOLCHAIN}  items: {total}",
        "# Regenerate with: python -m fnm insert <id>   (see PROTOCOL.md section 7)",
    ]
    for b in ordered:
        lines.append("")
        lines.extend(cartridge_literal(b, profile, max_choices))
    lines.append("")
    lines.append("# Every inserted cartridge in picker order: grade ascending, then title (PROTOCOL section 6b).")
    lines.append("FnmCartridges():[]fnm_cartridge = " + varr(f"{n}()" for n in names))
    return "\n".join(lines) + "\n"


def baked_cartridges(root: Path | None = None) -> list:
    """Every cartridge that has a baked.json, as baked dicts (directory order)."""
    return [load_baked(cid, root) for cid in list_ids(root)
            if (cart_dir(cid, root) / "baked.json").exists()]


def emit_maps(cid: str | None = None, root: Path | None = None, profile_override: str | None = None) -> list:
    """Write every registered map's slot (PROTOCOL 6a) holding EVERY baked cartridge (PROTOCOL 7). `cid`, if
    given, must be one of them. Every baked cartridge must pass rules 1-8 or nothing is written.
    Returns [(map_id, verse_path, profile)]."""
    from fnm.validate import validate
    bad = validate_all_maps(root)
    if bad:
        raise ValueError("invalid map profile(s): " + "; ".join(
            f"{mid}: {', '.join(f)}" for mid, f in bad.items()))
    bakeds = baked_cartridges(root)
    if not bakeds:
        raise ValueError("no baked cartridges (run bake first)")
    if cid is not None and cid not in {b["id"] for b in bakeds}:
        raise ValueError(f"{cid} has no baked.json (run bake first)")
    invalid = {b["id"]: validate(b["id"], root, check_determinism=False) for b in bakeds}
    invalid = {k: v for k, v in invalid.items() if v}
    if invalid:
        raise ValueError("invalid baked cartridge(s), nothing emitted: " + "; ".join(
            f"{k}: {len(v)} failure(s), first: {v[0]}" for k, v in invalid.items()))
    ordered = picker_order(bakeds)
    out = []
    for mid in list_map_ids(root):
        m = load_map(mid, root)
        profile = profile_override or m["render_profile"]
        src = verse_source(ordered, profile, m["max_choices"], mid)
        d = maps_dir(root) / mid / SLOT_DIR
        d.mkdir(parents=True, exist_ok=True)
        (d / SLOT_VERSE).write_bytes(src.encode("utf-8"))
        slot = "# GENERATED by fnm - the cartridges this map holds, in picker order (PROTOCOL 6a, 6b)\n"
        slot += "".join(f"cartridge={b['id']} {b['version']}\n" for b in ordered)
        slot += f"profile={profile}\n"
        (d / SLOT_TXT).write_bytes(slot.encode("utf-8"))
        write_profile(mid, root)
        out.append((mid, d / SLOT_VERSE, profile))
    return out


def carts_js_source(root: Path | None = None) -> str:
    lines = [
        "// GENERATED by fnm \u2014 do not edit. Rebuilt from every cartridges/*/baked.json on insert.",
        f"// toolchain: {TOOLCHAIN}  profile: unicode",
        "window.FNM_CARTRIDGES = window.FNM_CARTRIDGES || {};",
    ]
    for cid in list_ids(root):
        if not (cart_dir(cid, root) / "baked.json").exists():
            continue
        baked = load_baked(cid, root)
        _check_major(baked)
        data = json.dumps(apply_profile(baked, "unicode"), ensure_ascii=False, indent=2)
        data = data.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        lines.append(f"window.FNM_CARTRIDGES[{json.dumps(cid)}] = {data};")
    return "\n".join(lines) + "\n"


def emit_js(root: Path | None = None) -> Path:
    out = Path(root or REPO_ROOT) / CARTS_JS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(carts_js_source(root).encode("utf-8"))
    return out
