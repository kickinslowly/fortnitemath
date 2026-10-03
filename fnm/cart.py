"""Cartridge loading and baking (PROTOCOL §3, §4, §5 rule 9)."""
from __future__ import annotations

import importlib.util
import json
import random
import re
import sys
from pathlib import Path

from fnm import TOOLCHAIN

REPO_ROOT = Path(__file__).resolve().parent.parent
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ITEM_FIELDS = ("id", "tier", "prompt", "choices", "answer", "misconceptions", "explanation")


def cart_dir(cid: str, root: Path | None = None) -> Path:
    return Path(root or REPO_ROOT) / "cartridges" / cid


def load_manifest(cid: str, root: Path | None = None) -> dict:
    with open(cart_dir(cid, root) / "cartridge.json", encoding="utf-8") as f:
        return json.load(f)


def load_baked(cid: str, root: Path | None = None) -> dict:
    with open(cart_dir(cid, root) / "baked.json", encoding="utf-8") as f:
        return json.load(f)


def load_generator(cid: str, root: Path | None = None):
    path = cart_dir(cid, root) / "generator.py"
    name = "fnm_cart_gen_" + re.sub(r"\W", "_", cid)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses etc. look the module up by name
    old, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no __pycache__ in cartridges/
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = old
    return mod


def source_items(manifest: dict, cid: str, root: Path | None = None) -> list:
    d = cart_dir(cid, root)
    gen, src = d / "generator.py", d / "items.src.json"
    if gen.exists() and src.exists():
        raise ValueError(f"{cid}: has both generator.py and items.src.json (exactly one allowed)")
    if gen.exists():
        return load_generator(cid, root).generate(manifest, random.Random(manifest["seed"]))
    if src.exists():
        with open(src, encoding="utf-8") as f:
            return json.load(f)
    raise ValueError(f"{cid}: needs generator.py or items.src.json")


def assign_ids(cid: str, items: list) -> list:
    counters: dict = {}
    out = []
    for it in items:
        t = it["tier"]
        counters[t] = counters.get(t, 0) + 1
        full = {"id": f"{cid}/t{t}/{counters[t]:03d}"}
        full.update({k: it[k] for k in ITEM_FIELDS if k != "id"})
        extra = [k for k in it if k not in ITEM_FIELDS]
        if extra:
            raise ValueError(f"{full['id']}: unknown item fields {extra}")
        out.append(full)
    return out


def bake_bytes(cid: str, root: Path | None = None) -> bytes:
    manifest = load_manifest(cid, root)
    baked = dict(manifest)  # manifest field order preserved
    baked.pop("baked_with", None)
    baked.pop("items", None)
    baked["baked_with"] = TOOLCHAIN
    baked["items"] = assign_ids(cid, source_items(manifest, cid, root))
    text = json.dumps(baked, ensure_ascii=False, indent=2) + "\n"
    return text.encode("utf-8")


def bake(cid: str, root: Path | None = None) -> Path:
    data = bake_bytes(cid, root)
    out = cart_dir(cid, root) / "baked.json"
    out.write_bytes(data)  # bytes: LF preserved on Windows
    return out


def list_ids(root: Path | None = None) -> list:
    base = Path(root or REPO_ROOT) / "cartridges"
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if (p / "cartridge.json").exists())
