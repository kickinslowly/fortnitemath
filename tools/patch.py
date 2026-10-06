"""Exact-string, multi-line file edits that keep the file's line endings (Verse files are eol=lf; a Windows
write_text turns them CRLF and git then lists them modified with no content change).

Each needle must match exactly once, or nothing is written. Import it from a throwaway script:

    import sys; sys.path.insert(0, "tools"); from patch import patch
    patch("console/verse/fnm_director.verse", [("old text\\n", "new text\\n")])

or flip a Verse default from the command line (the shape tools/playtest-style hooks use):

    python tools/patch.py console/verse/fnm_director.verse "    DebugAutoPick : int = -1" "    DebugAutoPick : int = 0"
"""
import sys


def patch(path, pairs):
    raw = open(path, "rb").read()
    crlf = b"\r\n" in raw
    text = raw.decode("utf-8").replace("\r\n", "\n")
    for old, new in pairs:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: needle matched {n} times, nothing written:\n{old[:200]}")
        text = text.replace(old, new)
    if crlf:
        text = text.replace("\n", "\r\n")
    open(path, "wb").write(text.encode("utf-8"))
    print(f"patched {path}: {len(pairs)} edit(s)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    patch(sys.argv[1], [(sys.argv[2], sys.argv[3])])
