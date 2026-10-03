"""`fnm new <id>` — scaffold a cartridge directory."""
from __future__ import annotations

import json
from pathlib import Path

from fnm import PROTOCOL
from fnm.cart import ID_RE, cart_dir


def manifest_template(cid: str) -> dict:
    return {
        "protocol": PROTOCOL,
        "id": cid,
        "version": "0.1.0",
        "title": "New Topic",
        "subtitle": "Describe the skill",
        "grade": "6",
        "standards": [],
        "seed": 1,
        "items_per_tier": 24,
        "tiers": [
            {"tier": 1, "name": "Warm-up", "description": "Replace with what tier 1 practices."}
        ],
        "misconceptions": {
            "OFF_BY_ONE": {
                "student": "Count again carefully.",
                "teacher": "Placeholder misconception; replace with a real wrong rule.",
            }
        },
    }


GENERATOR_TEMPLATE = '''"""Generator for the {cid} cartridge (PROTOCOL.md section 3).

Contract: generate(manifest, rng) -> list of items in the section 4 shape WITHOUT "id"
(the toolchain assigns "<id>/t<tier>/<NNN>"). Stdlib only. Use ONLY the rng you are given,
never module-level random, so bakes are byte-identical (section 5 rule 9).

Each item:
    tier            int, a tier from the manifest
    prompt          <= 60 chars, printable ASCII plus x-sign, divide-sign, minus-sign etc. (section 5 rule 7)
    choices         2-4 strings, unique, each <= 14 chars
    answer          index of the correct choice
    misconceptions  per choice: None at answer, else a manifest misconception key or "ARITH"
    explanation     <= 160 chars, shown when the player is right

Checklist before baking:
  * Every wrong choice should come from a named wrong rule where one exists; ARITH is the fallback.
  * Control answer positions per tier (section 5 rule 8) -- assign them, do not hope.
  * Ship tests/test_<topic>.py that re-checks every baked answer by an INDEPENDENT method.
"""
import random


def generate(manifest: dict, rng: random.Random) -> list:
    items = []
    n = manifest["items_per_tier"]
    for t in manifest["tiers"]:
        tier = t["tier"]
        positions = [i % 4 for i in range(n)]  # exact answer-position balance
        rng.shuffle(positions)
        seen = set()
        while len(items) < n * tier:
            # TODO: replace this placeholder (a + b) with the real topic.
            a, b = rng.randint(2, 20), rng.randint(2, 20)
            prompt = f"{{a}} + {{b}}"
            if prompt in seen:
                continue
            seen.add(prompt)
            correct = a + b
            wrong = [("OFF_BY_ONE", correct + 1), ("ARITH", correct + 2), ("ARITH", correct + 10)]
            rng.shuffle(wrong)
            pos = positions[len(seen) - 1]
            pairs = wrong[:pos] + [(None, correct)] + wrong[pos:]
            items.append({{
                "tier": tier,
                "prompt": prompt,
                "choices": [str(v) for _, v in pairs],
                "answer": pos,
                "misconceptions": [m for m, _ in pairs],
                "explanation": f"{{a}} + {{b}} = {{correct}}.",
            }})
    return items
'''


def new(cid: str, root: Path | None = None) -> Path:
    if not ID_RE.match(cid) or len(cid) > 40:
        raise ValueError(f"id {cid!r} must be lowercase kebab-case, <= 40 chars")
    d = cart_dir(cid, root)
    if d.exists():
        raise FileExistsError(f"{d} already exists")
    d.mkdir(parents=True)
    (d / "cartridge.json").write_bytes(
        (json.dumps(manifest_template(cid), ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    (d / "generator.py").write_bytes(GENERATOR_TEMPLATE.format(cid=cid).encode("utf-8"))
    return d
