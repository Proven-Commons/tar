#!/usr/bin/env python3
"""Plant each fault below in a copy of the project, and check the tests catch it.

The faults here are the three the PR for audit F1 and F5 names: a
planted `sorry`, a planted axiom, and an extra theorem that is not on
the list. Two more are added: a listed theorem left out of
`TarPilot/Verify.lean`, and a `sorry` in `Spec.escape_noSpecial`,
which review question 2 asks about.

What the proofs catch: a change to the code under proof that alters an
answer a statement fixes stops `lake build`, since the proof of that
statement no longer goes through. What they do not catch: a fault in
the proofs themselves, or in the list of theorems checked. That is
every fault here, and `lake build` passes on each: Lean accepts a
`sorry` with a warning, and an axiom, an extra theorem or a missing
`#print axioms` line with none. What catches them is the axiom check
in `tests/run_tests.py`, which reads what `TarPilot/Verify.lean`
prints. Nor do the proofs cover header parsing, archive writing, the
`list` output or `Main.lean`. Only the tests cover those, and no fault
is planted there.

For each fault, this script copies the project into a temporary
directory, makes the change there, runs `lake build` and records
whether it passes, then runs `python3 tests/run_tests.py` and counts
its failures. A fault is caught when that script reports failures. The
project itself is never changed. The script writes the results to
tests/PLANTED-BUGS.md. It stops with an error, and writes no record,
if a test run gives no check count or a count that does not match its
exit status. It exits with 1 if a fault is not caught and is not
marked as equivalent.

Usage: python3 tests/planted_bugs.py
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RESOLVE_PLAIN = """theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
    resolve acc rel = acc ++ rel := by
  intro rel
  induction rel with
  | nil => intro acc _; simp [resolve]
  | cons c cs ih =>
    intro acc h
    have ⟨h1, h2, h3, _⟩ := h c (by simp)
    have hcs : ∀ x ∈ cs, PlainName x := fun x hx => h x (by simp [hx])
    simp only [resolve, h1, h2, h3, or_self, ite_false]
    rw [ih _ hcs]
    simp
"""
RESOLVE_PLAIN_STMT = """theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
    resolve acc rel = acc ++ rel """

ESCAPE_PROOF = """    ∀ ch ∈ (escape s).toList, isSpecial ch = false := by
  intro ch hch
  unfold escape at hch
  rw [String.toList_join, List.mem_flatMap] at hch
  obtain ⟨t, ht, hc⟩ := hch
  obtain ⟨c, _, rfl⟩ := List.mem_map.mp ht
  exact escapeChar_noSpecial c ch hc"""

CONTAIN_END = "(extractAll dest) := rfl\n\nend TarPilot\n"
VERIFY_END = "#print axioms Spec.escape_noSpecial\n"

# (name, [(file, text to replace, replacement)], why it is equivalent or None)
BUGS = [
    # A helper lemma proved by `sorry` or by an axiom. Two of the listed
    # theorems use it: extractAll_resolves_inside, and through it
    # extractArchive_resolves_inside.
    ("sorry in a helper lemma (resolve_plain)",
     [("Proofs/Contain.lean", RESOLVE_PLAIN, RESOLVE_PLAIN_STMT + ":= by\n  exact sorry\n")],
     None),
    ("axiom cheat : False behind a helper lemma (resolve_plain)",
     [("Proofs/Contain.lean", RESOLVE_PLAIN,
       "axiom cheat : False\n\n" + RESOLVE_PLAIN_STMT + ":= by\n  exact cheat.elim\n")],
     None),
    # An extra theorem that Verify.lean prints but the list does not
    # hold. The first row proves it by `sorry`; the second proves it
    # without one, so only the check on the names can catch it.
    ("extra unlisted theorem, proved by sorry",
     [("Proofs/Contain.lean", CONTAIN_END,
       CONTAIN_END + "\ntheorem TarPilot.extra_claim : TarPilot.gate \"..\" = none := sorry\n"),
      ("TarPilot/Verify.lean", VERIFY_END, VERIFY_END + "#print axioms TarPilot.extra_claim\n")],
     None),
    ("extra unlisted theorem, proved",
     [("Proofs/Contain.lean", CONTAIN_END,
       CONTAIN_END + "\ntheorem TarPilot.extra_claim : True := trivial\n"),
      ("TarPilot/Verify.lean", VERIFY_END, VERIFY_END + "#print axioms TarPilot.extra_claim\n")],
     None),
    # Not named by the PR. A listed theorem left out of Verify.lean, which
    # only the check on the names can catch, and a sorry in the theorem
    # review question 2 asks about.
    ("listed theorem left out of Verify.lean (manifest_lines)",
     [("TarPilot/Verify.lean", "#print axioms TarPilot.manifest_lines\n", "")],
     None),
    ("sorry in Spec.escape_noSpecial",
     [("Spec/Defs.lean", ESCAPE_PROOF,
       "    ∀ ch ∈ (escape s).toList, isSpecial ch = false := by\n  sorry")],
     None),
]


def failures(out):
    """The failures the test script reports, or None if it gave no
    check count (for example, if the build failed)."""
    m = re.search(r"(\d+)/(\d+) checks passed", out)
    return int(m.group(2)) - int(m.group(1)) if m else None


def run():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "project"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git"))
        for name, edits, equivalent in BUGS:
            originals = {}
            for rel, old, new in edits:
                path = work / rel
                text = originals.setdefault(rel, (ROOT / rel).read_text())
                current = path.read_text()
                if current.count(old) != 1:
                    sys.exit(f"{name}: the text to replace is not in {rel} exactly once")
                path.write_text(current.replace(old, new))
            build = subprocess.run(["lake", "build"], cwd=work, capture_output=True, text=True)
            warned = "declaration uses `sorry`" in build.stdout + build.stderr
            test = subprocess.run([sys.executable, "tests/run_tests.py"],
                                  cwd=work, capture_output=True, text=True)
            for rel, text in originals.items():
                (work / rel).write_text(text)
            out = test.stdout + test.stderr
            n = failures(out)
            if n is None:
                sys.exit(f"{name}: the tests gave no check count\n{out[-2000:]}")
            if (n > 0) != (test.returncode != 0):
                sys.exit(f"{name}: the tests report {n} failures but exit with "
                         f"{test.returncode}\n{out[-2000:]}")
            fails = [l[5:].split(":")[0] for l in test.stdout.splitlines() if l.startswith("FAIL ")]
            rows.append((name, edits, equivalent, build.returncode, warned, n, fails))
            print(f"{name}: build exit {build.returncode}, {n} failures", flush=True)
    return rows


def write(rows):
    lines = [
        "# Planted bugs",
        "",
        "Written by `python3 tests/planted_bugs.py`. Each row is one small change to the",
        "proofs or to the axiom check, made in a copy. `lake build` ran on the copy, then",
        "`tests/run_tests.py`. A fault is caught when the tests report failures.",
        "",
        "| Fault | Files | `lake build` | Failures | Failing checks |",
        "|-------|-------|--------------|----------|----------------|",
    ]
    for name, edits, equivalent, code, warned, n, fails in rows:
        files = ", ".join(sorted({f"`{rel}`" for rel, _, _ in edits}))
        build = ("passes" if code == 0 else "fails") + (", warns of a `sorry`" if warned else "")
        cell = str(n) if n else ("0, equivalent: " + equivalent if equivalent else "0, NOT CAUGHT")
        lines.append(f"| {name} | {files} | {build} | {cell} | {', '.join(fails)} |")
    lines += ["", "## The changes", ""]
    for name, edits, _, _, _, _, _ in rows:
        for rel, old, new in edits:
            lines += [f"**{name}** in `{rel}`:", "", "```", "- " + old.rstrip("\n").replace("\n", "\n- "),
                      "+ " + new.rstrip("\n").replace("\n", "\n+ "), "```", ""]
    lines += [
        "## Not here",
        "",
        "The review rounds the PR describes also built changes to the code under proof.",
        "A change that alters an answer a statement fixes stops `lake build`, so it is",
        "for the proofs to catch, not for these checks. Those changes were not kept in",
        "the repo, so they are not planted here, and this record says nothing about them.",
        "",
    ]
    (ROOT / "tests" / "PLANTED-BUGS.md").write_text("\n".join(lines))


def main():
    # A run that stops early must not leave an earlier record.
    (ROOT / "tests" / "PLANTED-BUGS.md").unlink(missing_ok=True)
    rows = run()
    write(rows)
    missed = [r[0] for r in rows if not r[5] and not r[2]]
    caught = sum(1 for r in rows if r[5])
    print(f"{caught} of {len(rows)} planted bugs caught; results in tests/PLANTED-BUGS.md")
    if missed:
        sys.exit("not caught: " + ", ".join(missed))


if __name__ == "__main__":
    main()
