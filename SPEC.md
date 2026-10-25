# Tar pilot specification

Status: **draft, awaiting independent specification review**. This document
records the intended contract of this implementation. It is not an approval
record and does not establish the org's verified bar.

## Supported archive input

The reader accepts a strict subset of POSIX ustar. It returns the complete
entry list or an error; it never returns a successfully parsed prefix of an
invalid archive.

- Input length is a multiple of 512 bytes. Every entry has a complete
  512-byte header and enough bytes for its declared payload and block padding.
- Header magic is exactly `ustar` followed by NUL, and version is exactly
  `00`. GNU's different magic/version is rejected.
- The checksum is the unsigned sum of all 512 header bytes, treating bytes
  148 through 155 as ASCII spaces. Both checksum and size are octal fields:
  leading spaces and trailing spaces/NUL are removed, remaining bytes must
  be `0` through `7`, and an empty field means zero. Base-256 sizes fail.
- Types NUL, `0`, and `7` are data files. Types `1` through `6` are accepted
  only with size zero and are skipped by extraction. Every other type
  rejects the whole archive, including GNU longname/longlink, pax per-file
  and global headers, and sparse extension types.
- The name and prefix fields are each decoded as UTF-8 up to their first
  NUL. Invalid UTF-8 in either field rejects the whole archive. Bytes after
  a terminating NUL are outside the field value. A nonempty prefix is
  joined to the name with `/`. No invalid field is replaced with empty text.
- A NUL-type entry whose full name ends with `/` is rejected: legacy readers
  can interpret it as a directory rather than a regular file.
- The archive ends with at least two consecutive all-zero blocks. All bytes
  after the first end block must also be zero. Missing end blocks, partial
  blocks, concatenated nonempty archives, and nonzero trailing data are rejected.

Extension-free output from a tool using its pax option can still satisfy
this subset; format labels alone do not determine acceptance. Header mode,
owner, timestamps, device fields, and link targets are ignored. They do not
affect the emitted in-memory file paths or contents. Payload padding need
not be zero. This reader does not decompress archives or write extracted
files to disk.

## Extraction

The parser returns names, original typeflags, and payload bytes in archive
order. `extractEntry` emits a result only for NUL, `0`, or `7` entries whose
names pass the path gate. `extractAll` preserves the order and duplicates of
those results. Non-data entries are skipped; a rejected data-file name does
not reject the archive.

The gate rejects names beginning with `/`, any `..` component, and any
component containing `/` or NUL. It drops empty and `.` components and
requires a nonempty result. It joins those relative components after the
caller-supplied destination components.

`PlainName`, `gate_plain`, `extractAll_contained`, `extractAll_joined`, and
`extractAll_resolves_inside` state the formal guarantees. With slash-free
destination components, the rendered string splits into exactly the
destination followed by nonempty plain names. Resolving it with the relative
POSIX lexical resolver gives the resolved destination followed by those
names. This does not model absolute-root handling, Windows paths, existing
filesystem symlinks, or filesystem races.

## Commands and archive writing

`list` and `manifest` parse the whole archive before printing any entries.
Malformed or unsupported archives exit 1, print an error to stderr, and
produce no stdout. Accepted archives exit 0. `manifest` calls `extractEntry`
and `joinPath` for `OK` results, printing `REJECT` for a data-file name that
fails the gate and `SKIP` for a non-data entry.

The CLI output is a textual view, not an escaped wire format: names containing
tabs or line breaks are printed literally. Formatting, I/O handling, byte sums,
and exit behavior are outside the proof. Tests cover formatting, byte sums,
and archive-rejection exits; they do not cover every I/O failure.

`create` emits regular ustar entries followed by two zero blocks. It fails
when a name cannot fit the ustar name/prefix fields or a size cannot fit an
octal size field. The header builder rejects embedded NUL, unsupported
types, non-data entries with payloads, and ambiguous NUL-type directories.
Mode is fixed at 0644; owner IDs and timestamps are zero. Archive writing is
tested rather than proved.

## Evidence and limits

`python3 tests/run_tests.py` builds the current sources, runs the Lean
regressions, compares accepted archives with Python `tarfile`, checks
rejected cases for exit 1 and no stdout, and checks every printed theorem's
axioms against the standard three. The committed report records seeds,
case counts, versions, and failures. `tests/parser_cases.py` includes the
format and UTF-8 failures from the
[2026-10-24 audit](https://github.com/Proven-Commons/mission/pull/1), all 256
typeflag bytes, valid random archives, and mutated invalid archives.

`lake check --paranoid` replays the built proof declarations through all six
bundled kernels in a sandbox. CI runs both commands. Passing them does not
prove the byte parser or writer, validate this specification's adequacy, or
supply independent approval. The compiler, runtime, kernels, hardware, and
test oracles remain trusted. Requiring the CI check through branch protection
is a separate repository setting.
