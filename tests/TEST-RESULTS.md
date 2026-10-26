# Test results

Run by `tests/run_tests.py` against Python's `tarfile` module.
Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release). Python: 3.13.17. System tar: tar (GNU tar) 1.35.

- Checks run: 121 (14 of them on the axioms of the theorems)
- Failures: 0
- Archive A entries compared (list and manifest): 23
- Manifest outcome on archive A: 10 extracted, 9 rejected by the path gate, 4 skipped as non-regular
- Files written by the Lean `create` command and read back by Python: 3
- Broken inputs that must fail with exit code 1: truncated archive, random garbage, corrupted checksum
- Archives in formats the pilot does not read, which must fail with exit code 1 under `list` and `manifest`: 29
- Archives in other formats it reads, compared with tarfile under `list` and `manifest`: 13

How the output is compared with tarfile. tarfile drops the `/` at the end of a
directory name, so directory names in `list` and names in `SKIP` lines are
compared without it. tarfile also reads an entry with typeflag NUL and a name
ending in `/` as a directory, typeflag 5, so for the readable archives the
tool's typeflag 0 on such an entry is read as 5. Every other typeflag is
compared as printed.

Axiom check (`TarPilot/Verify.lean`):

```
'TarPilot.gate_eq' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.gate_plain' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.manifest_eq' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.manifest_extracted' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.manifest_lines' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.manifest_lines_eq' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_contained' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_joined' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_resolves_inside' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractArchive_eq' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractArchive_resolves_inside' depends on axioms: [propext, Classical.choice, Quot.sound]
'Spec.escape_noSpecial' depends on axioms: [propext, Classical.choice, Quot.sound]
```
