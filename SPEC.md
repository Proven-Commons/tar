# Specification: tar

A reader for tar archives that lists them and says where each regular file would be extracted, without letting any entry land outside the destination. A reviewer who did not write this specification approves it, together with `Spec.lean`, `Spec/Defs.lean`, and the other files `bar.toml` lists.

Archives are bytes. Names are UTF-8 strings. The command-line tool reads a file and prints lines.

## Reading an archive

Scope: POSIX ustar, and GNU headers that carry nothing ustar does not. Anything outside the rules below makes the whole archive fail to parse, rather than be read in a way the pilot does not vouch for.

An archive is a sequence of entries, then its end. Each entry starts with a 512-byte header block. A header of a regular file is followed by its data, padded to a whole number of blocks. Links, devices, directories and FIFOs (types `1` to `6`) store no data, as POSIX says: the next header follows straight after, whatever their size field says, which is how GNU tar and Python's `tarfile` read them.

The end is a block of zeros where a header is due. It must be followed by at least one more block of zeros, and by nothing but zero bytes up to the end of the input, and the input's length must be a whole number of 512-byte blocks. So these fail to parse:

- a single block of zeros followed by the end of the input, or by a block that is not all zeros, such as the header of another entry;
- an entry, or any byte that is not zero, after the end, as when two archives are joined with `cat`;
- an input whose length is not a multiple of 512, even when the bytes past the last whole block are zeros.

GNU tar with `--ignore-zeros`, and Python's `tarfile` with `ignore_zeros=True`, read on past zero blocks and would extract entries after them. Without these rules the pilot would stop at the first zero block, and never list or vouch for those entries.

A header is read only when all of these hold:

- Bytes 257 to 264 are `ustar`, NUL, `00` (POSIX), or `ustar`, two spaces, NUL (GNU). A GNU header must have only zeros in bytes 345 to 499, where ustar keeps its name prefix and GNU keeps times, sparse maps, and volume offsets.
- The checksum field (bytes 148 to 155) is the sum of all 512 bytes, as unsigned numbers, counting the checksum field itself as spaces. A sum over signed bytes, which some old tars wrote and GNU tar and `tarfile` accept, is not read.
- The size field (bytes 124 to 135) and the checksum field are octal: leading spaces, then digits `0` to `7`, then NULs or spaces. A field with no digits reads as zero when it is all NUL, and is not read when it holds a space, as GNU tar refuses it. Base-256 fields are not read.
- The typeflag (byte 156) is NUL or one of `0` to `7`, the POSIX types. GNU long names and long links (`L`, `K`), pax headers (`x`, `g`), and any other type are not read.
- The name field (bytes 0 to 99) and the prefix field (bytes 345 to 499), each up to its first NUL, are valid UTF-8. The entry's name is the name field, or the prefix, `/`, and the name field when the prefix is not empty.
- A regular typeflag (NUL, `0`, `7`) with a name ending in `/`, which older archives use for a directory, has size zero: readers disagree on whether data follows such an entry.

An archive fails to parse when a header is not read, when an entry's data runs past the end of the input, or when the archive does not end as above, which includes an input that stops before its end. Then the tool prints nothing on standard output and exits with code 1, as it does when the file cannot be read.

## The path gate

Each entry's name goes through the gate, which gives the components the entry is extracted under, or rejects the name. The rules:

- A name that starts with `/` is rejected.
- A name with a `..` component, or with a special character, is rejected. The special characters are the control characters (C0, DEL, and C1) and the Unicode line separator U+2028 and paragraph separator U+2029, which some readers take as line breaks.
- Empty and `.` components are dropped.
- A name with nothing left is rejected.

So every component the gate gives is a plain name: not empty, not `.` or `..`, and free of `/` and of special characters.

## Extraction

Only regular files are extracted: typeflag `0`, NUL from older archives, or `7`, a contiguous file, which POSIX lets a reader treat as regular; and a name that does not end in `/`, which older archives use for a directory and GNU tar reads as one. Directories, links, devices, and FIFOs are skipped, so a link entry cannot place a later entry outside the destination.

For each entry, in archive order, the outcome is one of:

- extract: a regular file whose name passes the gate, at the destination followed by the gate's components, with the entry's own data;
- reject: a regular file whose name fails the gate;
- skip: any other entry.

Extraction works on an in-memory list. Nothing is written to disk.

## The command-line tool

`tar-pilot list <file>` prints one line per entry: the name, its data size, and its typeflag as a decimal code, separated by tabs.

`tar-pilot manifest <file> <dest>` prints one line per entry, separated by tabs:

- `OK`, the path, the data size, and the sum of the data bytes, for an extracted entry. The path is the destination exactly as given, then the gate's components joined by `/`: after a `/` when the destination does not end in one, and with nothing before them when the destination is empty.
- `REJECT` and the name, for a rejected entry.
- `SKIP`, the name, and the typeflag code, for a skipped entry.

In `list`, `REJECT` and `SKIP` lines, a backslash in a name is printed as two backslashes, U+2028 and U+2029 as `\u2028` and `\u2029`, and any other special character as `\x` and two lowercase hex digits. So a printed name holds no special character, which `Spec/Defs.lean` proves (`Spec.escape_noSpecial`). Every line ends in a line feed. A destination that holds a special character, or U+FFFD (which the Lean runtime puts in place of bytes that are not UTF-8), is refused, with exit code 2.

`tar-pilot create <out> <file>...` writes a ustar archive of the given files, each under the name given. A long name is split at a `/` into the prefix and name fields, and neither part may be empty, so an absolute name keeps its `/`. A name that does not fit makes it fail with exit code 1, writing nothing.

Any other use prints a usage message and exits with code 2.

## What must always hold

Each property is a theorem in `Spec.lean`, under the name given. The definitions the statements use are in `Spec/Defs.lean`.

| Property | Theorem |
|----------|---------|
| The gate is exactly its rules. | `TarPilot.gate_eq` |
| A name that passes the gate gives a non-empty list of plain names. | `TarPilot.gate_plain` |
| The outcome of each entry is as described under Extraction. | `TarPilot.manifest_eq` |
| The extracted outcomes are exactly the extractor's output, in order. | `TarPilot.manifest_extracted` |
| Each line `manifest` prints is exactly the line described above (`Spec.line`). | `TarPilot.manifest_lines_eq` |
| With a destination free of special characters, a line holds no special character but its tabs, and every `OK` line is the destination as given, then plain names joined by `/`, then a tab. | `TarPilot.manifest_lines` |
| Every extracted path is the destination followed by a non-empty list of plain names. | `TarPilot.extractAll_contained` |
| Joined with `/`, it splits back into the destination components and those names. | `TarPilot.extractAll_joined` |
| Resolved lexically, it is the resolved destination followed by those names, for entries or for an archive read from bytes. | `TarPilot.extractAll_resolves_inside`, `TarPilot.extractArchive_resolves_inside` |
| Extracting an archive read from bytes is parsing it, then extracting the entries. | `TarPilot.extractArchive_eq` |

The statements fix what extraction, the gate, and the `manifest` output do with the entries of a parsed archive. How bytes are parsed into entries, where an archive ends among them, the `list` output, `create`, and the few lines of `Main.lean` that print the manifest and check the destination are fixed by the rules above and checked by the differential tests, not by a proof. No statement is about the lines `list` prints.

## Oracle

Python's `tarfile` module, and a model of the format above written in `tests/run_tests.py` independently of the Lean code. The model is checked against `tarfile` on every unmutated archive both read.
