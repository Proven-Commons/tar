# Test results

Run by `tests/run_tests.py` against Python's `tarfile` module.
Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release). Python: 3.12.14.

- Checks run: 40
- Failures: 0
- Archive A entries compared (list and manifest): 14
- Manifest outcome on archive A: 9 extracted, 3 rejected by the path gate, 2 skipped as non-regular
- Files written by the Lean `create` command and read back by Python: 3
- Path regression entries: 524 (512 random, seed 20261024), compared with the spec under 8 destinations and checked with `posixpath`
- `tests/PathSafety.lean`: cleaner, gate, joined-path and relative-resolution regressions
- Broken inputs rejected with exit code 1: truncated archive, random garbage, corrupted checksum

Axiom check (`TarPilot/Verify.lean`):

```
'TarPilot.gate_sound' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.cleanComponents_sound' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_safe' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractArchive_safe' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.cleanComponents_plain' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.gate_plain' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractEntry_contained' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_contained' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_joined' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractAll_resolves_inside' depends on axioms: [propext, Classical.choice, Quot.sound]
'TarPilot.extractEntry_resolves_inside' depends on axioms: [propext, Classical.choice, Quot.sound]
```
