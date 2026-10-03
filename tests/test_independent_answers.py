"""Independent re-check of every baked answer (PROTOCOL §5, last paragraph).

Uses Python's own parser (ast) and a tiny safe evaluator — never the generator's evaluator.
Division is rewritten to // but every // is first checked for exact divisibility separately.
"""
import ast

import pytest

from conftest import CID
from fnm.cart import REPO_ROOT
import json

with open(REPO_ROOT / "cartridges" / CID / "baked.json", encoding="utf-8") as _f:
    ITEMS = json.load(_f)["items"]


def to_python(prompt: str) -> str:
    return (prompt.replace("×", "*").replace("÷", "//").replace("−", "-").replace("^", "**"))


def safe_eval(node):
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp):
        a, b = safe_eval(node.left), safe_eval(node.right)
        assert a >= 0 and b >= 0, "negative intermediate"
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.FloorDiv):
            q, r = divmod(a, b)
            assert r == 0, f"inexact division {a} ÷ {b}"
            return q
        if isinstance(node.op, ast.Pow):
            assert b <= 3
            return a ** b
    raise AssertionError(f"unexpected node {ast.dump(node)}")


@pytest.mark.parametrize("item", ITEMS, ids=[it["id"] for it in ITEMS])
def test_answer_independent(item):
    tree = ast.parse(to_python(item["prompt"]), mode="eval")
    value = safe_eval(tree)
    assert value >= 0
    assert item["choices"][item["answer"]] == str(value)
    assert item["explanation"].endswith(f"= {value}.")
