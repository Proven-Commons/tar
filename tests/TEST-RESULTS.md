# Test results

Written by `tests/run_tests.py`. Rerun it to check these numbers.

- Oracle: Python 3.13.17 `tarfile`, and the model of the format in `tests/run_tests.py`, which tarfile checks on every unmutated archive both read
- Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release)
- System tar: tar (GNU tar) 1.35
- Seed: 20261025
- Inputs: 10072
- Archives: 72 fixed, 10000 random
- Random archives: 10000, 5000 of them mutated; the model reads 3966, and tarfile agrees with it on all 3135 unmutated ones both read
- Checks run: 23347
- Archive A entries compared (list and manifest): 23
- Manifest outcome on archive A: 10 extracted, 9 rejected by the path gate, 4 skipped as non-regular
- Files written by the Lean `create` command and read back by Python: 3
- Broken inputs that must fail with exit code 1: truncated archive, random garbage, corrupted checksum
- Archives in formats the pilot does not read, which must fail with exit code 1 under `list` and `manifest`, and which the model must refuse: 35
- Archives in other formats it reads, compared with tarfile under `list` and `manifest`: 19
- Archives that do not end as `SPEC.md` says (a lone zero block, an entry or a nonzero byte after the end, two archives joined, a length that is not a whole number of blocks), which must fail with exit code 1 under `list` and `manifest`: 9
- Archives that end as it says (two or more zero blocks, then only zeros), compared with the model under `list` and `manifest`: 4
- Failures: 0

How the fixed archives are compared with tarfile. tarfile drops the `/` at the
end of a directory name, so directory names in `list` and names in `SKIP` lines
are compared without it. tarfile also reads an entry with typeflag NUL and a
name ending in `/` as a directory, typeflag 5, so for the readable archives the
tool's typeflag 0 on such an entry is read as 5. Every other typeflag is
compared as printed. The random archives are compared with the model, and the
model with tarfile as `tarfile_agrees` in `tests/run_tests.py` says.
