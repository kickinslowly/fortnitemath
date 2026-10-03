"""PROTOCOL §5 validation. Returns a list of Failure; empty means valid."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from fnm import PROTOCOL_MAJOR
from fnm.cart import ID_RE, ITEM_FIELDS, bake_bytes, cart_dir

ALLOWED_EXTRA = set("×÷−≤≥≠√π")  # × ÷ − ≤ ≥ ≠ √ π
LIMITS = {"prompt": 60, "choice": 14, "explanation": 160, "student": 80,
          "tier name": 24, "title": 32, "subtitle": 40}


@dataclass
class Failure:
    rule: int
    where: str  # item id, or a manifest location
    msg: str

    def __str__(self):
        return f"rule {self.rule} [{self.where}]: {self.msg}"


def protocol_major(protocol) -> int | None:
    if not isinstance(protocol, str) or not protocol.startswith("fnm-cart/"):
        return None
    head = protocol.split("/", 1)[1].split(".", 1)[0]
    return int(head) if head.isdigit() else None


def bad_chars(s: str) -> list:
    return sorted({c for c in s if not (" " <= c <= "~" or c in ALLOWED_EXTRA)})


def display_strings(baked: dict):
    """(where, kind, text) for every display string in a baked cartridge."""
    yield "manifest", "title", baked.get("title", "")
    yield "manifest", "subtitle", baked.get("subtitle", "")
    for t in baked.get("tiers", []):
        w = f"tier {t.get('tier')}"
        yield w, "tier name", t.get("name", "")
        yield w, "tier description", t.get("description", "")
    for key, m in (baked.get("misconceptions") or {}).items():
        yield f"misconception {key}", "student", m.get("student", "")
        yield f"misconception {key}", "teacher", m.get("teacher", "")
    for it in baked.get("items", []):
        w = it.get("id", "?")
        yield w, "prompt", it.get("prompt", "")
        for c in it.get("choices", []):
            yield w, "choice", c
        yield w, "explanation", it.get("explanation", "")


def validate_baked(baked: dict, dir_name: str | None = None) -> list:
    F: list = []

    def fail(rule, where, msg):
        F.append(Failure(rule, where, msg))

    # Rule 1 — protocol major
    if protocol_major(baked.get("protocol")) != PROTOCOL_MAJOR:
        fail(1, "manifest", f"protocol {baked.get('protocol')!r} is not fnm-cart/{PROTOCOL_MAJOR}")

    cid = baked.get("id", "")
    if not isinstance(cid, str) or not ID_RE.match(cid) or len(cid) > 40:
        fail(4, "manifest", f"id {cid!r} must be lowercase kebab-case, <= 40 chars")
    if dir_name is not None and cid != dir_name:
        fail(4, "manifest", f"id {cid!r} does not match directory {dir_name!r}")

    # Rule 2 — tiers
    tiers = baked.get("tiers") or []
    nums = [t.get("tier") for t in tiers]
    T = len(nums)
    if not 1 <= T <= 5 or nums != list(range(1, T + 1)):
        fail(2, "manifest", f"tiers must be numbered 1..T contiguously with T in 1..5, got {nums}")
    tier_set = set(nums)
    items = baked.get("items") or []
    for it in items:
        if it.get("tier") not in tier_set:
            fail(2, it.get("id", "?"), f"tier {it.get('tier')!r} does not exist")

    # Rule 3 — counts
    ipt = baked.get("items_per_tier")
    if not isinstance(ipt, int) or ipt < 24:
        fail(3, "manifest", f"items_per_tier {ipt!r} must be >= 24")
        ipt = 24
    per_tier = Counter(it.get("tier") for it in items)
    for n in nums:
        if per_tier[n] < ipt:
            fail(3, f"tier {n}", f"has {per_tier[n]} items, needs >= {ipt}")

    # Rule 4 — ids, prompts
    for iid, c in Counter(it.get("id") for it in items).items():
        if c > 1:
            fail(4, str(iid), f"duplicate item id ({c}x)")
    seen = defaultdict(dict)
    for it in items:
        p, t = it.get("prompt"), it.get("tier")
        if p in seen[t]:
            fail(4, it.get("id", "?"), f"prompt {p!r} duplicates {seen[t][p]} in tier {t}")
        else:
            seen[t][p] = it.get("id")

    # Rule 5 — choices / answer / misconceptions
    declared = set((baked.get("misconceptions") or {}).keys())
    if "ARITH" in declared:
        fail(5, "manifest", "ARITH is reserved and must not be declared")
    for it in items:
        w = it.get("id", "?")
        missing = [k for k in ITEM_FIELDS if k not in it]
        if missing:
            fail(5, w, f"missing fields {missing}")
            continue
        ch, ans, mis = it["choices"], it["answer"], it["misconceptions"]
        if not isinstance(ch, list) or not 2 <= len(ch) <= 4 or not all(isinstance(c, str) for c in ch):
            fail(5, w, "choices must be a list of 2-4 strings")
            continue
        stripped = [c.strip() for c in ch]
        if len(set(stripped)) != len(stripped):
            fail(5, w, f"duplicate choices {ch}")
        if not isinstance(ans, int) or isinstance(ans, bool) or not 0 <= ans < len(ch):
            fail(5, w, f"answer {ans!r} out of range")
            continue
        if not isinstance(mis, list) or len(mis) != len(ch):
            fail(5, w, "misconceptions must be the same length as choices")
            continue
        for i, m in enumerate(mis):
            if i == ans and m is not None:
                fail(5, w, f"misconceptions[{i}] must be null at the answer")
            if i != ans:
                if m is None:
                    fail(5, w, f"misconceptions[{i}] is null but {i} is not the answer")
                elif m != "ARITH" and m not in declared:
                    fail(5, w, f"misconception {m!r} is not declared")

    # Rule 6 — lengths
    def lim(kind, where, s, key):
        if isinstance(s, str) and len(s) > LIMITS[key]:
            fail(6, where, f"{kind} is {len(s)} chars (max {LIMITS[key]}): {s!r}")

    lim("title", "manifest", baked.get("title"), "title")
    lim("subtitle", "manifest", baked.get("subtitle"), "subtitle")
    for t in tiers:
        lim("tier name", f"tier {t.get('tier')}", t.get("name"), "tier name")
    for key, m in (baked.get("misconceptions") or {}).items():
        lim("student text", f"misconception {key}", m.get("student"), "student")
    for it in items:
        w = it.get("id", "?")
        lim("prompt", w, it.get("prompt"), "prompt")
        lim("explanation", w, it.get("explanation"), "explanation")
        for c in it.get("choices") or []:
            lim("choice", w, c, "choice")

    # Rule 7 — charset
    for where, kind, s in display_strings(baked):
        if not isinstance(s, str):
            fail(7, where, f"{kind} is not a string")
            continue
        bad = bad_chars(s)
        if bad:
            fail(7, where, f"{kind} has disallowed characters {bad}: {s!r}")

    # Rule 8 — answer balance
    groups = defaultdict(list)
    for it in items:
        if isinstance(it.get("choices"), list) and isinstance(it.get("answer"), int):
            groups[(it.get("tier"), len(it["choices"]))].append(it["answer"])
    for (t, n), answers in sorted(groups.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        m, cnt = len(answers), Counter(answers)
        lo, hi = 0.5 / n * m, 1.5 / n * m
        for pos in range(n):
            if not lo <= cnt[pos] <= hi:
                fail(8, f"tier {t}", f"{n}-choice items: answer at position {pos} in {cnt[pos]}/{m} "
                                     f"(allowed {lo:g}..{hi:g})")
    return F


def validate(cid: str, root: Path | None = None, check_determinism: bool = True) -> list:
    path = cart_dir(cid, root) / "baked.json"
    if not path.exists():
        return [Failure(0, cid, f"{path} does not exist (run bake)")]
    raw = path.read_bytes()
    baked = json.loads(raw.decode("utf-8"))
    F = validate_baked(baked, dir_name=cid)
    # Rule 9 — determinism, and baked.json is what the source produces today
    if check_determinism:
        a, b = bake_bytes(cid, root), bake_bytes(cid, root)
        if a != b:
            F.append(Failure(9, cid, "two bakes with the manifest seed differ"))
        elif a != raw:
            F.append(Failure(9, cid, "baked.json is stale: a fresh bake differs (re-run bake)"))
    return F
