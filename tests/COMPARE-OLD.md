# Old and new tool compared

Written by `tests/compare_old.py`. Rerun it to check these numbers.

- Old tool: commit 7517a86. New tool: commit 1273382.
- Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release). Python: 3.13.17.
- Seed: 20261025
- Random archives: 3000, written by Python's `tarfile` in ustar format
- Destinations: `out`, the empty string, `/srv/x`, `a//b`, `./o`
- `manifest` runs: 15000
- Lines the new tool printed: 16360 OK, 11065 REJECT, 18195 SKIP
- Runs that differ as printed: 4200. The names hold no special character, so
  the only escape the new tool can print in them is a backslash as two.
- Runs that differ, after the new escapes are undone: 0

The names hold no special character, and no destination ends in `/` or holds
a special character. So this run checks that nothing else changed. The
changes the PR means to make are covered by the fixed cases in
`tests/run_tests.py`.
