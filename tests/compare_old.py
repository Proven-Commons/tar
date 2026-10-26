#!/usr/bin/env python3
"""Compare the tool with the tool before the containment change.

The run the PR for audit F1 and F5 reports: 3,000 random hostile
archives under five destinations, with `manifest` from the old tool
(commit 7517a86, the base of that change) and from this checkout. The
new tool escapes names in REJECT and SKIP lines, so the script undoes
that escaping first: two backslashes give one, `\\xNN` gives that
character, and `\\u2028` and `\\u2029` give theirs. After that the two
outputs and exit codes must be the same.

The names are drawn from plain parts, `..`, `.`, empty parts, a
backslash and non-ASCII letters, with a leading or trailing `/` at
times. They hold no special character, and no destination ends in `/`
or holds a special character. So the run checks that nothing else
changed. It does not cover the changes the PR means to make; the fixed
cases in `tests/run_tests.py` cover those.

Run from anywhere (needs git, and the old commit in the history):

    python3 tests/compare_old.py [--seed N] [--count N] [--new REV]

With `--new REV`, the new tool is built from commit REV instead of this
checkout. The comparison is about the tool at 1273382, the commit of
the containment change. A later change to the parser changes the
output on purpose, so on a later branch pass `--new 1273382` to rerun
it.

It builds both tools, writes `tests/COMPARE-OLD.md`, and exits non-zero
if any run differs.
"""

import argparse
import io
import os
import platform
import random
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PILOT_DIR = Path(__file__).resolve().parent.parent
RESULTS = PILOT_DIR / "tests" / "COMPARE-OLD.md"
OLD = "7517a86"
DESTS = ["out", "", "/srv/x", "a//b", "./o"]
PARTS = ["a", "b", "..", ".", "", "x.txt", "é", "日本", "a b", "-", "~", "\\", "..a", "a..",
         "...", ":"]
TYPES = [tarfile.REGTYPE, tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE, tarfile.SYMTYPE]


def build(where):
    r = subprocess.run(["lake", "build", "tar-pilot"], cwd=where, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
        sys.exit(f"lake build failed in {where}")
    return Path(where) / ".lake" / "build" / "bin" / "tar-pilot"


def tool_at(rev, td):
    """Build the tool at commit `rev` in a directory of its own. The
    checkout is not changed."""
    src = Path(td) / rev
    src.mkdir()
    r = subprocess.run(["git", "archive", "--format=tar", rev], cwd=PILOT_DIR,
                       capture_output=True)
    if r.returncode != 0:
        sys.exit(f"git archive {rev} failed: {r.stderr.decode()}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        tf.extractall(src, filter="data")
    return build(src)


def name(rng):
    k = rng.randrange(1, 6)
    s = "/".join(rng.choice(PARTS) for _ in range(k))
    if rng.random() < 0.2:
        s = "/" + s
    if rng.random() < 0.1:
        s = s + "/"
    return s


def write_archive(rng, path):
    with tarfile.open(path, "w", format=tarfile.USTAR_FORMAT) as tf:
        for _ in range(rng.randrange(1, 6)):
            n = name(rng)
            if len(n.encode()) > 100:
                continue
            ti = tarfile.TarInfo(n)
            ti.mtime = 0
            ti.type = rng.choice(TYPES)
            data = rng.randbytes(rng.randrange(0, 40)) \
                if ti.type in (tarfile.REGTYPE, tarfile.AREGTYPE) else b""
            ti.size = len(data)
            try:
                tf.addfile(ti, io.BytesIO(data))
            except Exception:
                pass


ESCAPE = re.compile(rb"\\\\|\\x([0-9a-f]{2})|\\u(2028|2029)")


def unescape_char(m):
    if m.group(0) == b"\\\\":
        return b"\\"
    if m.group(1):
        return chr(int(m.group(1), 16)).encode()
    return chr(int(m.group(2), 16)).encode()


def unescape(out):
    """The new tool's output with the names in REJECT and SKIP lines
    as the old tool printed them."""
    lines = []
    for line in out.split(b"\n"):
        if line.startswith(b"REJECT\t") or line.startswith(b"SKIP\t"):
            fields = line.split(b"\t")
            fields[1] = ESCAPE.sub(unescape_char, fields[1])
            line = b"\t".join(fields)
        lines.append(line)
    return b"\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--count", type=int, default=3000, help="random archives")
    ap.add_argument("--new", help="build the new tool from this commit, not the checkout")
    args = ap.parse_args()
    RESULTS.unlink(missing_ok=True)

    rng = random.Random(args.seed)
    runs = 0
    raw = 0
    diffs = []
    lines = {"OK": 0, "REJECT": 0, "SKIP": 0}
    with tempfile.TemporaryDirectory() as td:
        old = tool_at(OLD, td)
        new = tool_at(args.new, td) if args.new else build(PILOT_DIR)
        path = os.path.join(td, "t.tar")
        for _ in range(args.count):
            write_archive(rng, path)
            for dest in DESTS:
                a = subprocess.run([old, "manifest", path, dest], capture_output=True)
                b = subprocess.run([new, "manifest", path, dest], capture_output=True)
                runs += 1
                for line in b.stdout.split(b"\n"):
                    kind = line.split(b"\t")[0].decode()
                    if kind in lines:
                        lines[kind] += 1
                raw += (a.returncode, a.stdout) != (b.returncode, b.stdout)
                if (a.returncode, a.stdout) != (b.returncode, unescape(b.stdout)):
                    diffs.append((dest, a.stdout[:300], b.stdout[:300]))

    lean_ver = subprocess.run(["lean", "--version"], capture_output=True,
                              text=True).stdout.strip()
    out = [
        "# Old and new tool compared",
        "",
        "Written by `tests/compare_old.py`. Rerun it to check these numbers.",
        "",
        f"- Old tool: commit {OLD}. New tool: "
        + (f"commit {args.new}." if args.new else "this checkout."),
        f"- Lean: {lean_ver}. Python: {platform.python_version()}.",
        f"- Seed: {args.seed}",
        f"- Random archives: {args.count}, written by Python's `tarfile` in ustar format",
        "- Destinations: " + ", ".join(f"`{d}`" if d else "the empty string" for d in DESTS),
        f"- `manifest` runs: {runs}",
        f"- Lines the new tool printed: {lines['OK']} OK, {lines['REJECT']} REJECT, "
        f"{lines['SKIP']} SKIP",
        f"- Runs that differ as printed: {raw}. The names hold no special character, so",
        "  the only escape the new tool can print in them is a backslash as two.",
        f"- Runs that differ, after the new escapes are undone: {len(diffs)}",
        "",
        "The names hold no special character, and no destination ends in `/` or holds",
        "a special character. So this run checks that nothing else changed. The",
        "changes the PR means to make are covered by the fixed cases in",
        "`tests/run_tests.py`.",
        "",
    ]
    if diffs:
        out += ["## Differences", ""]
        for dest, a, b in diffs[:20]:
            out += [f"- destination {dest!r}: old {a!r}, new {b!r}"]
        out += [""]
    RESULTS.write_text("\n".join(out))
    print(f"{runs} manifest runs, {len(diffs)} differ; results in {RESULTS}")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
