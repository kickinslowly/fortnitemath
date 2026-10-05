"""Command line: python -m fnm <validate|bake|emit|insert|new|list> ..."""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from fnm import TOOLCHAIN
from fnm import cart, emit, maps, scaffold
from fnm.profiles import PROFILES
from fnm.validate import validate


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p)


def cmd_validate(cid, root, quiet=False) -> int:
    fails = validate(cid, root)
    for f in fails:
        print(f"FAIL {f}")
    bad_maps = maps.validate_all_maps(root)
    for mid, mf in bad_maps.items():
        for f in mf:
            print(f"FAIL map {mid}: {f}")
    if fails or bad_maps:
        print(f"{cid}: {len(fails)} cartridge failure(s), {len(bad_maps)} invalid map(s)")
        return 1
    if not quiet:
        print(f"{cid}: valid (rules 1-9); {len(maps.list_map_ids(root))} map profile(s) valid")
    return 0


def cmd_bake(cid, root) -> int:
    out = cart.bake(cid, root)
    n = len(cart.load_baked(cid, root)["items"])
    print(f"baked {n} items -> {_rel(out, root)}")
    return 0


def cmd_emit(cid, root, profile) -> int:
    written = emit.emit_maps(cid, root, profile)
    if not written:
        print("warning: no maps registered (maps/*/map.json); no Verse slot written")
    count = len(emit.baked_cartridges(root))
    for mid, path, prof in written:
        print(f"emitted {_rel(path, root)} (map {mid}, profile {prof}, {count} cartridge(s))")
    j = emit.emit_js(root)
    print(f"emitted {_rel(j, root)} (all baked cartridges, profile unicode)")
    return 0


def cmd_sync(mid, root) -> int:
    copied = maps.sync(mid, root)
    if copied is None:
        print(f"map {mid}: uefn_project is null in maps/{mid}/map.json; nothing to sync. "
              f"Set it to the UEFN project root once the project exists.")
        return 0
    for p in copied:
        print(f"copied -> {p}")
    return 0


def cmd_insert(cid, root, profile) -> int:
    cmd_bake(cid, root)
    if cmd_validate(cid, root):
        print("insert stopped before emit: fix validation failures first")
        return 1
    return cmd_emit(cid, root, profile)


def cmd_new(cid, root) -> int:
    d = scaffold.new(cid, root)
    print(f"created {_rel(d, root)}/cartridge.json and generator.py")
    return 0


def cmd_list(root) -> int:
    ids = cart.list_ids(root)
    print("cartridges:")
    if not ids:
        print("  (none)")
    for cid in ids:
        m = cart.load_manifest(cid, root)
        baked_path = cart.cart_dir(cid, root) / "baked.json"
        if baked_path.exists():
            counts = Counter(it["tier"] for it in cart.load_baked(cid, root)["items"])
            per = " ".join(f"t{t}:{counts[t]}" for t in sorted(counts))
            baked = f"baked y  items {sum(counts.values())} ({per})"
        else:
            baked = "baked n"
        print(f"  {cid}  \"{m.get('title')}\"  tiers {len(m.get('tiers', []))}  {baked}")
    print("maps:")
    mids = maps.list_map_ids(root)
    if not mids:
        print("  (none)")
    for mid in mids:
        m = maps.load_map(mid, root)
        slot = maps.read_slot(mid, root)
        held = ("slot: " + ", ".join(f"{c['id']} {c['version']}" for c in slot["cartridges"])
                + f" ({slot.get('profile')})" if slot and slot["cartridges"] else "slot: empty")
        print(f"  {mid}  \"{m.get('title')}\"  max_choices {m.get('max_choices')}  "
              f"profile {m.get('render_profile')}  {held}")
    return 0


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser(prog="fnm", description=f"FNM cartridge toolchain ({TOOLCHAIN})")
    ap.add_argument("--root", type=Path, default=cart.REPO_ROOT, help="repo root (default: this repo)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "bake", "insert", "new", "emit", "sync"):
        p = sub.add_parser(name)
        if name == "emit":
            p.add_argument("id", nargs="?", default=None,
                           help="optional cartridge id (must be baked); the slot always holds every baked cartridge")
        else:
            p.add_argument("id", help="map id" if name == "sync" else "cartridge id")
        if name in ("insert", "emit"):
            p.add_argument("--profile", choices=PROFILES, default=None,
                           help="override every map's render_profile for the Verse slot")
    sub.add_parser("list")
    a = ap.parse_args(argv)
    root = a.root.resolve()
    try:
        if a.cmd == "validate":
            return cmd_validate(a.id, root)
        if a.cmd == "bake":
            return cmd_bake(a.id, root)
        if a.cmd == "emit":
            return cmd_emit(a.id, root, a.profile)
        if a.cmd == "insert":
            return cmd_insert(a.id, root, a.profile)
        if a.cmd == "new":
            return cmd_new(a.id, root)
        if a.cmd == "sync":
            return cmd_sync(a.id, root)
        return cmd_list(root)
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
