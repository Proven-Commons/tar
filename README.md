# tar: a tar extractor that cannot escape its destination

This repo reads a tar archive (ustar format) and extracts regular files into an in-memory list of paths and file contents. Every path it emits is the destination followed by a cleaned relative path. Machine-checked proofs show that every `OK` line the command-line tool prints is the destination exactly as given, then plain names: none is empty, `.` or `..`, or holds `/`, a control character, or a Unicode line or paragraph separator. So no entry can climb out of the destination, and no name can forge a line or a field of the tool's output. Each line the tool prints is proved to be exactly the line `Spec/Defs.lean` writes out from the rules.

It is the first Proven Commons project. Status: built, not yet verified. The org's [bar audit](https://github.com/Proven-Commons/mission/pull/1) lists what is still missing against the verified bar in [mission](https://github.com/Proven-Commons/mission).

## Run it

Needs Lean 4.35.0 (install with elan, toolchain pinned in `lean-toolchain`).

```
lake build
.lake/build/bin/tar-pilot list <file.tar>
.lake/build/bin/tar-pilot manifest <file.tar> out
.lake/build/bin/tar-pilot create <out.tar> <file> [more files...]
```

`manifest` prints what extraction would do, in archive order, and writes nothing to disk: `OK` with the final path, size, and byte sum for an extracted file, `REJECT` for a regular file whose name fails the path gate, `SKIP` for a non-regular entry. Fields are separated by tabs and lines end in a line feed. In `REJECT` and `SKIP` lines, and in `list`, a backslash in a name is printed as two, the line and paragraph separators U+2028 and U+2029 as `\u2028` and `\u2029`, and a control character as `\x` and two hex digits. A destination that holds any of these special characters, or U+FFFD (which the Lean runtime puts in place of bytes that are not UTF-8), is refused (exit code 2). A U+FFFD typed as such is refused too: by the time the tool reads its arguments, it cannot tell one from the other.

## What is proved

The theorems are in `Proofs/Contain.lean`, about the code in `TarPilot/Path.lean` and `TarPilot/Archive.lean`. Their statements use the definitions in `Spec/Defs.lean`: a special character (a control character, C0, DEL, or C1, or the Unicode line or paragraph separator), a plain name (not empty, `.` or `..`, and free of `/` and special characters), the components of a path string (the parts between `/`), the gate's rules, the regular typeflags, a path under a destination, how a name is printed, the exact line printed for an entry, and lexical resolution of a relative path. They are about the code definitions `Spec/Defs.lean` lists, which a reviewer reads with them.

The gate rules, which `gate_eq` proves the gate follows exactly: a name that starts with `/` is rejected. A name with a `..` component, or with a special character, is rejected. Empty and `.` components are dropped. A name with nothing left is rejected. Only regular files (typeflag `0` or NUL) are extracted, which `manifest_eq` proves. Directory, link, and other entries are skipped, so a link entry cannot place a later entry outside the destination.

- `gate_eq`: the gate is exactly its rules.
- `gate_plain`: a name that passes the gate gives a non-empty list of plain names.
- `manifest_eq`: what the tool's `manifest` says about each entry. A regular file whose name passes the gate is extracted at the destination followed by the gate's components, with its own data. A regular file whose name fails is rejected, and anything else is skipped.
- `manifest_extracted`: the entries the manifest extracts are exactly the output of the extractor, `extractAll`, in order.
- `manifest_lines_eq`: the lines `tar-pilot manifest <file> <dest>` prints are exactly `Spec.line` for each entry: `OK`, the path, the size and the byte sum; `REJECT` and the printed name; or `SKIP`, the printed name and the typeflag code. The path is the destination exactly as given, then the gate's components joined by `/`: with destination `out` that is `out/a/b`; with `out/` or `/` it is `out/a/b` or `/a/b`, with no doubled `/`.
- `Spec.escape_noSpecial`, proved in `Spec/Defs.lean` itself, since it is about the specification alone: a printed name holds no special character, so it cannot break a line or a field.
- `manifest_lines`: given a destination with no special character, as the tool requires, the only special characters in a line are its tab separators, and every line that starts with `OK` and a tab continues with the destination, then a non-empty list of plain names, then a tab.
- `extractAll_contained`: every path the extractor emits is the destination followed by a non-empty list of plain names.
- `extractAll_joined`: joined with `/`, such a path splits back into exactly the destination components and those names, when no destination component holds `/`.
- `extractAll_resolves_inside` and `extractArchive_resolves_inside`: resolved lexically, it is the resolved destination followed by those names, for an archive given as entries or as bytes. No `..` in an archive reaches above the destination. The resolution reads a path as relative and drops a leading `/`, so for an absolute destination read both sides from `/`.
- `extractArchive_eq`: extracting an archive read from bytes is parsing it, then the extractor.

The statements fix what extraction does with a parsed archive. They do not fix how bytes are parsed into entries, which the tests cover.

Axiom check: each theorem depends only on the standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`, or a subset). The test script fails on any other axiom, `sorryAx` included, and if the list of theorems checked is not exactly the list above. Full output is recorded in `tests/TEST-RESULTS.md`.

## What is not proved

Read this before trusting the pilot with real archives:

- Header parsing, octal fields, checksums, and archive writing are tested, not proved. The tests compare the Lean code against Python's `tarfile` module and against an independent copy of the extraction spec. Results are in `tests/TEST-RESULTS.md`: 37 checks, 14 of them on the axioms, 0 failures. They cover 23 archive entries with normal files, hostile names (control characters and line separators among them), and a long name split over the ustar prefix field; eight destinations, and six refused: five for a special character or U+FFFD, and one given as bytes that are not UTF-8; and broken inputs (truncated, garbage, bad checksum).
- The `list` output is tested, not proved. So is `Main.lean`: that it prints `o.line` for each outcome of the manifest, and refuses a destination with a special character or U+FFFD. Read it with the statements; it is a few lines.
- Extraction works on an in-memory model. Nothing here writes files to disk, so the step from a proved in-memory path to a safe write on a real filesystem (races, symlinks already on disk, symlinked destination folders) is outside this project for now. The proof resolves paths lexically, as POSIX does when no component is a symlink.
- The destination itself. The proof says where a path lands relative to the destination, not whether the destination is a safe place to write. The destination is the command-line argument as the Lean runtime decodes it from UTF-8.
- Formats beyond POSIX ustar. GNU tar extensions (long name entries, pax headers), base-256 size fields, and sparse files are not supported. A base-256 size field fails to parse, but an archive with a GNU long name or a pax header is not refused, as the bar audit's probes show (findings F2 and F3). Such a header is skipped as a non-regular entry, so the file after it is read under the name in its own ustar header: a long name is cut to 100 bytes, and a pax path is ignored. A name or prefix field that is not valid UTF-8 reads as empty. So a short name like that is rejected, but a name split over both fields, with one field invalid, is extracted under another name. In every probe the path stays inside the destination, since the gate still runs.
- The Lean compiler, runtime, and kernel are trusted, as in every Lean project. A bug in them is outside the proof.

## Re-check it

```
lake build
lake env lean TarPilot/Verify.lean
python3 tests/run_tests.py
```

The build fails if a proof breaks, though it accepts a `sorry` with only a warning. The second command prints the axioms each theorem depends on. The test script builds the project first, fails if any theorem depends on an axiom other than the three standard ones, reruns every comparison, and rewrites `tests/TEST-RESULTS.md`.

`python3 tests/compare_old.py` builds the tool as it was before the containment change (commit 7517a86) and compares the two on 3,000 random archives under five destinations, from a recorded seed. Once the new escapes in names are undone, the output must be the same. It writes `tests/COMPARE-OLD.md`.

`python3 tests/planted_bugs.py` plants, one at a time in a copy, a `sorry`, an axiom, an extra theorem that is not on the list, and a listed theorem left out of `TarPilot/Verify.lean`. It records that `lake build` passes on each and that the test script fails. It writes `tests/PLANTED-BUGS.md`.

## Layout

- `TarPilot/Path.lean`: the path gate.
- `TarPilot/Octal.lean`: octal fields.
- `TarPilot/Header.lean`: the 512-byte ustar header, checksum, build and parse.
- `TarPilot/Archive.lean`: whole-archive parse and write, extraction, and the manifest the tool prints.
- `Spec/Defs.lean`: the definitions the theorems are stated with.
- `Proofs/Contain.lean`: the theorems and their proofs.
- `TarPilot/Verify.lean`: the axiom check.
- `Main.lean`: the command line front end.
- `tests/run_tests.py`: differential tests against Python's `tarfile`.
- `tests/compare_old.py`: the old tool and the new one compared on random archives.
- `tests/planted_bugs.py`: faults planted in the proofs, which the axiom check must catch.
