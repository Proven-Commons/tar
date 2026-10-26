#!/usr/bin/env python3
"""Differential tests for the Proven Commons tar pilot.

Compares the Lean implementation against Python's `tarfile` module and
against an independent implementation of the extraction spec written
below. Run from anywhere:

    python3 tests/run_tests.py

It builds the Lean project first, so it never checks stale code, runs
all cases in a temporary directory, writes `tests/TEST-RESULTS.md`, and
exits non-zero if any case fails.

With `--tool REV`, the checks on the tool run against the tool built
from commit REV, in a temporary directory, instead of this checkout's.
The checkout is not changed or built. The axiom check reads this
checkout's proofs, not the tool, so it is left out. The record goes to
`tests/TEST-RESULTS-REV.md`, with REV as a short hash, and
`tests/TEST-RESULTS.md` is left as it is. This shows which of these
checks an earlier tool fails:

    python3 tests/run_tests.py --tool 1273382
"""

import argparse
import io
import os
import random
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PILOT_DIR = Path(__file__).resolve().parent.parent
EXE = PILOT_DIR / ".lake" / "build" / "bin" / "tar-pilot"
RESULTS = PILOT_DIR / "tests" / "TEST-RESULTS.md"
# The theorems `TarPilot/Verify.lean` prints the axioms of.
THEOREMS = ["TarPilot." + t for t in [
    "gate_eq", "gate_plain", "manifest_eq", "manifest_extracted", "manifest_lines",
    "manifest_lines_eq", "extractAll_contained",
    "extractAll_joined", "extractAll_resolves_inside", "extractArchive_eq",
    "extractArchive_resolves_inside"]] + ["Spec.escape_noSpecial"]

checks = 0
failures = []


def check(name, ok, detail=""):
    global checks
    checks += 1
    if not ok:
        failures.append(f"{name}: {detail}")
        print(f"FAIL {name}: {detail}")


def run_lean(*args, cwd=None):
    """Run the tool. Its output is decoded without newline translation,
    so a stray CR shows up as a mismatch."""
    r = subprocess.run([str(EXE), *args], capture_output=True, cwd=cwd)
    return subprocess.CompletedProcess(
        r.args, r.returncode, r.stdout.decode("utf-8", "surrogateescape"),
        r.stderr.decode("utf-8", "surrogateescape"))


def is_special(c):
    """A control character (C0 below space, DEL, or C1), or the line
    separator U+2028 or the paragraph separator U+2029."""
    return ord(c) < 0x20 or 0x7F <= ord(c) < 0xA0 or c in "\u2028\u2029"


def escape_char(c):
    if c == "\\":
        return "\\\\"
    if c in "\u2028\u2029":
        return f"\\u{ord(c):04x}"
    return f"\\x{ord(c):02x}" if is_special(c) else c


def escape_name(name):
    """A name as the tool prints it: a backslash as two, U+2028 and
    U+2029 as `\\u2028` and `\\u2029`, any other special character as
    `\\x` and two hex digits."""
    return "".join(escape_char(c) for c in name)


def spec_gate(name):
    """The extraction spec, implemented independently of the Lean code.

    Returns the cleaned relative components, or None to reject.
    Absolute names are rejected. Any `..`, and any special character,
    is rejected. Empty and `.` components are dropped. An empty result
    is rejected.
    """
    if name.startswith("/") or any(is_special(c) for c in name):
        return None
    out = []
    for comp in name.split("/"):
        if comp == "..":
            return None
        if comp in ("", "."):
            continue
        out.append(comp)
    return out if out else None


def is_regular(ti):
    return ti.isreg()


# Typeflags of regular files: `0`, NUL, and `7` (contiguous file).
REGULAR_CODES = (ord("0"), 0, ord("7"))


def is_regular_entry(name, tcode):
    """A regular file: typeflag `0`, NUL or `7`, and a name that does not
    end in `/`, which older archives use for a directory."""
    return tcode in REGULAR_CODES and not name.endswith("/")


def one_file(fmt, name, data=b"x", typ=tarfile.REGTYPE, pax=None):
    """An archive of one entry, written by Python's tarfile."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=fmt) as t:
        ti = tarfile.TarInfo(name)
        ti.size = len(data)
        ti.type = typ
        ti.mtime = 0
        if pax:
            ti.pax_headers = pax
        t.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def patch_header(raw, offset, new_bytes):
    """Overwrite bytes in the first header and fix its checksum."""
    hdr = bytearray(raw[:512])
    hdr[offset:offset + len(new_bytes)] = new_bytes
    hdr[148:156] = b" " * 8
    hdr[148:156] = ("%06o\0 " % sum(hdr)).encode()
    return bytes(hdr) + raw[512:]


LONG = "d/" + "n" * 120 + ".txt"
SPLIT = "p" * 30 + "/" + "q" * 90 + "/file.txt"


def unsupported_archives(work):
    """Archives that use what the pilot does not read. Each must fail to
    parse: these are the probes of findings F2, F3 and F7 of the bar
    audit, and more of the same kinds."""
    yield "GNU long name entry (typeflag L)", one_file(tarfile.GNU_FORMAT, LONG)
    yield "GNU long link entry (typeflag K)", patch_header(
        one_file(tarfile.GNU_FORMAT, "l.txt"), 156, b"K")
    yield "pax long path (typeflag x)", one_file(tarfile.PAX_FORMAT, LONG)
    yield "pax path override", one_file(tarfile.PAX_FORMAT, "safe.txt",
                                        pax={"path": "other/dir/real.txt"})
    yield "pax path override that climbs out", one_file(
        tarfile.PAX_FORMAT, "safe.txt", pax={"path": "../../etc/cron.d/x"})
    yield "pax non-ASCII name", one_file(tarfile.PAX_FORMAT, "café/notes.txt")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT,
                      pax_headers={"comment": "global"}) as t:
        ti = tarfile.TarInfo("g.txt")
        ti.size = 1
        t.addfile(ti, io.BytesIO(b"g"))
    yield "pax global header (typeflag g)", buf.getvalue()
    split = one_file(tarfile.USTAR_FORMAT, SPLIT)
    yield "split name, invalid UTF-8 in the prefix field only", patch_header(split, 345, b"\xff")
    yield "split name, invalid UTF-8 in the name field only", patch_header(split, 0, b"\xff")
    yield "split name, invalid UTF-8 in both fields", patch_header(
        patch_header(split, 0, b"\xff"), 345, b"\xff")
    yield "short name, invalid UTF-8", patch_header(
        one_file(tarfile.USTAR_FORMAT, "short.txt"), 0, b"\xff")
    gnu = one_file(tarfile.GNU_FORMAT, "a.txt")
    yield "GNU header with access and change times (incremental dump)", patch_header(
        gnu, 345, b"15267276047\x0015267276047\x00")
    yield "GNU header with a sparse map", patch_header(gnu, 386, b"00000000001")
    for code in b"DMNSVAZ":
        yield f"unknown typeflag {chr(code)}", patch_header(
            one_file(tarfile.USTAR_FORMAT, "u.txt"), 156, bytes([code]))
    yield "base-256 size field", patch_header(
        one_file(tarfile.USTAR_FORMAT, "b.txt"), 124, b"\x80" + b"\x00" * 10 + b"\x01")
    yield "ustar magic with a GNU version", patch_header(
        one_file(tarfile.USTAR_FORMAT, "m.txt"), 263, b" \x00")
    yield "no magic (old Unix V7 header)", patch_header(
        one_file(tarfile.USTAR_FORMAT, "v.txt"), 257, b"\x00" * 8)
    for name, typ in [("d/", tarfile.AREGTYPE), ("e/", tarfile.REGTYPE)]:
        yield f"name ending in / with typeflag {typ!r} and data", one_file(
            tarfile.USTAR_FORMAT, name, data=b"x", typ=typ)
    yield "size field of spaces", patch_header(
        one_file(tarfile.USTAR_FORMAT, "f", data=b""), 124, b" " * 12)
    gnu_tar = shutil.which("tar")
    if gnu_tar:
        src = work / "systar-long" / "d"
        src.mkdir(parents=True)
        (src / ("n" * 120 + ".txt")).write_bytes(b"x")
        out = work / "systar-long.tar"
        subprocess.run([gnu_tar, "cf", str(out), "d"], cwd=work / "systar-long", check=True)
        yield "system tar, default format, long name", out.read_bytes()
    if gnu_tar and is_gnu_tar(gnu_tar):
        # GNU tar's own output for the GNU fields in bytes 345 to 499.
        src = work / "systar-gnu-fields"
        src.mkdir()
        (src / "a.txt").write_bytes(b"hi\n")
        with open(src / "sparse", "wb") as f:
            f.seek(1 << 20)
            f.write(b"end")
        out = work / "systar-incremental.tar"
        subprocess.run([gnu_tar, "cf", str(out), "--format=gnu",
                        f"--listed-incremental={work / 'systar.snar'}", "a.txt"],
                       cwd=src, check=True)
        yield "system tar, incremental dump (times in bytes 345 to 368)", out.read_bytes()
        out = work / "systar-sparse.tar"
        subprocess.run([gnu_tar, "cf", str(out), "--format=gnu", "--sparse", "sparse"],
                       cwd=src, check=True)
        yield "system tar, sparse file (typeflag S, map in bytes 386 to 494)", out.read_bytes()


def readable_archives(work):
    """Archives in formats the pilot reads. Each must read as Python's
    tarfile reads it."""
    yield "contiguous file (typeflag 7)", one_file(
        tarfile.USTAR_FORMAT, "contig.bin", data=b"contiguous", typ=tarfile.CONTTYPE)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as t:
        for name, data in [("gnu.txt", b"gnu"), ("dir/inner.bin", bytes(range(40)))]:
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mtime = 0
            t.addfile(ti, io.BytesIO(data))
    yield "GNU format, short names", buf.getvalue()
    yield "pax format, short ASCII name (no pax header)", one_file(
        tarfile.PAX_FORMAT, "plain.txt", data=b"plain")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as t:
        for name, typ, data in [("olddir/", tarfile.AREGTYPE, b""),
                                ("olddir/f.txt", tarfile.AREGTYPE, b"old"),
                                ("slashdir/", tarfile.REGTYPE, b"")]:
            ti = tarfile.TarInfo(name)
            ti.type = typ
            ti.size = len(data)
            ti.mtime = 0
            t.addfile(ti, io.BytesIO(data))
    yield "names ending in / with typeflags NUL and 0, read as directories", buf.getvalue()
    for typ in [tarfile.LNKTYPE, tarfile.SYMTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE,
                tarfile.DIRTYPE, tarfile.FIFOTYPE]:
        yield f"typeflag {typ.decode()} with a size field, then two files", hidden_after(typ)
    gnu_tar = shutil.which("tar")
    if gnu_tar:
        # Every kind of entry GNU tar writes for short names in its own
        # formats: GNU keeps nothing in bytes 345 to 499 for these unless
        # it is asked for an incremental dump, a sparse file or a
        # multi-volume archive.
        src = work / "systar-short"
        (src / "d").mkdir(parents=True)
        (src / "a.txt").write_bytes(b"hi\n")
        (src / "empty").write_bytes(b"")
        (src / "d" / "b.txt").write_bytes(b"x\n")
        os.link(src / "a.txt", src / "hard.txt")
        os.symlink("a.txt", src / "sym")
        os.mkfifo(src / "fifo")
        names = ["a.txt", "empty", "d", "hard.txt", "sym", "fifo"]
        for fmt in ["default"] + (["gnu", "oldgnu"] if is_gnu_tar(gnu_tar) else []):
            out = work / f"systar-short-{fmt}.tar"
            opts = [] if fmt == "default" else [f"--format={fmt}"]
            subprocess.run([gnu_tar, "cf", str(out), *opts, *names], cwd=src, check=True)
            yield (f"system tar, {fmt} format, short names: files, a directory, "
                   "a hard link, a symlink, a FIFO"), out.read_bytes()


def is_gnu_tar(tar):
    r = subprocess.run([tar, "--version"], capture_output=True, text=True)
    return r.stdout.startswith("tar (GNU tar)")


def tar_version():
    tar = shutil.which("tar")
    if not tar:
        return "none"
    r = subprocess.run([tar, "--version"], capture_output=True, text=True)
    return (r.stdout.splitlines() or ["unknown"])[0]


def hidden_after(typ):
    """An entry of type `typ` whose size field says 1024, then a header and
    data that fill those 1024 bytes, then one more file. Types 1 to 6
    store no data, so a reader must see all three entries."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as t:
        for name, kind, data in [("node", typ, b""), ("hidden.txt", tarfile.REGTYPE, b"hidden"),
                                 ("b.txt", tarfile.REGTYPE, b"b")]:
            ti = tarfile.TarInfo(name)
            ti.type = kind
            ti.size = len(data)
            ti.mtime = 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                ti.linkname = "target"
            t.addfile(ti, io.BytesIO(data))
    return patch_header(buf.getvalue(), 124, b"00000002000\0")


def tarfile_view(path):
    """(name, data, typeflag code) for each entry, as tarfile reads it."""
    out = []
    with tarfile.open(path) as tf:
        for m in tf.getmembers():
            data = tf.extractfile(m).read() if m.isreg() else b""
            tcode = m.type[0] if isinstance(m.type, bytes) else ord(m.type)
            out.append((m.name, data, tcode))
    return out


def build_archive_a(path):
    """Archive with normal, hostile, and edge-case entries, built with
    Python's tarfile as the reference implementation."""
    rng = random.Random(42)
    entries = [
        ("hello.txt", b"hello world", tarfile.REGTYPE),
        ("dir/nested.bin", bytes(range(256)) * 3, tarfile.REGTYPE),
        ("empty.txt", b"", tarfile.REGTYPE),
        ("big.bin", rng.randbytes(5000), tarfile.REGTYPE),
        ("dir", b"", tarfile.DIRTYPE),
        ("../evil.txt", b"evil", tarfile.REGTYPE),
        ("a/../../evil2.txt", b"evil2", tarfile.REGTYPE),
        ("/abs.txt", b"abs", tarfile.REGTYPE),
        ("./dot.txt", b"dot", tarfile.REGTYPE),
        ("a//b.txt", b"ab", tarfile.REGTYPE),
        ("a/./c.txt", b"ac", tarfile.REGTYPE),
        ("link.txt", b"hello.txt", tarfile.SYMTYPE),
        ("x\nOK\t/etc/passwd", b"line break in a name", tarfile.REGTYPE),
        ("../y\nOK\t/etc/cron.d/z", b"line break in a rejected name", tarfile.REGTYPE),
        ("tab\there.txt", b"tab", tarfile.REGTYPE),
        ("del\x7f.txt", b"del", tarfile.REGTYPE),
        ("nel\x85.txt", b"next line", tarfile.REGTYPE),
        ("back\\slash.txt", b"backslash", tarfile.REGTYPE),
        ("ls\u2028OK\t/etc/passwd", b"line separator in a name", tarfile.REGTYPE),
        ("ps\u2029.txt", b"paragraph separator", tarfile.SYMTYPE),
        ("link\nOK\t/etc/shadow", b"x", tarfile.SYMTYPE),
        ("p" * 50 + "/" + "x" * 70 + ".txt", b"long name split over prefix", tarfile.REGTYPE),
        ("deep/" + "/".join(f"d{i}" for i in range(8)) + "/leaf.txt", b"leaf", tarfile.REGTYPE),
    ]
    with tarfile.open(path, "w", format=tarfile.USTAR_FORMAT) as tf:
        for name, data, typ in entries:
            ti = tarfile.TarInfo(name)
            ti.type = typ
            ti.mtime = 0
            if typ == tarfile.SYMTYPE:
                ti.linkname = data.decode()
                ti.size = 0
                tf.addfile(ti)
            elif typ == tarfile.DIRTYPE:
                ti.size = 0
                tf.addfile(ti)
            else:
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
    return entries


def under(dest, rel):
    """The printed path of `rel` under `dest`."""
    if dest == "":
        return rel
    return dest + rel if dest.endswith("/") else dest + "/" + rel


def expected_manifest(entries_data, dest="out"):
    """Expected manifest lines from the spec, in archive order.
    entries_data: list of (name, data, typeflag_byte)."""
    lines = []
    for name, data, tcode in entries_data:
        if not is_regular_entry(name, tcode):
            lines.append(f"SKIP\t{escape_name(name)}\t{tcode}")
            continue
        rel = spec_gate(name)
        if rel is None:
            lines.append(f"REJECT\t{escape_name(name)}")
        else:
            lines.append(f"OK\t{under(dest, '/'.join(rel))}\t{len(data)}\t{sum(data)}")
    return lines


def output_lines(stdout):
    """The lines a command printed: split on LF only, as the format is.
    Output that does not end in LF gives a line that matches nothing."""
    if stdout and not stdout.endswith("\n"):
        return stdout.split("\n") + ["(no LF at the end)"]
    return stdout.split("\n")[:-1] if stdout else []


def list_rows(stdout):
    """(name, size, typeflag) for each line `list` printed, or a row
    that matches nothing when a line has not three fields."""
    rows = []
    for line in output_lines(stdout):
        parts = line.split("\t")
        try:
            rows.append((parts[0], int(parts[1]), int(parts[2])) if len(parts) == 3 else (line,))
        except ValueError:
            rows.append((line,))
    return rows


def as_tarfile_reads(row):
    """A `list` row as tarfile reads the entry. tarfile reads typeflag
    NUL with a name ending in `/` as a directory, typeflag 5 ("Old V7
    tar format represents a directory as a regular file with a trailing
    slash", in tarfile.py). Every other row is left as it is."""
    if len(row) == 3 and row[2] == 0 and row[0].endswith("/"):
        return (row[0], row[1], 53)
    return row


def skip_as_tarfile_reads(line):
    """A `manifest` line as tarfile reads the entry: the same rule, for
    SKIP lines."""
    p = line.split("\t")
    if len(p) == 3 and p[0] == "SKIP" and p[2] == "0" and p[1].endswith("/"):
        return "\t".join([p[0], p[1], "53"])
    return line


def commit_of(rev):
    """The short hash of commit `rev`."""
    r = subprocess.run(["git", "rev-parse", "--short=7", "--verify", rev + "^{commit}"],
                       cwd=PILOT_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"not a commit: {rev}")
    return r.stdout.strip()


def tool_at(rev, td):
    """Build the tool at commit `rev` in `td`. The checkout is not
    changed."""
    src = td / "tool-src"
    src.mkdir()
    r = subprocess.run(["git", "archive", "--format=tar", rev], cwd=PILOT_DIR,
                       capture_output=True)
    if r.returncode != 0:
        sys.exit(f"git archive {rev} failed: {r.stderr.decode()}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        tf.extractall(src, filter="data")
    build = subprocess.run(["lake", "build", "tar-pilot"], cwd=src, capture_output=True,
                           text=True)
    if build.returncode != 0:
        print(build.stdout + build.stderr)
        sys.exit(f"lake build failed at {rev}")
    return src / ".lake" / "build" / "bin" / "tar-pilot"


def main():
    global EXE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tool", metavar="REV",
                    help="check the tool built from commit REV instead of this checkout's, "
                         "and leave out the axiom check")
    args = ap.parse_args()
    rev = commit_of(args.tool) if args.tool else None
    results = RESULTS if rev is None else PILOT_DIR / "tests" / f"TEST-RESULTS-{rev}.md"
    # A run that stops early must not leave an earlier passing record.
    results.unlink(missing_ok=True)
    if rev is None:
        build = subprocess.run(["lake", "build"], cwd=PILOT_DIR, capture_output=True,
                               text=True)
        if build.returncode != 0:
            print(build.stdout + build.stderr)
            sys.exit("lake build failed")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        if rev is not None:
            EXE = tool_at(rev, td)
        archive_a = td / "a.tar"
        entries = build_archive_a(archive_a)

        # Reference view of archive A from Python tarfile.
        with tarfile.open(archive_a) as tf:
            members = tf.getmembers()
            ref_entries = []
            for m in members:
                data = tf.extractfile(m).read() if m.isreg() else b""
                tcode = m.type[0] if isinstance(m.type, bytes) else ord(m.type)
                ref_entries.append((m.name, data, tcode))

        # 1. list: Lean agrees with tarfile on name, size, typeflag.
        r = run_lean("list", str(archive_a))
        check("list-exit", r.returncode == 0, r.stderr)
        lean_list = [row for row in list_rows(r.stdout)]
        # tarfile strips the trailing slash from directory names when
        # reading; the raw header keeps it. Normalize both sides.
        norm = lambda nl: [(n[0].rstrip("/"),) + tuple(n[1:]) if len(n) == 3 and n[2] == 53 else n
                           for n in nl]
        lean_list, ref_list = norm(lean_list), norm(
            [(escape_name(n), len(d), t) for (n, d, t) in ref_entries])
        check("list-match", lean_list == ref_list,
              f"lean={lean_list} ref={ref_list}")

        # 2. manifest: Lean agrees with the spec on every entry.
        r = run_lean("manifest", str(archive_a), "out")
        check("manifest-exit", r.returncode == 0, r.stderr)
        norm_skip = lambda ls: [
            "\t".join([p[0], p[1].rstrip("/")] + p[2:]) if l.startswith("SKIP") and len(p) > 1
            else l for l in ls for p in [l.split("\t")]]
        lean_manifest = norm_skip(output_lines(r.stdout))
        exp_manifest = norm_skip(expected_manifest(ref_entries))
        check("manifest-match", lean_manifest == exp_manifest,
              f"lean={lean_manifest} expected={exp_manifest}")

        # 2b. Other destinations: the printed path is the destination as
        # given, then the entry's components, with no doubled `/`.
        for dest in ["out/", "/", "", "/srv/data", "a//b", "../up", "./o"]:
            r = run_lean("manifest", str(archive_a), dest)
            check(f"manifest-dest {dest!r}",
                  r.returncode == 0 and
                  norm_skip(output_lines(r.stdout)) == norm_skip(expected_manifest(ref_entries, dest)),
                  f"rc={r.returncode} lean={output_lines(r.stdout)[:3]}")
        # The last is bytes that are not UTF-8, which the Lean runtime
        # reads as U+FFFD before `main` runs.
        for dest in ["out\nOK", "o\tut", "o\x7f", "o\u2028ut", "o\ufffdut", b"o\xffut"]:
            r = run_lean("manifest", str(archive_a), dest)
            check(f"manifest-dest-refused {dest!r}", r.returncode == 2 and r.stdout == "",
                  f"rc={r.returncode} out={r.stdout[:100]!r}")
        ok_count = sum(1 for l in exp_manifest if l.startswith("OK"))
        rej_count = sum(1 for l in exp_manifest if l.startswith("REJECT"))
        skip_count = sum(1 for l in exp_manifest if l.startswith("SKIP"))

        # 3. create: Lean writes an archive Python can read back exactly.
        src = td / "src"
        (src / "sub").mkdir(parents=True)
        files = {"x.txt": b"created by lean", "sub/y.bin": bytes(range(200)),
                 "q" * 60 + "/" + "z" * 50 + ".bin": random.Random(7).randbytes(1200)}
        for rel, data in files.items():
            p = src / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        out_tar = td / "created.tar"
        r = run_lean("create", str(out_tar), *files.keys(), cwd=src)
        check("create-exit", r.returncode == 0, r.stderr)
        got = {}
        if r.returncode == 0:
            with tarfile.open(out_tar) as tf:
                for m in tf.getmembers():
                    if m.isreg():
                        got[m.name] = tf.extractfile(m).read()
        check("create-readback", got == files, f"got={list(got)} want={list(files)}")
        # A name too long for the name field, with no `/` to split it at,
        # fails with exit code 1 and writes nothing.
        target = td / "bad.tar"
        (src / ("n" * 101)).write_bytes(b"x")
        r = run_lean("create", str(target), "n" * 101, cwd=src)
        check("create-refuses-long-name", r.returncode == 1 and not target.exists(),
              f"rc={r.returncode} exists={target.exists()}")

        # 4. Lean reads its own archive back with the same manifest.
        if r.returncode == 0:
            r2 = run_lean("manifest", str(out_tar), "out")
            exp2 = []
            for rel, data in files.items():
                joined = "/".join(["out"] + spec_gate(rel))
                exp2.append(f"OK\t{joined}\t{len(data)}\t{sum(data)}")
            check("self-manifest", output_lines(r2.stdout) == exp2,
                  f"lean={output_lines(r2.stdout)} expected={exp2}")

        # 5. Hostile and broken input must fail cleanly, not crash.
        raw = archive_a.read_bytes()
        trunc = td / "trunc.tar"
        trunc.write_bytes(raw[:1000])
        r = run_lean("list", str(trunc))
        check("truncated-fails", r.returncode == 1, f"rc={r.returncode}")
        garbage = td / "garbage.tar"
        garbage.write_bytes(random.Random(1).randbytes(4096))
        r = run_lean("list", str(garbage))
        check("garbage-fails", r.returncode == 1, f"rc={r.returncode}")
        badsum = td / "badsum.tar"
        mutated = bytearray(raw)
        mutated[10] ^= 0xFF  # corrupt a name byte; checksum now wrong
        badsum.write_bytes(bytes(mutated))
        r = run_lean("list", str(badsum))
        check("bad-checksum-fails", r.returncode == 1, f"rc={r.returncode}")

        # 6. Formats the pilot does not read fail to parse, with exit
        # code 1 and nothing on standard output, for both commands.
        unsupported = 0
        for i, (label, raw) in enumerate(unsupported_archives(td)):
            unsupported += 1
            path = td / f"unsupported{i}.tar"
            path.write_bytes(raw)
            for cmd in (["list", str(path)], ["manifest", str(path), "out"]):
                r = run_lean(*cmd)
                check(f"unsupported-fails: {label} ({cmd[0]})",
                      r.returncode == 1 and r.stdout == "",
                      f"rc={r.returncode} out={r.stdout[:200]!r}")

        # 7. Formats the pilot reads give what tarfile reads.
        readable = 0
        for i, (label, raw) in enumerate(readable_archives(td)):
            readable += 1
            path = td / f"readable{i}.tar"
            path.write_bytes(raw)
            ref = tarfile_view(path)
            # tarfile reports an old-style directory (typeflag NUL, name
            # ending in `/`) as typeflag 5. The tool's output is read the
            # same way (`as_tarfile_reads`); no other typeflag changes.
            r = run_lean("list", str(path))
            got = norm([as_tarfile_reads(row) for row in list_rows(r.stdout)])
            want = norm([(escape_name(n), len(d), t) for (n, d, t) in ref])
            check(f"readable-list: {label}", r.returncode == 0 and got == want,
                  f"rc={r.returncode} lean={got} expected={want}")
            r = run_lean("manifest", str(path), "out")
            got = norm_skip([skip_as_tarfile_reads(l) for l in output_lines(r.stdout)])
            want = norm_skip(expected_manifest(ref))
            check(f"readable-manifest: {label}", r.returncode == 0 and got == want,
                  f"rc={r.returncode} lean={got} expected={want}")

    # 8. Axiom check: Verify.lean prints the axioms of exactly the
    # theorems in THEOREMS, and each depends on the three standard axioms
    # at most. Any other axiom, `sorryAx` included, fails the check. It
    # reads this checkout's proofs, so it is left out with `--tool`.
    if rev is None:
        ax = subprocess.run(["lake", "env", "lean", "TarPilot/Verify.lean"],
                            cwd=PILOT_DIR, capture_output=True, text=True)
        ax_out = ax.stdout + ax.stderr
        check("axioms-run", ax.returncode == 0, ax_out[:400])
        allowed = {"propext", "Classical.choice", "Quot.sound"}
        records = {}
        for m in re.finditer(r"'([\w.]+)' depends on axioms: \[(.*?)\]", ax_out, re.DOTALL):
            records[m.group(1)] = {a.strip() for a in m.group(2).split(",") if a.strip()}
        for m in re.finditer(r"'([\w.]+)' does not depend on any axioms", ax_out):
            records[m.group(1)] = set()
        expected = set(THEOREMS)
        check("axioms-names", set(records) == expected,
              f"printed {sorted(records)}, expected {sorted(expected)}")
        for name, used in sorted(records.items()):
            check(f"axioms-{name}", used <= allowed, f"axioms: {sorted(used)}")
        axiom_checks = len(records) + 2

    lean_ver = subprocess.run(["lean", "--version"], capture_output=True,
                              text=True).stdout.strip()

    if rev is None:
        header = [f"Run by `tests/run_tests.py` against Python's `tarfile` module."]
        count = f"- Checks run: {checks} ({axiom_checks} of them on the axioms of the theorems)"
    else:
        header = [
            f"Run by `tests/run_tests.py --tool {rev}` against Python's `tarfile` module.",
            f"The tool was built from commit {rev}, not from this checkout. The axiom",
            "check reads this checkout's proofs, not the tool, so it is left out.",
        ]
        count = f"- Checks run: {checks}, all on the tool"
    lines = [
        "# Test results",
        "",
        *header,
        f"Lean: {lean_ver}. Python: {sys.version.split()[0]}. System tar: {tar_version()}.",
        "",
        count,
        f"- Failures: {len(failures)}",
        f"- Archive A entries compared (list and manifest): {len(ref_entries)}",
        f"- Manifest outcome on archive A: {ok_count} extracted, "
        f"{rej_count} rejected by the path gate, {skip_count} skipped as non-regular",
        f"- Files written by the Lean `create` command and read back by Python: {len(files)}",
        "- Broken inputs that must fail with exit code 1: truncated archive, "
        "random garbage, corrupted checksum",
        f"- Archives in formats the pilot does not read, which must fail with exit code 1 "
        f"under `list` and `manifest`: {unsupported}",
        f"- Archives in other formats it reads, compared with tarfile under `list` and "
        f"`manifest`: {readable}",
        "",
        "How the output is compared with tarfile. tarfile drops the `/` at the end of a",
        "directory name, so directory names in `list` and names in `SKIP` lines are",
        "compared without it. tarfile also reads an entry with typeflag NUL and a name",
        "ending in `/` as a directory, typeflag 5, so for the readable archives the",
        "tool's typeflag 0 on such an entry is read as 5. Every other typeflag is",
        "compared as printed.",
        "",
    ]
    if rev is None:
        lines += ["Axiom check (`TarPilot/Verify.lean`):", "", "```", ax_out.strip(), "```", ""]
    if failures:
        lines += ["## Failures", ""] + [f"- {f}" for f in failures] + [""]
    results.write_text("\n".join(lines))
    print(f"{checks - len(failures)}/{checks} checks passed; results in {results}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
