# tar: a tar extractor that cannot escape its destination

This repo reads a tar archive (ustar format) and extracts regular files into an in-memory list of paths and file contents. Every path it emits is built by joining the destination with a cleaned relative path. A machine-checked proof covers the joined string: resolving a relative POSIX path lexically, without symlinks, leaves it inside the resolved destination. This tool writes no extracted files to disk.

It is the first Proven Commons project. The org's home repo, [mission](https://github.com/Proven-Commons/mission), publishes the verified bar it is measured against. Status: built, not yet verified. The [bar audit of 2026-10-24](https://github.com/Proven-Commons/mission/blob/main/reviews/tar/2026-10-24-bar-audit.md) found that the bar is not yet met, and lists the fixes.

The [draft specification](SPEC.md) defines the supported ustar subset and extraction contract. It awaits independent review. GNU magic, extension metadata, invalid UTF-8 path fields, incomplete end blocks, and nonzero trailing data reject the whole archive before `list` or `manifest` prints entries.

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

The gate rules: absolute names are rejected. Any `..` component is rejected, as is a component containing `/` or NUL. Empty and `.` components are dropped. A name with nothing left is rejected. Data files (typeflag `0`, NUL, or `7`) are extracted. Directory, link, and other supported non-data entries are skipped, so a link entry cannot place a later entry outside the destination.

Axiom check: each proof depends only on the standard Lean axioms (`propext`, `Classical.choice`, `Quot.sound`, or a subset). Full output is recorded in `tests/TEST-RESULTS.md`.

## What is not proved

Read this before trusting the pilot with real archives:

- Header parsing, octal fields, checksums, and archive writing are tested, not proved. The tests compare the Lean code against Python's `tarfile` module and against an independent copy of the extraction spec. The [test report](tests/TEST-RESULTS.md) records the original archive and create/readback checks, 524 path cases across eight destinations, and the parser campaign (seed `20261025`: 512 random valid archives and 512 mutated invalid archives, plus fixed regressions). Every parser case checks both `list` and `manifest`; rejected cases must print no stdout. All 256 typeflag bytes are covered. `posixpath` independently checks emitted paths. Lean regressions cover separators, NUL, UTF-8 decoding, header writing, and the old theorem's traversal counterexample.
- Extraction works on an in-memory model. Nothing here writes files to disk, so the step from a proved in-memory path to a safe write on a real filesystem (races, symlinked destination folders) is outside this project for now.
- The reader intentionally rejects formats outside its [supported subset](SPEC.md): GNU magic, pax/GNU extension headers, sparse extension types, base-256 sizes, non-data entries with payloads, and ambiguous NUL-type directory names. It requires block alignment, two zero end blocks, and only zero record padding after them. Some other tar readers accept inputs this pilot rejects. UTF-8 is required for both path fields; other encodings are not converted. The CLI prints tabs and line breaks in names literally; its text output is not an escaped wire format.
- The Lean compiler, runtime, kernel, and hardware are trusted. The tests also rely on Python's `tarfile` and `posixpath` as oracles. Bugs in these are outside the proof.

## Re-check it

```
lake build
lake env lean TarPilot/Verify.lean
python3 tests/run_tests.py
lake check --paranoid
```

The build checks the proofs, but accepts `sorry` with a warning. The second command prints the axiom list. The test script always rebuilds, runs the Lean regressions and every comparison, and rewrites `tests/TEST-RESULTS.md`. It requires each named theorem's axiom list to contain only `propext`, `Classical.choice`, and `Quot.sound`, so `sorryAx` and custom axioms fail the tests.

`lake check --paranoid` needs a working `bubblewrap` sandbox on Linux. It replays proofs through all six bundled kernels and rejects nonstandard axioms. The `Proofs and differential tests` workflow runs the test script and the sandboxed proof check on pull requests and pushes to `main`, and saves the test report as an artifact. Branch protection must separately require this workflow; independent specification approval is still outstanding.

## Layout

- `TarPilot/Path.lean`: the path gate and its proofs.
- `TarPilot/Octal.lean`: octal fields.
- `TarPilot/Header.lean`: the 512-byte ustar header, checksum, build and parse.
- `TarPilot/Archive.lean`: whole-archive parse and write, extraction, and the safety theorems.
- `TarPilot/Verify.lean`: the axiom check.
- `Main.lean`: the command line front end.
- `tests/run_tests.py`: differential tests against Python's `tarfile`.
- `tests/PathSafety.lean`: path safety regressions, including the old statement's counterexample.
- `tests/HeaderSafety.lean`: UTF-8 decoding and header-builder regressions.
- `tests/parser_cases.py`: format regressions and seeded parser comparisons.
- `SPEC.md`: the draft contract for review.
