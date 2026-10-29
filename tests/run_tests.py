#!/usr/bin/env python3
"""Differential tests for the Proven Commons tar pilot.

Compares the tool's `list` and `manifest` commands against Python's
`tarfile` module and against a model of the format the pilot reads,
written below from SPEC.md, independently of the Lean code. Run from
anywhere:

    python3 tests/run_tests.py [--seed N] [--count N] [--tool REV]

It has two parts:

- Fixed cases: an archive of normal, hostile and edge-case entries
  written with tarfile, under eight destinations, and six destinations
  the tool must refuse; archives written by the tool and read back by
  tarfile; broken archives; the formats the pilot does not read (the
  probes of the 2026-10-24 bar audit, and more of the same kinds);
  archives that do not end as SPEC.md says (a lone zero block, entries
  or other bytes after the end, two archives joined, a length that is
  not a whole number of blocks), which must fail to parse; archives
  that do end as it says; and archives in formats it reads, GNU tar's
  own output among them, each compared with tarfile under `list` and
  `manifest`.
- Random cases, from a recorded seed: archives written by tarfile in
  ustar, GNU and pax formats, with hostile names, every POSIX entry
  type, and random data, and the same kind of archives mutated (bytes
  flipped, header fields overwritten with or without a fixed checksum,
  cut, extended, or changed where the archive ends). For each, the
  tool's output must equal the model's. Where the model and tarfile
  both read an unmutated archive, they must also agree on every entry,
  which checks the model against an independent reader.

It builds the Lean project first, so it never checks stale code, writes
`tests/TEST-RESULTS.md`, and exits non-zero if any case fails. The
proofs are checked by `lake comparator --paranoid`, not here.

With `--tool REV`, the checks run against the tool built from commit
REV, in a temporary directory, instead of this checkout's. The checkout
is not changed or built. The record goes to
`tests/TEST-RESULTS-REV.md`, with REV as a short hash, and
`tests/TEST-RESULTS.md` is left as it is. This shows which of these
checks an earlier tool fails:

    python3 tests/run_tests.py --tool 1273382
"""

import argparse
import io
import os
import platform
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
checks = 0
failures = []
# For each kind of check, how many ran and how many failed.
kinds = {}
# The record lists every failure of a fixed case, and this many of the
# random cases; the script prints them all as it runs.
RANDOM_SHOWN = 20


def kind_of(name):
    """A check's name without the archive or destination it ran on."""
    if name.startswith("random "):
        return "random " + name.split(" ", 2)[2]
    kind = re.split(r"[ :]", name, maxsplit=1)[0]
    for cmd in ("list", "manifest"):
        if name.endswith(f"({cmd})"):
            kind += f" ({cmd})"
    return kind


def check(name, ok, detail=""):
    global checks
    checks += 1
    count = kinds.setdefault(kind_of(name), [0, 0])
    count[0] += 1
    if not ok:
        count[1] += 1
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
    # The same with no data. With data, a reader that took the typeflag
    # as a non-regular entry would then fail on the data as a header, so
    # only these show that the typeflag itself is refused.
    for code in b"xgLKDMNSVAZ":
        yield f"typeflag {chr(code)} with size 0", patch_header(
            one_file(tarfile.USTAR_FORMAT, "u.txt", data=b""), 156, bytes([code]))
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
    yield "digit 8 in the size field", patch_header(
        one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"x" * 8), 124, b"00000000008\0")
    yield "NUL before the digits of the size field", patch_header(
        one_file(tarfile.USTAR_FORMAT, "a.txt"), 124, b"\x000000000001\0")
    yield "GNU magic with version 00", patch_header(
        one_file(tarfile.GNU_FORMAT, "a.txt"), 263, b"00")
    yield "GNU header with the last byte of the prefix area set", patch_header(
        one_file(tarfile.GNU_FORMAT, "a.txt"), 499, b"\x01")
    signed = bytearray(one_file(tarfile.USTAR_FORMAT, "\u00e9.txt", data=b"hi\n"))
    signed[148:156] = b" " * 8
    signed[148:156] = b"%06o\0 " % sum(b - 256 if b > 127 else b for b in signed[:512])
    yield "checksum over signed bytes", bytes(signed)
    end = bytearray(one_file(tarfile.USTAR_FORMAT, "a.txt"))
    end[1024 + 511] = 1
    yield "a block of zeros but its last byte where the end should be", bytes(end)
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


def entries_only(raw):
    """An archive written by tarfile without its end: the headers and
    data of its entries, up to its first zero block."""
    return raw[:walk_headers(raw)[1]]


def bad_end_archives():
    """Archives that do not end as SPEC.md says: at least two blocks of
    zeros where a header is due, then only zero bytes, in an input that
    is a whole number of 512-byte blocks. Each must fail to parse.
    (label, archive, whether it hides an entry): an archive hides an
    entry when tarfile with `ignore_zeros=True`, which reads on past
    zero blocks as GNU tar's `--ignore-zeros` does, reads `hidden.txt`
    in it."""
    a = entries_only(one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"visible"))
    full = one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"visible")
    hidden = one_file(tarfile.USTAR_FORMAT, "hidden.txt", data=b"hidden")
    yield "one zero end block only", a + bytes(512), False
    yield "a valid entry hidden after a single zero block", a + bytes(512) + hidden, True
    yield "a nonzero byte after two zero end blocks", a + bytes(1024) + b"\x01" + bytes(511), False
    yield "a nonzero byte in the last block of tarfile's end padding", full[:-1] + b"\x01", False
    yield "two archives joined, the second after the first's end blocks", full + hidden, True
    yield "two archives joined, the first with exactly two end blocks", (
        a + bytes(1024) + hidden), True
    yield "a length one byte past a whole number of blocks, the extra byte zero", (
        full + b"\0"), False
    yield "a length short of a whole number of blocks, the end blocks complete", (
        a + bytes(1024 + 300)), False
    yield "no zero block at all", a, False


def good_end_archives():
    """Archives that end as SPEC.md says. Each must read, as the model
    reads it."""
    a = entries_only(one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"visible"))
    yield "exactly two zero end blocks", a + bytes(1024)
    yield "three zero end blocks", a + bytes(1536)
    yield "tarfile's end, padded to a 10240-byte record", one_file(
        tarfile.USTAR_FORMAT, "a.txt", data=b"visible")
    yield "no entries: two zero blocks", bytes(1024)


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
    yield "a 100-byte name", one_file(tarfile.USTAR_FORMAT, "f" * 96 + ".txt", data=b"full")
    yield "a 155-byte prefix", one_file(tarfile.USTAR_FORMAT, "d" * 155 + "/f.txt", data=b"deep")
    yield "a size field of 12 digits and no terminator", patch_header(
        one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"x" * 15), 124, b"000000000017")
    yield "a size field ending in a space and a NUL", patch_header(
        one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"y"), 124, b"0000000001 \0")
    seven = bytearray(one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"z"))
    seven[148:156] = b" " * 8
    seven[148:156] = b"%07o\0" % sum(seven[:512])
    yield "a checksum of seven digits", bytes(seven)
    yield "a header with its last twelve bytes set", patch_header(
        one_file(tarfile.USTAR_FORMAT, "a.txt", data=b"pad"), 500, b"padding1234!")
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


# ---- A model of the format, from SPEC.md --------------------------------

USTAR_MAGIC = b"ustar\x0000"
GNU_MAGIC = b"ustar  \x00"


def model_octal(field):
    """An octal field: leading spaces, then digits 0 to 7, then NULs or
    spaces. A field with no digits reads as 0 when it is all NUL, and is
    invalid (None) when it holds a space. Anything else is invalid."""
    field = bytes(field)
    digits = field.lstrip(b" ").rstrip(b"\x00 ")
    if any(c < 0x30 or c > 0x37 for c in digits):
        return None
    if not digits:
        return None if b" " in field else 0
    return int(digits, 8)


def model_name(field):
    """A name field: the bytes before the first NUL, as UTF-8, or None."""
    try:
        return bytes(field).split(b"\x00", 1)[0].decode("utf-8")
    except UnicodeDecodeError:
        return None


def model_header(block):
    """(name, size, typeflag) of a header block, or None if the pilot
    must not read it."""
    magic = block[257:265]
    if not (magic == USTAR_MAGIC or (magic == GNU_MAGIC and block[345:500] == bytes(155))):
        return None
    stored = model_octal(block[148:156])
    if stored is None or stored != sum(block[:148]) + 8 * 32 + sum(block[156:512]):
        return None
    size = model_octal(block[124:136])
    typeflag = block[156]
    if size is None or not (typeflag == 0 or 0x30 <= typeflag <= 0x37):
        return None
    name, prefix = model_name(block[0:100]), model_name(block[345:500])
    if name is None or prefix is None:
        return None
    full = name if prefix == "" else prefix + "/" + name
    # Only regular typeflags are followed by data. A regular typeflag with
    # a name ending in `/` is a directory, and must say size 0.
    regular = typeflag in REGULAR_CODES
    if regular and full.endswith("/") and size != 0:
        return None
    return full, (size if regular else 0), typeflag


def model_parse(data):
    """The entries (name, data, typeflag) of an archive, or None when the
    whole archive must fail to parse. The input must be a whole number
    of 512-byte blocks. Where a header is due, a block of zeros ends the
    archive: at least one more block of zeros must follow it, and only
    zero bytes up to the end of the input."""
    if len(data) % 512 != 0:
        return None
    off, entries = 0, []
    while True:
        if off + 512 > len(data):
            return None
        block = data[off:off + 512]
        if block == bytes(512):
            rest = data[off:]
            return entries if len(rest) >= 1024 and rest == bytes(len(rest)) else None
        header = model_header(block)
        if header is None:
            return None
        name, size, typeflag = header
        start = off + 512
        if start + size > len(data):
            return None
        entries.append((name, data[start:start + size], typeflag))
        off = start + (size + 511) // 512 * 512


def model_output(command, data, dest="out"):
    """(exit code, stdout lines) the tool must give."""
    entries = model_parse(data)
    if entries is None:
        return 1, []
    if command == "list":
        return 0, [f"{escape_name(n)}\t{len(d)}\t{t}" for n, d, t in entries]
    return 0, expected_manifest(entries, dest)


# ---- Random archives ----------------------------------------------------

PARTS = ["a", "b", "x.txt", "..", ".", "", "é", "日本", "a b", "-", "\\", "..a", ":",
         "\n", "\t", "\x7f", "\x85", " ", "n" * 60, "p" * 120]
TYPES = [tarfile.REGTYPE, tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.CONTTYPE,
         tarfile.DIRTYPE, tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE,
         tarfile.BLKTYPE, tarfile.FIFOTYPE]
FORMATS = [tarfile.USTAR_FORMAT, tarfile.USTAR_FORMAT, tarfile.GNU_FORMAT, tarfile.PAX_FORMAT]
DESTS = ["out", "out/", "/", "", "/srv/data", "a//b", "../up", "./o"]


def random_name(rng):
    if rng.random() < 0.15:
        # Lengths at the edges of the name and prefix fields.
        kind = rng.randrange(3)
        if kind == 0:
            return "f" * (rng.choice([99, 100, 101]) - 4) + ".txt"
        if kind == 1:
            return "d" * rng.choice([154, 155, 156]) + "/f.txt"
        return "d" * 150 + "/" + "f" * rng.choice([99, 100, 101])
    name = "/".join(rng.choice(PARTS) for _ in range(rng.randrange(1, 5)))
    if rng.random() < 0.15:
        name = "/" + name
    if rng.random() < 0.1:
        name += "/"
    return name or "e"


def random_archive(rng):
    """An archive written by tarfile with random entries."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=rng.choice(FORMATS)) as tf:
        for _ in range(rng.randrange(1, 6)):
            ti = tarfile.TarInfo(random_name(rng))
            ti.type = rng.choice(TYPES)
            ti.mtime = 0
            data = b""
            if ti.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.CONTTYPE):
                # A regular typeflag with a name ending in `/` is a directory
                # that must say size 0; give it data only sometimes.
                if not ti.name.endswith("/") or rng.random() < 0.3:
                    data = rng.randbytes(rng.choice([0, 1, 511, 512, 513, rng.randrange(3000)]))
                ti.size = len(data)
            else:
                if ti.type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    ti.linkname = random_name(rng)
                # tarfile writes the size field but no data for other types,
                # which store none.
                ti.size = rng.choice([0, 0, 0, 1, 512, 1024])
            regular = ti.type in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.CONTTYPE)
            try:
                tf.addfile(ti, io.BytesIO(data) if regular else None)
            except (ValueError, UnicodeError, tarfile.TarError):
                pass
    return buf.getvalue()


def walk_headers(data):
    """Where the header blocks of an archive are, found by following the
    size fields as a reader would, whether or not the headers are valid,
    and where the next header would be after the last of them: the
    first zero block, for an archive that ends as it should."""
    offs, off = [], 0
    while off + 512 <= len(data) and len(offs) < 64:
        block = data[off:off + 512]
        if block == bytes(512):
            break
        offs.append(off)
        size = model_octal(block[124:136]) or 0
        off += 512 + ((size + 511) // 512 * 512 if block[156] in REGULAR_CODES else 0)
    return offs, off


def header_offsets(data):
    return walk_headers(data)[0]


def mutate_end(rng, out):
    """One change where the archive ends: keep one, two or three zero
    blocks; put the archive again after a single zero block, or after
    the whole archive; set a byte after the end to one that is not
    zero; cut the end short; or end with 1023, 1025 or 1536 zero
    bytes."""
    end = min(walk_headers(bytes(out))[1], len(out))
    kind = rng.randrange(6)
    if kind == 0:
        return out[:end] + bytes(512 * rng.choice([1, 2, 3]))
    if kind == 1:
        return out[:end] + bytes(512) + out
    if kind == 2:
        return out + out
    if kind == 3 and end < len(out):
        out[rng.randrange(end, len(out))] = rng.randrange(1, 256)
        return out
    if kind == 4:
        return out[:end + rng.randrange(0, 1025)]
    return out[:end] + bytes(rng.choice([1023, 1025, 1536]))


def field_value(rng, field):
    """A value for one header field, often at the edge of what is valid."""
    n = rng.randrange(0, 1200)
    if field == "size":
        return rng.choice([b"%011o\0" % n, b"%012o" % n, b" %010o\0" % n, b"%010o \0" % n,
                           b"%010o\0 " % n, b"\0%010o\0" % n, b"%010o8\0" % n, b"%010o9 " % n,
                           b" " * 12, bytes(12), b"%011o " % n, b"\x80" + bytes(10) + b"\x01"])
    if field == "magic":
        return rng.choice([b"ustar\x0000", b"ustar  \x00", b"ustar\x00  ", b"ustar 00",
                           b"ustar\x00\x00\x00", b"ustar  0", b"ustar\x0001", b"USTAR\x0000"])
    if field == "typeflag":
        return bytes([rng.choice(b"0123456789\x00LKxgSDAZ")])
    if field == "name":
        return rng.choice([b"f" * 96 + b".txt", b"g" * 100, b"a\xffb", b"a\x00b.txt",
                           b"\xc3\xa9.txt", b"x/../y", b"/abs", b"dir/"]).ljust(100, b"\0")
    if field == "prefix":
        return rng.choice([b"d" * 155, b"d" * 154, bytes(154) + b"\x01", b"1" + bytes(154),
                           b"p\xff", b"pre"]).ljust(155, b"\0")
    return bytes(rng.randrange(256) for _ in range(8))


FIELDS = {"name": (0, 100), "mode": (100, 8), "size": (124, 12), "typeflag": (156, 1),
          "magic": (257, 8), "prefix": (345, 155), "pad": (500, 12)}


def set_checksum(block, how):
    """Write a checksum into a header block: the right one, the right one
    in seven digits, the sum of signed bytes, or none (left stale)."""
    if how == "stale":
        return
    block[148:156] = b" " * 8
    if how == "signed":
        total = sum(b - 256 if b > 127 else b for b in block)
        block[148:156] = b"%06o\0 " % (total % 0o1000000)
    elif how == "seven":
        block[148:156] = b"%07o\0" % sum(block)
    else:
        block[148:156] = b"%06o\0 " % sum(block)


def mutate(rng, data):
    """One to three random changes to an archive, most of them to a field
    of a header, with the checksum then made right, signed, seven digits,
    or left stale, and the others to bytes anywhere, to the length, or
    to where the archive ends."""
    out = bytearray(data)
    for _ in range(rng.randrange(1, 4)):
        kind = rng.randrange(9)
        offs = header_offsets(bytes(out))
        if kind <= 3 and offs:
            base = rng.choice(offs)
            name = rng.choice(list(FIELDS))
            off, width = FIELDS[name]
            value = field_value(rng, name)[:width]
            if rng.random() < 0.3:
                # Only the tail of the field.
                cut = rng.randrange(width)
                value = value[cut:]
                off += cut
            out[base + off:base + off + len(value)] = value
            block = out[base:base + 512]
            set_checksum(block, rng.choice(["right", "right", "right", "signed", "seven", "stale"]))
            out[base:base + 512] = block
        elif kind == 4 and out:
            out[rng.randrange(len(out))] ^= 1 << rng.randrange(8)
        elif kind == 5 and out:
            del out[rng.randrange(len(out)):]
        elif kind == 6:
            out += rng.choice([bytes(512), bytes(1024), rng.randbytes(rng.randrange(1, 600))])
        elif kind == 7:
            out = bytearray(mutate_end(rng, out))
        else:
            base = rng.randrange(max(1, len(out) // 512)) * 512
            del out[base:base + 512]
    return bytes(out)


def tarfile_view_bytes(data):
    """(name, data, typeflag) as tarfile reads each entry, or None."""
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            return [(m.name, tf.extractfile(m).read() if m.isreg() else b"", m.type[0])
                    for m in tf.getmembers()]
    except (tarfile.TarError, UnicodeError, ValueError, OSError):
        return None


def tarfile_agrees(data, entries):
    """Whether tarfile reads what the model reads. tarfile drops the
    trailing `/` of a directory name and returns no data for an entry that
    is not a regular file. It reads an entry with typeflag NUL and a name
    field ending in `/` as a directory, but misses that rule when the name
    is split so the name field is empty, and reads typeflag `0` or `7`
    with a trailing `/` as a regular file. The model, like GNU tar, reads
    any regular typeflag with a name ending in `/` as a directory, so
    such entries are compared as directories on both sides."""
    got = tarfile_view_bytes(data)
    if got is None:
        return False

    def norm(entries):
        out = []
        for n, d, t in entries:
            if t == 0x35 or (t in REGULAR_CODES and n.endswith("/")):
                n, d, t = n.rstrip("/"), b"", 0x35
            out.append((n, d if t in REGULAR_CODES else b"", t))
        return out
    return norm(got) == norm(entries)


def random_cases(seed, count, work):
    """Run `count` random archives, every second one mutated."""
    rng = random.Random(seed)
    stats = {"archives": 0, "mutated": 0, "read": 0, "tarfile": 0}
    path = work / "random.tar"
    for i in range(count):
        data = random_archive(rng)
        mutated = i % 2 == 1
        if mutated:
            data = mutate(rng, data)
        path.write_bytes(data)
        stats["archives"] += 1
        stats["mutated"] += mutated
        dest = rng.choice(DESTS)
        for command in ("list", "manifest"):
            args = [command, str(path)] + ([dest] if command == "manifest" else [])
            r = run_lean(*args)
            want_rc, want = model_output(command, data, dest)
            got = output_lines(r.stdout) if r.stdout.endswith("\n") or not r.stdout else ["(no LF)"]
            check(f"random {i} {command}", (r.returncode, got) == (want_rc, want),
                  f"seed={seed} rc={r.returncode} want_rc={want_rc} got={got[:3]} want={want[:3]}")
        entries = model_parse(data)
        if entries is not None:
            stats["read"] += 1
            if not mutated:
                agrees = tarfile_agrees(data, entries)
                stats["tarfile"] += agrees
                check(f"random {i} model agrees with tarfile", agrees,
                      f"seed={seed} model={entries[:3]} tarfile={(tarfile_view_bytes(data) or [])[:3]}")
    return stats


def main():
    global EXE
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--count", type=int, default=10000,
                    help="random archives, half of them mutated")
    ap.add_argument("--tool", metavar="REV",
                    help="check the tool built from commit REV instead of this checkout's")
    args = ap.parse_args()
    if shutil.which("tar") is None:
        sys.exit("needs GNU tar on PATH: some fixed cases are archives it writes")
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

        # 5b. Usage errors exit with code 2.
        for bad_use in [[], ["frob"], ["manifest", str(archive_a)], ["list"]]:
            r = run_lean(*bad_use)
            check(f"usage {bad_use[:1]}", r.returncode == 2 and r.stdout == "",
                  f"rc={r.returncode}")

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
            check(f"unsupported-model: {label}", model_parse(raw) is None,
                  "the model reads it")

        # 6b. Archives that do not end as SPEC.md says fail to parse, with
        # exit code 1 and nothing on standard output, for both commands.
        # The model must refuse them too. Where the case puts an entry
        # after the zero blocks, tarfile with ignore_zeros=True must read
        # it, so the case shows what a reader that reads on would extract.
        bad_end = 0
        for i, (label, raw, hides) in enumerate(bad_end_archives()):
            bad_end += 1
            path = td / f"bad-end{i}.tar"
            path.write_bytes(raw)
            for cmd in (["list", str(path)], ["manifest", str(path), "out"]):
                r = run_lean(*cmd)
                check(f"end-fails: {label} ({cmd[0]})",
                      r.returncode == 1 and r.stdout == "",
                      f"rc={r.returncode} out={r.stdout[:200]!r}")
            check(f"end-model: {label}", model_parse(raw) is None, "the model reads it")
            if hides:
                with tarfile.open(fileobj=io.BytesIO(raw), ignore_zeros=True) as tf:
                    names = tf.getnames()
                check(f"end-hides: {label}", "hidden.txt" in names, f"tarfile reads {names}")

        # 6c. Archives that end as SPEC.md says read as the model reads
        # them, under both commands.
        good_end = 0
        for i, (label, raw) in enumerate(good_end_archives()):
            good_end += 1
            path = td / f"good-end{i}.tar"
            path.write_bytes(raw)
            check(f"end-model-reads: {label}", model_parse(raw) is not None, "the model refuses it")
            for cmd in (["list", str(path)], ["manifest", str(path), "out"]):
                r = run_lean(*cmd)
                want = model_output(cmd[0], raw, "out")
                check(f"end-reads: {label} ({cmd[0]})",
                      (r.returncode, output_lines(r.stdout)) == want,
                      f"rc={r.returncode} out={r.stdout[:200]!r} want={want}")

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

        # Archive A, the tool's own archive, three broken ones, the
        # format probes, and the end-of-archive cases.
        fixed_archives = 1 + 1 + 3 + unsupported + readable + bad_end + good_end

        # 8. Random archives from the seed.
        stats = random_cases(args.seed, args.count, td)

    lean_ver = subprocess.run(["lake", "env", "lean", "--version"], cwd=PILOT_DIR,
                              capture_output=True, text=True).stdout.strip()

    inputs = fixed_archives + stats["archives"]
    if rev is None:
        header = ["Written by `tests/run_tests.py`. Rerun it to check these numbers."]
    else:
        header = [f"Written by `tests/run_tests.py --tool {rev}`. The tool was built from",
                  f"commit {rev}, not from this checkout."]
    lines = [
        "# Test results",
        "",
        *header,
        "",
        f"- Oracle: Python {platform.python_version()} `tarfile`, and the model of the "
        f"format in `tests/run_tests.py`, which tarfile checks on every unmutated "
        f"archive both read",
        f"- Lean: {lean_ver}",
        f"- System tar: {tar_version()}",
        f"- Seed: {args.seed}",
        f"- Inputs: {inputs}",
        f"- Archives: {fixed_archives} fixed, {stats['archives']} random",
        f"- Random archives: {stats['archives']}, {stats['mutated']} of them mutated; "
        f"the model reads {stats['read']}, and tarfile agrees with it on all "
        f"{stats['tarfile']} unmutated ones both read",
        f"- Checks run: {checks}",
        f"- Archive A entries compared (list and manifest): {len(ref_entries)}",
        f"- Manifest outcome on archive A: {ok_count} extracted, "
        f"{rej_count} rejected by the path gate, {skip_count} skipped as non-regular",
        f"- Files written by the Lean `create` command and read back by Python: {len(files)}",
        "- Broken inputs that must fail with exit code 1: truncated archive, "
        "random garbage, corrupted checksum",
        f"- Archives in formats the pilot does not read, which must fail with exit code 1 "
        f"under `list` and `manifest`, and which the model must refuse: {unsupported}",
        f"- Archives in other formats it reads, compared with tarfile under `list` and "
        f"`manifest`: {readable}",
        f"- Archives that do not end as `SPEC.md` says (a lone zero block, an entry or a "
        f"nonzero byte after the end, two archives joined, a length that is not a whole "
        f"number of blocks), which must fail with exit code 1 under `list` and "
        f"`manifest`: {bad_end}",
        f"- Archives that end as it says (two or more zero blocks, then only zeros), "
        f"compared with the model under `list` and `manifest`: {good_end}",
        f"- Failures: {len(failures)}",
        "",
        "How the fixed archives are compared with tarfile. tarfile drops the `/` at the",
        "end of a directory name, so directory names in `list` and names in `SKIP` lines",
        "are compared without it. tarfile also reads an entry with typeflag NUL and a",
        "name ending in `/` as a directory, typeflag 5, so for the readable archives the",
        "tool's typeflag 0 on such an entry is read as 5. Every other typeflag is",
        "compared as printed. The random archives are compared with the model, and the",
        "model with tarfile as `tarfile_agrees` in `tests/run_tests.py` says.",
        "",
    ]
    if failures:
        lines += ["## Failures by check", "", "| Check | Run | Failed |", "|-------|-----|--------|"]
        lines += [f"| {k} | {n} | {f} |" for k, (n, f) in kinds.items()]
        fixed = [f for f in failures if not f.startswith("random ")]
        rand = [f for f in failures if f.startswith("random ")]
        lines += ["", "## Failures", ""] + [f"- {f}" for f in fixed + rand[:RANDOM_SHOWN]] + [""]
        if len(rand) > RANDOM_SHOWN:
            lines += [f"This lists every failure of a fixed case, and the first {RANDOM_SHOWN} of the",
                      f"{len(rand)} failures of random cases. The script prints them all as it runs.",
                      ""]
    results.write_text("\n".join(lines))
    print(f"{checks - len(failures)}/{checks} checks passed; results in {results}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
