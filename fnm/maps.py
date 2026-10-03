"""Map profiles (PROTOCOL §6a): registry, validation, choice reduction, sync."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from fnm import PROTOCOL_MAJOR
from fnm.cart import ID_RE, REPO_ROOT
from fnm.profiles import PROFILES

SLOT_DIR = "generated"
SLOT_VERSE = "fnm_active_cartridge.verse"
SLOT_TXT = "SLOT.txt"

# TODO(G2): UEFN's Verse folder layout is UNVERIFIED. Assumed: <project>/Plugins/<ProjectName>/Content/
# where ProjectName is the project directory's name. Confirm on the first real UEFN project and fix
# here only. All files land flat in one folder on purpose: a subfolder is a separate Verse module and
# its definitions are <internal> to it (PROTOCOL open item O3).
UEFN_VERSE_SUBPATH = "Plugins/{project}/Content"


def maps_dir(root: Path | None = None) -> Path:
    return Path(root or REPO_ROOT) / "maps"


def list_map_ids(root: Path | None = None) -> list:
    base = maps_dir(root)
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if (p / "map.json").exists())


def load_map(mid: str, root: Path | None = None) -> dict:
    with open(maps_dir(root) / mid / "map.json", encoding="utf-8") as f:
        return json.load(f)


def validate_map(m: dict, dir_name: str | None = None) -> list:
    """List of human-readable failures for one map profile."""
    from fnm.validate import protocol_major
    F = []
    if protocol_major(m.get("protocol")) != PROTOCOL_MAJOR:
        F.append(f"protocol {m.get('protocol')!r} is not fnm-cart/{PROTOCOL_MAJOR}")
    mid = m.get("id")
    if not isinstance(mid, str) or not ID_RE.match(mid):
        F.append(f"id {mid!r} must be lowercase kebab-case")
    if dir_name is not None and mid != dir_name:
        F.append(f"id {mid!r} does not match directory {dir_name!r}")
    mc = m.get("max_choices")
    if not isinstance(mc, int) or isinstance(mc, bool) or not 2 <= mc <= 4:
        F.append(f"max_choices {mc!r} must be an integer 2-4")
    if m.get("render_profile") not in PROFILES:
        F.append(f"render_profile {m.get('render_profile')!r} must be one of {list(PROFILES)}")
    up = m.get("uefn_project")
    if up is not None and (not isinstance(up, str) or not Path(up).is_absolute()):
        F.append(f"uefn_project {up!r} must be null or an absolute path")
    if not isinstance(m.get("title", ""), str):
        F.append("title must be a string")
    return F


def validate_all_maps(root: Path | None = None) -> dict:
    """{map_id: [failures]} for every registered map with at least one failure."""
    out = {}
    for mid in list_map_ids(root):
        try:
            f = validate_map(load_map(mid, root), mid)
        except json.JSONDecodeError as e:
            f = [f"map.json is not valid JSON: {e}"]
        if f:
            out[mid] = f
    return out


def reduce_item(item: dict, max_choices: int) -> dict:
    """§6a: keep the correct choice; drop ARITH (last first), then misconceptions (last first)
    until len(choices) <= max_choices. Keeps baked relative order; re-indexes answer."""
    n = len(item["choices"])
    if n <= max_choices:
        return dict(item)
    mis, ans = item["misconceptions"], item["answer"]
    arith = [i for i in range(n) if i != ans and mis[i] == "ARITH"]
    other = [i for i in range(n) if i != ans and mis[i] != "ARITH"]
    drop_order = arith[::-1] + other[::-1]
    dropped = set(drop_order[: n - max_choices])
    keep = [i for i in range(n) if i not in dropped]
    out = dict(item)
    out["choices"] = [item["choices"][i] for i in keep]
    out["misconceptions"] = [mis[i] for i in keep]
    out["answer"] = keep.index(ans)
    return out


def read_slot(mid: str, root: Path | None = None) -> dict | None:
    p = maps_dir(root) / mid / SLOT_DIR / SLOT_TXT
    if not p.exists():
        return None
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def sync(mid: str, root: Path | None = None) -> list | None:
    """Copy console/verse/*.verse + the map's slot into the UEFN project. None if no project set."""
    root = Path(root or REPO_ROOT)
    m = load_map(mid, root)
    fails = validate_map(m, mid)
    if fails:
        raise ValueError(f"map {mid}: " + "; ".join(fails))
    proj = m.get("uefn_project")
    if proj is None:
        return None
    proj = Path(proj)
    if not proj.is_dir():
        raise FileNotFoundError(f"uefn_project {proj} does not exist")
    slot = maps_dir(root) / mid / SLOT_DIR / SLOT_VERSE
    if not slot.exists():
        raise FileNotFoundError(f"{slot} missing: run insert first")
    dest = proj / UEFN_VERSE_SUBPATH.format(project=proj.name)
    dest.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in sorted((root / "console" / "verse").glob("*.verse")) + [slot]:
        shutil.copyfile(src, dest / src.name)
        copied.append(dest / src.name)
    return copied
