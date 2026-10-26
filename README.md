# tar: a tar extractor that cannot escape its destination

This repo reads a tar archive (ustar format) and works out where each regular file would be extracted, without writing anything to disk. Machine-checked proofs show that every `OK` line the command-line tool prints is the destination exactly as given, then plain names: none is empty, `.` or `..`, or holds `/`, a control character, or a Unicode line or paragraph separator. So no entry can climb out of the destination, and no name can forge a line or a field of the tool's output. The path gate, the extraction rule, and every line the tool prints for a parsed archive are proved to be exactly what this page and `SPEC.md` say. Parsing is tested on ten thousand random and mutated archives against a model of the format written from `SPEC.md`, which Python's `tarfile` checks on every unmutated archive both read, and on fixed archives against `tarfile` and GNU tar.

It is the first Proven Commons project, and the subject of the org's [bar audit](https://github.com/Proven-Commons/mission/pull/1) of 2026-10-24, whose findings it fixes.

Status: in progress. The specification has not yet been approved by a reviewer apart from its author, so this is not verified.

## Run it

Needs Lean 4.35.0 (install with elan; the toolchain is pinned in `lean-toolchain`).

```
lake build
.lake/build/bin/tar-pilot list <file.tar>
.lake/build/bin/tar-pilot manifest <file.tar> out
.lake/build/bin/tar-pilot create <out.tar> <file> [more files...]
```

`manifest` prints what extraction would do, in archive order: `OK` with the final path, size, and byte sum for an extracted file, `REJECT` for a regular file whose name fails the path gate, `SKIP` for any other entry. Fields are separated by tabs and lines end in a line feed. In `REJECT` and `SKIP` lines, and in `list`, a backslash in a name is printed as two, the line and paragraph separators U+2028 and U+2029 as `\u2028` and `\u2029`, and a control character as `\x` and two hex digits. A destination that holds any of these special characters, or U+FFFD (which the Lean runtime puts in place of bytes that are not UTF-8), is refused (exit code 2). A U+FFFD typed as such is refused too: by the time the tool reads its arguments, it cannot tell one from the other. `SPEC.md` gives every rule in plain words.

## What is proved

The statements are in `Spec.lean`, the definitions they use in `Spec/Defs.lean`, and the proofs in `Proofs/`. The definitions say what a special character is (a control character, C0, DEL, or C1, or the Unicode line or paragraph separator), what a plain name is, how a path string splits into components, the gate's rules, which entries are regular files, how a path is written under a destination, how a name is printed, the exact line printed for an entry, and how a relative path resolves. The statements are about the code definitions `Spec/Defs.lean` lists, which a reviewer reads with them.

The gate's rules: a name that starts with `/` is rejected. A name with a `..` component, or with a special character, is rejected. Empty and `.` components are dropped. A name with nothing left is rejected. Only regular files are extracted: typeflag `0`, NUL, or `7` (a contiguous file), with a name that does not end in `/`, which older archives use for a directory and GNU tar reads as one. So an entry with a regular typeflag and a name ending in `/` gets a `SKIP` line when its size is zero. When its size is not zero, the whole archive fails to parse, since readers disagree on whether data follows (see the list under What is not proved). Directories, links, and other entries are skipped, so a link entry cannot place a later entry outside the destination.

| Claim | Theorem |
|-------|---------|
| The gate is exactly its rules. | `TarPilot.gate_eq` |
| A name that passes the gate gives a non-empty list of plain names. | `TarPilot.gate_plain` |
| Each entry is extracted, rejected, or skipped exactly as the rules say, an extracted entry at the destination followed by the gate's components and with its own data. | `TarPilot.manifest_eq` |
| The entries the manifest extracts are exactly the extractor's output, in order. | `TarPilot.manifest_extracted` |
| The lines `tar-pilot manifest <file> <dest>` prints are exactly `Spec.line` for each entry: `OK`, the path, the size and the byte sum; `REJECT` and the printed name; or `SKIP`, the printed name and the typeflag code. The path is the destination exactly as given, then the gate's components joined by `/`: `out/a/b` under `out`, and `out/a/b` or `/a/b` under `out/` or `/`, with no doubled `/`. | `TarPilot.manifest_lines_eq` |
| Given a destination with no special character, as the tool requires, the only special characters in a line are its tab separators, and every line that starts with `OK` and a tab continues with the destination, then a non-empty list of plain names, then a tab. | `TarPilot.manifest_lines` |
| Every path the extractor emits is the destination followed by a non-empty list of plain names. | `TarPilot.extractAll_contained` |
| Joined with `/`, such a path splits back into exactly the destination components and those names. | `TarPilot.extractAll_joined` |
| Resolved lexically, it is the resolved destination followed by those names, for an archive given as entries or as bytes: no `..` in an archive reaches above the destination. The resolution reads a path as relative and drops a leading `/`, so for an absolute destination read both sides from `/`. | `TarPilot.extractAll_resolves_inside`, `TarPilot.extractArchive_resolves_inside` |
| Extracting an archive read from bytes is parsing it, then the extractor. | `TarPilot.extractArchive_eq` |

`Spec/Defs.lean` also proves, about the specification alone, that a printed name holds no special character, so it cannot break a line or a field (`Spec.escape_noSpecial`).

## What is not proved

- Parsing bytes into entries: the header layout, octal fields, checksums, and which formats are read. So are the `list` output, `create`, and `Main.lean`: that it prints `o.line` for each outcome of the manifest, and refuses a destination with a special character or U+FFFD. `Main.lean` is a few lines; read it with the statements. The differential tests cover these, against Python's `tarfile` and against a model of the format written from `SPEC.md`. The statements hold for whatever entries a parse gives.
- Formats beyond POSIX ustar. The pilot reads ustar headers, and GNU headers that carry nothing ustar does not. As POSIX says, and as GNU tar and Python's `tarfile` read them, links, devices, directories and FIFOs store no data, whatever their size field says. An archive that uses anything outside the rules in `SPEC.md` fails to parse as a whole, rather than be read in a way the pilot does not vouch for:
  - typeflags outside the POSIX set (NUL and `0` to `7`), among them GNU long names and long links (`L`, `K`), pax headers (`x`, `g`), and GNU sparse, incremental and volume entries. GNU tar writes long names this way by default, and Python's `tarfile` writes pax headers for long or non-ASCII names;
  - a GNU header with anything where ustar keeps its name prefix (bytes 345 to 499), such as the access and change times of an incremental dump. GNU tar 1.35 puts nothing there for short names, in its default, `gnu` and `oldgnu` formats, unless it is asked for an incremental dump, a sparse file or a multi-volume archive;
  - a name or prefix field that is not valid UTF-8;
  - a base-256 size field, or a size field of spaces, which GNU tar refuses;
  - a regular typeflag with a name ending in `/`, which reads as a directory, and a size that is not zero, where readers disagree on whether data follows;
  - a checksum over signed bytes, which some old tars wrote and GNU tar and `tarfile` accept;
  - any other magic, such as an old Unix V7 header.
- Writing to disk. Extraction works on an in-memory list, so the step from a proved path to a safe write on a real filesystem (races, symlinks already on disk, a symlinked destination) is outside this project for now. The proofs resolve paths lexically, as POSIX does when no component is a symlink.
- The destination itself. The proofs say where a path lands relative to the destination, not whether the destination is a safe place to write. The destination is the command-line argument as the Lean runtime decodes it from UTF-8.

## What you must trust

- The Lean kernel and the five external kernels shipped with Lean, which all check the proofs.
- `lake comparator`, which builds the statements and the proofs in a sandbox, exports them, and checks that each proof proves exactly its statement.
- bubblewrap and the Linux kernel's namespaces, which keep the untrusted build from tampering with that check.
- The Lean compiler, with the C compiler and linker shipped with it, and the runtime, which turn the proved definitions into the program that runs.
- Lean's core library, including the compiled code it puts in place of some definitions the proofs reason about (by `implemented_by` and `extern`), such as `Nat.repr` for the printed numbers and string comparison in the gate.
- The operating system and hardware it runs on.
- Python's `tarfile`, and the model of the format in `tests/run_tests.py`, as the oracle in the differential tests. The record names the Python version.

This project has no dependencies beyond Lean itself.

## Re-check it

Needs Linux, [elan](https://github.com/leanprover/elan), bubblewrap (`apt install bubblewrap`), Python 3, and GNU tar, which writes some of the test archives.

```
lake build
lake comparator --paranoid
python3 tests/run_tests.py
```

`lake comparator --paranoid` builds the statements and the proofs in a sandbox. It checks that each theorem in `Proofs/` proves exactly the statement in `Spec.lean`, using only the axioms `propext`, `Classical.choice`, and `Quot.sound`, and replays it through every kernel shipped with Lean. The test script builds the project, runs the fixed and random cases from a recorded seed, and rewrites `tests/TEST-RESULTS.md`. It checks the tool, not the proofs, and does not run the comparator, so run the comparator as well. The bar job in CI (`.github/workflows/bar.yml`) runs both, through mission's `bar/check.py`.

`python3 tests/compare_old.py --new 1273382` builds the tool as it was before the containment change (commit 7517a86) and the tool of that change (commit 1273382), and compares the two on 3,000 random archives under five destinations, from a recorded seed. Once the new escapes in names are undone, the output must be the same. It writes `tests/COMPARE-OLD.md`. Without `--new`, it compares this checkout's tool, and runs differ on purpose: some random names end in `/` with a regular typeflag, and this tool skips such an entry, or refuses the archive when the entry has data.

`python3 tests/run_tests.py --tool 1273382` runs the same checks against the tool of the containment change (commit 1273382), from before the parser changes, and writes `tests/TEST-RESULTS-1273382.md`: 10,377 of the 23,269 checks fail there. The 3,134 checks of the model against `tarfile` do not run the tool, so they pass.

`python3 tests/planted_bugs.py` plants, one at a time in a copy, a `sorry`, an axiom, an extra theorem that is not on the list, and a listed theorem left out of `TarPilot/Verify.lean`. It records that `lake build` passes on each and that the test script fails. It writes `tests/PLANTED-BUGS.md`.

## Layout

- `TarPilot/Path.lean`: the path gate.
- `TarPilot/Octal.lean`: octal fields.
- `TarPilot/Header.lean`: the 512-byte header: checksum, build, and parse.
- `TarPilot/Archive.lean`: whole-archive parse and write, extraction, and the manifest and lines the tool prints.
- `Spec.lean`: the statements, with `sorry` for proofs. A reviewer approves this file.
- `Spec/Defs.lean`: the definitions the statements use, with checks of examples.
- `Proofs.lean` and `Proofs/`: the proofs, under the same names.
- `Main.lean`: the command-line tool.
- `lakefile.toml`: the build. It names the package and its version, its libraries and executable, and the default targets, and sets nothing else.
- `comparator.json`: which theorems `lake comparator` checks, and which axioms it allows.
- `bar.toml`: the record for the bar check: status, authors, approvals, and where things are.
- `SPEC.md`: the specification in plain words.
- `tests/run_tests.py`: the differential tests.
- `tests/compare_old.py`: the tool before the containment change and the tool of that change, compared on random archives.
