"""Test-side lint for the generated Verse slot. Not a compiler: it checks the small, fixed surface
the emitter is allowed to produce (PROTOCOL §7) so a broken file is caught before UEFN sees it."""
import re

# Escapes confirmed in the Book of Verse (see fnm/emit.py for sources).
VALID_ESCAPES = set('tnr"\'\\{}<>&#~')
ITEM_FIELDS = ("Id", "Tier", "Prompt", "Choices", "Answer", "Feedback", "Explanation")
TIER_FIELDS = ("Tier", "Name", "Description")
CART_FIELDS = ("Protocol", "Id", "Version", "Title", "Subtitle", "Grade", "Tiers", "Items")
PAIRS = {")": "(", "]": "[", "}": "{"}


def lint(src: str) -> list:
    errors = []
    if "\t" in src:
        errors.append("tab character present")
    stack = []
    i, line = 0, 1
    in_comment = False
    prev_sig = ""  # last significant char outside strings/comments
    while i < len(src):
        c = src[i]
        if c == "\n":
            line += 1
            in_comment = False
            i += 1
            continue
        if in_comment:
            i += 1
            continue
        if c == "#":
            in_comment = True
            i += 1
            continue
        if c == "<" and src[i + 1:i + 2] == "#":
            errors.append(f"line {line}: block comment opener '<#' outside a string")
        if c == '"':
            j = i + 1
            while True:
                if j >= len(src) or src[j] == "\n":
                    errors.append(f"line {line}: unterminated string literal")
                    break
                d = src[j]
                if d == "\\":
                    nxt = src[j + 1:j + 2]
                    if nxt not in VALID_ESCAPES:
                        errors.append(f"line {line}: invalid escape \\{nxt}")
                    j += 2
                    continue
                if d in "{}":
                    errors.append(f"line {line}: raw {d!r} inside string literal")
                if d == "\t":
                    errors.append(f"line {line}: raw tab inside string literal")
                if d == '"':
                    break
                j += 1
            i = j + 1
            prev_sig = '"'
            continue
        if c in "([{":
            stack.append((c, line))
        elif c in ")]}":
            if prev_sig == ",":
                errors.append(f"line {line}: trailing comma before {c!r}")
            if not stack or stack[-1][0] != PAIRS[c]:
                errors.append(f"line {line}: unbalanced {c!r}")
            else:
                stack.pop()
        if not c.isspace():
            prev_sig = c
        i += 1
    for c, ln in stack:
        errors.append(f"line {ln}: unclosed {c!r}")

    # Structure (PROTOCOL 7): one FnmCartridge_<id>() per cartridge, every field in each, and exactly one
    # FnmCartridges() registry listing exactly those functions.
    funcs = re.findall(r"^(FnmCartridge_\w+)\(\):fnm_cartridge = fnm_cartridge\{$", src, re.M)
    if not funcs:
        errors.append("no 'FnmCartridge_<id>():fnm_cartridge = fnm_cartridge{' line")
    if len(set(funcs)) != len(funcs):
        errors.append("duplicated cartridge function")
    regs = re.findall(r"^FnmCartridges\(\):\[\]fnm_cartridge = array\{(.*)\}$", src, re.M)
    if len(regs) != 1:
        errors.append("missing or duplicated 'FnmCartridges():[]fnm_cartridge = array{...}' line")
    else:
        listed = [n.strip() for n in regs[0].split(",") if n.strip()]
        if sorted(listed) != sorted(f"{f}()" for f in funcs):
            errors.append(f"registry lists {listed}, functions defined are {funcs}")
    for f in CART_FIELDS:
        if len(re.findall(rf"^    {f} := ", src, re.M)) != len(funcs):
            errors.append(f"cartridge field {f} missing in some cartridge")
    for n, ln in enumerate(src.splitlines(), 1):
        s = ln.strip()
        if s.startswith("fnm_item{"):
            for f in ITEM_FIELDS:
                if not re.search(rf"[{{,] ?{f} := ", strip_strings(s)):
                    errors.append(f"line {n}: fnm_item missing field {f}")
        if s.startswith("fnm_tier{"):
            for f in TIER_FIELDS:
                if not re.search(rf"[{{,] ?{f} := ", strip_strings(s)):
                    errors.append(f"line {n}: fnm_tier missing field {f}")
    return errors


def strip_strings(s: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', s)


def string_literals(s: str) -> list:
    """Unescaped contents of every string literal on a line."""
    out = []
    for m in re.finditer(r'"((?:\\.|[^"\\])*)"', s):
        out.append(re.sub(r"\\(.)", lambda e: {"t": "\t", "n": "\n", "r": "\r"}.get(e.group(1), e.group(1)),
                          m.group(1)))
    return out
