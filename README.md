# tar: a tar extractor that cannot escape its destination

This repo reads a tar archive (ustar format) and extracts regular files into an in-memory list of paths and file contents. Every path it emits is built by joining the destination with a cleaned relative path. A machine-checked proof covers the joined string: resolving a relative POSIX path lexically, without symlinks, leaves it inside the resolved destination. This tool writes no extracted files to disk.

It is the first Proven Commons project. The org's home repo, [mission](https://github.com/Proven-Commons/mission), publishes the verified bar it is measured against. Status: built, not yet verified. The [bar audit of 2026-10-24](https://github.com/Proven-Commons/mission/blob/main/reviews/tar/2026-10-24-bar-audit.md) found that the bar is not yet met, and lists the fixes.

## Run it

Needs Lean 4.35.0 (install with elan, toolchain pinned in `lean-toolchain`).

```
lake build
.lake/build/bin/tar-pilot list <file.tar>
.lake/build/bin/tar-pilot manifest <file.tar> out
.lake/build/bin/tar-pilot create <out.tar> <file> [more files...]
```

`manifest` prints what extraction would do, in archive order, and writes nothing to disk: `OK` with the final path, size, and byte sum for an extracted file, `REJECT` for a regular file whose name fails the path gate, `SKIP` for a non-regular entry.

## What is proved

The path gate and the extraction rule, in `TarPilot/Path.lean` and `TarPilot/Archive.lean`:

- `cleanComponents_plain` and `gate_plain`: accepted components are plain names, with no empty name, `.`, `..`, embedded `/`, or NUL. The gate also requires a nonempty result. The original `cleanComponents_sound` and `gate_sound` guarantees remain available.
- `extractEntry_contained` and `extractAll_contained`: every accepted path is the destination components followed by a nonempty list of plain names.
- `extractAll_joined`: rendering those components with `joinPath` and splitting the string on `/` recovers the destination followed by the plain names. This assumes the destination components themselves contain no `/`, as when the CLI splits its destination argument.
- `extractAll_resolves_inside` and `extractEntry_resolves_inside`: resolving that rendered string with the relative POSIX lexical resolver in `Path.lean` gives the resolved destination followed by the plain names, under the same destination assumption. Archive names cannot add a parent traversal above the destination. The resolver preserves leading `..`; it does not model absolute-root handling, Windows paths, or symlinks.
- `extractAll_safe` and `extractArchive_safe`: the original component-list guarantee, including extraction from archive bytes.

The CLI's `OK` lines call `extractEntry` and `joinPath`, the same functions used by these statements. `extractAll` filters the results of `extractEntry`. The CLI adds only `REJECT` and `SKIP` diagnostics for entries with no extracted result, preserving archive order. Parsing, diagnostics, and formatting sizes and byte sums remain outside the proof.

The gate rules: absolute names are rejected. Any `..` component is rejected, as is a component containing `/` or NUL. Empty and `.` components are dropped. A name with nothing left is rejected. Only regular files (typeflag `0` or NUL) are extracted. Directory, link, and other entries are skipped, so a link entry cannot place a later entry outside the destination.

Axiom check: each proof depends only on the standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`, or a subset). Full output is recorded in `tests/TEST-RESULTS.md`.

## What is not proved

Read this before trusting the pilot with real archives:

- Header parsing, octal fields, checksums, and archive writing are tested, not proved. The tests compare the Lean code against Python's `tarfile` module and against an independent copy of the extraction spec. Results are in `tests/TEST-RESULTS.md`: the original 14 archive entries and create/readback checks, plus 524 path cases (512 random, seed `20261024`) under eight destinations. Manifest comparisons preserve duplicate names and entry order; `posixpath` independently checks containment of emitted paths. Lean regressions cover embedded separators, NUL, the old theorem's traversal counterexample, and lexical resolution. Broken inputs cover truncated archives, garbage, and bad checksums.
- Extraction works on an in-memory model. Nothing here writes files to disk, so the step from a proved in-memory path to a safe write on a real filesystem (races, symlinked destination folders) is outside this project for now.
- Invalid UTF-8 becomes an empty header field. With a split ustar name, a valid prefix or name can survive while the invalid field is lost. GNU longname and pax path overrides are ignored rather than reliably rejected, so extension-bearing archives can produce incorrect names. Base-256 sizes and sparse files are not supported. Typeflag `7` (contiguous file) is skipped even though Python treats it as regular. These parser and compatibility findings from the audit remain open; use the pilot only for its supported ustar subset.
- The Lean compiler, runtime, kernel, and hardware are trusted. The tests also rely on Python's `tarfile` and `posixpath` as oracles. Bugs in these are outside the proof.

## Re-check it

```
lake build
lake env lean TarPilot/Verify.lean
python3 tests/run_tests.py
```

The build checks the proofs, but accepts `sorry` with a warning. The second command prints the axiom list. The test script always rebuilds, runs the Lean regressions and every comparison, and rewrites `tests/TEST-RESULTS.md`. It requires each named theorem's axiom list to contain only `propext`, `Classical.choice`, and `Quot.sound`, so `sorryAx` and custom axioms fail the tests.

## Layout

- `TarPilot/Path.lean`: the path gate and its proofs.
- `TarPilot/Octal.lean`: octal fields.
- `TarPilot/Header.lean`: the 512-byte ustar header, checksum, build and parse.
- `TarPilot/Archive.lean`: whole-archive parse and write, extraction, and the safety theorems.
- `TarPilot/Verify.lean`: the axiom check.
- `Main.lean`: the command line front end.
- `tests/run_tests.py`: differential tests against Python's `tarfile`.
- `tests/PathSafety.lean`: path safety regressions, including the old statement's counterexample.
