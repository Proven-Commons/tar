# Test results

Written by `tests/run_tests.py`. Rerun it to check these numbers.

- Oracle: Python 3.13.17 `tarfile`, and the model of the format in `tests/run_tests.py`, which tarfile checks on every unmutated archive both read
- Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release)
- Seed: 20261025
- Inputs: 10055
- Archives: 55 fixed, 10000 random
- Random archives: 10000, 5000 of them mutated; the model reads 4732, and tarfile agrees with it on all 3134 unmutated ones both read
- Checks run: 23243
- Archive A entries compared (list and manifest): 23
- Manifest outcome on archive A: 10 extracted, 9 rejected by the path gate, 4 skipped as non-regular
- Files written by the Lean `create` command and read back by Python: 3
- Broken inputs rejected with exit code 1: truncated archive, random garbage, corrupted checksum
- Archives in formats the pilot does not read, rejected with exit code 1 by `list` and `manifest`: 33
- Archives in other formats it reads, compared with tarfile: 17
- Failures: 0
