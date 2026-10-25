"""Parser contract regressions and seeded comparisons with Python tarfile.

Parsing remains outside the Lean proof. Valid inputs are compared with
tarfile; inputs outside the documented subset must fail without output.
"""

import io
import random
import tarfile

PARSER_SEED = 20261025
RANDOM_ARCHIVES = 512
MUTATED_ARCHIVES = 512
REGULAR = (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.CONTTYPE)
SUPPORTED = REGULAR + (tarfile.LNKTYPE, tarfile.SYMTYPE, tarfile.CHRTYPE,
                       tarfile.BLKTYPE, tarfile.DIRTYPE, tarfile.FIFOTYPE)


def archive(entries, fmt=tarfile.USTAR_FORMAT):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w", format=fmt, encoding="utf-8") as tf:
        for name, data, typ in entries:
            ti = tarfile.TarInfo(name)
            ti.type = typ
            ti.mtime = 0
            ti.size = len(data) if typ in REGULAR else 0
            if typ in (tarfile.LNKTYPE, tarfile.SYMTYPE):
                ti.linkname = "target"
            tf.addfile(ti, io.BytesIO(data) if ti.size else None)
    return out.getvalue()


def patch(raw, offset, value, repair_checksum=True, header_offset=0):
    out = bytearray(raw)
    out[header_offset + offset:header_offset + offset + len(value)] = value
    if repair_checksum:
        out[header_offset + 148:header_offset + 156] = b" " * 8
        checksum = sum(out[header_offset:header_offset + 512])
        out[header_offset + 148:header_offset + 156] = f"{checksum:06o}\0 ".encode()
    return bytes(out)


def reference(raw):
    with tarfile.open(fileobj=io.BytesIO(raw), encoding="utf-8", errors="strict") as tf:
        return [(m.name.rstrip("/") if m.isdir() else m.name,
                 tf.extractfile(m).read() if m.type in REGULAR else b"", m.type[0])
                for m in tf.getmembers()]


def run_parser_cases(work, run_lean, check, expected_manifest):
    counts = {"accepted": 0, "rejected": 0, "entries": 0,
              "seed": PARSER_SEED, "random_archives": RANDOM_ARCHIVES,
              "mutated_archives": MUTATED_ARCHIVES}
    path = work / "parser-case.tar"

    def accepted(label, raw):
        counts["accepted"] += 1
        entries = reference(raw)
        counts["entries"] += len(entries)
        path.write_bytes(raw)
        listed = run_lean("list", str(path))
        actual = []
        for line in listed.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                name, size, flag = parts
                actual.append((name.rstrip("/") if flag == "53" else name, int(size), int(flag)))
        expected = [(name, len(data), flag) for name, data, flag in entries]
        check(f"parser-list-{label}", listed.returncode == 0 and actual == expected,
              f"rc={listed.returncode}, got={actual[:3]}, want={expected[:3]}, {listed.stderr}")
        manifest = run_lean("manifest", str(path), "out")
        lines = []
        for line in manifest.stdout.splitlines():
            parts = line.split("\t")
            if parts[0] == "SKIP":
                parts[1] = parts[1].rstrip("/")
            lines.append("\t".join(parts))
        want = expected_manifest(entries)
        check(f"parser-manifest-{label}", manifest.returncode == 0 and lines == want,
              f"rc={manifest.returncode}, got={lines[:3]}, want={want[:3]}, {manifest.stderr}")

    def rejected(label, raw):
        counts["rejected"] += 1
        path.write_bytes(raw)
        for command in ("list", "manifest"):
            args = (command, str(path), "out") if command == "manifest" else (command, str(path))
            result = run_lean(*args)
            check(f"parser-reject-{label}-{command}", result.returncode == 1 and result.stdout == "",
                  f"rc={result.returncode}, stdout={result.stdout[:160]}, stderr={result.stderr[:160]}")

    one = archive([("safe.txt", b"payload", tarfile.REGTYPE)])
    split = archive([("p" * 30 + "/" + "q" * 90 + "/file.txt", b"x", tarfile.REGTYPE)])
    accepted("empty", bytes(1024))
    accepted("all-types", archive([(f"type-{typ[0]}", b"data", typ) for typ in SUPPORTED]))
    accepted("utf8", archive([("café/notes.txt", b"hello", tarfile.REGTYPE),
                              ("é" * 40 + "/" + "q" * 80 + "/file.txt", b"split", tarfile.REGTYPE)]))
    accepted("contiguous-hostile", archive([("../evil", b"x", tarfile.CONTTYPE),
                                            ("./safe//data", b"data", tarfile.CONTTYPE)]))
    accepted("two-zero-blocks", one[:2048])

    # Formats with extension metadata must not silently change the pathname.
    rejected("gnu-short", archive([("short.txt", b"x", tarfile.REGTYPE)], tarfile.GNU_FORMAT))
    rejected("gnu-long", archive([("d/" + "n" * 120, b"x", tarfile.REGTYPE)], tarfile.GNU_FORMAT))
    rejected("pax-long", archive([("d/" + "n" * 120, b"x", tarfile.REGTYPE)], tarfile.PAX_FORMAT))
    rejected("pax-utf8", archive([("café/notes.txt", b"x", tarfile.REGTYPE)], tarfile.PAX_FORMAT))
    pax = io.BytesIO()
    with tarfile.open(fileobj=pax, mode="w", format=tarfile.PAX_FORMAT,
                      pax_headers={"path": "../../etc/cron.d/x"}) as tf:
        info = tarfile.TarInfo("safe.txt")
        info.size = 1
        tf.addfile(info, io.BytesIO(b"x"))
    rejected("pax-override", pax.getvalue())
    for flag in range(256):
        if bytes([flag]) not in SUPPORTED:
            rejected(f"type-{flag}", patch(one, 156, bytes([flag])))
    for label, raw in (
        ("bad-prefix-utf8", patch(split, 345, b"\xff")),
        ("bad-name-utf8", patch(split, 0, b"\xff")),
        ("bad-both-utf8", patch(patch(split, 0, b"\xff"), 345, b"\xff")),
        ("bad-short-utf8", patch(one, 0, b"\xff")),
        ("bad-magic", patch(one, 257, b"vstar\0")),
        ("bad-version", patch(one, 263, b"01")),
        ("base256-size", patch(one, 124, b"\x80" + bytes(10) + b"\x07")),
        ("non-octal-size", patch(one, 124, b"8")),
        ("bad-checksum", patch(one, 0, b"X", repair_checksum=False)),
        ("one-zero-block", one[:1536]),
        ("no-zero-blocks", one[:1024]),
        ("short-empty", bytes(512)),
        ("partial-block", one[:-1]),
        ("trailing-garbage", one + b"X" + bytes(511)),
        ("second-zero-nonzero", patch(one, 0, b"X", repair_checksum=False, header_offset=1536)),
        ("nonregular-data", patch(one, 156, tarfile.SYMTYPE)),
        ("legacy-directory", patch(patch(one, 0, b"dir/\0"), 156, tarfile.AREGTYPE)),
    ):
        rejected(label, raw)
    # Invalid later entries reject the whole archive, with no clean prefix output.
    two = archive([("first", b"x", tarfile.REGTYPE), ("second", b"y", tarfile.REGTYPE)])
    rejected("late-unsupported", patch(two, 156, b"x", header_offset=1024))
    rejected("late-invalid-utf8", patch(two, 0, b"\xff", header_offset=1024))

    rng = random.Random(PARSER_SEED)
    names = ("file", "dir/nested", "../evil", "/absolute", "./dot//path", "same", "café/data")
    for i in range(RANDOM_ARCHIVES):
        entries = [(rng.choice(names), rng.randbytes(rng.randrange(0, 1025)), rng.choice(SUPPORTED))
                   for _ in range(rng.randrange(1, 7))]
        accepted(f"seeded-{i}", archive(entries))
    # Random positions and values in known-invalid classes, with checksums repaired
    # except in the checksum case. This exercises the actual parser, not just gates.
    for i in range(MUTATED_ARCHIVES):
        kind = i % 5
        if kind == 0:
            bad = patch(one, rng.randrange(0, 8), bytes([rng.randrange(0xF5, 256)]))
        elif kind == 1:
            bad = patch(one, 156, bytes([rng.choice([f for f in range(256) if bytes([f]) not in SUPPORTED])]))
        elif kind == 2:
            bad = patch(one, 263, bytes([rng.randrange(49, 256), 48]))
        elif kind == 3:
            bad = patch(one, rng.randrange(0, 8), b"Z", repair_checksum=False)
        else:
            bad = one[:rng.randrange(0, 2048)]
        rejected(f"mutated-{i}", bad)
    return counts
