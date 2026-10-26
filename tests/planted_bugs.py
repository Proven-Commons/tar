#!/usr/bin/env python3
"""Plant each fault below in a copy of the project, and record what catches it.

The faults are a `sorry` and an axiom behind a helper lemma, an extra
theorem, and a statement of `Spec.lean` left out of `comparator.json`,
the list of theorems the comparator checks. The version of this script
in the PR for audit F1 and F5 plants the same kinds of fault against
`TarPilot/Verify.lean`. Here they are planted against the proof check
this branch uses, `lake comparator --paranoid`. Two more are a `sorry`
and an axiom in `Spec.escape_noSpecial`, which `comparator.json` does
not list: the proof of `TarPilot.manifest_lines` uses it, so the
comparator checks it with that theorem.

What the proofs catch: a change to the code under proof that alters an
answer a statement fixes stops `lake build`, since the proof of that
statement no longer goes through. What they do not catch: a fault in
the proofs themselves, or in the list of theorems checked. That is
every fault here, and `lake build` passes on each: Lean accepts a
`sorry` with a warning, and an axiom, an extra theorem or a name left
out of `comparator.json` with none. `lake comparator --paranoid`
rejects a `sorry` or an axiom in the proof of a theorem it checks, or
in anything that proof uses. It checks only the theorems
`comparator.json` lists. So it cannot see a listed theorem that the
page does not claim, or a statement in `Spec.lean` that the list leaves
out. Mission's `bar/check.py` checks those (items 2 and 3); pass
`--bar` to run it on each copy. The tests in `tests/run_tests.py` check
the tool, not the proofs, so they report no failures here. Nor do the
proofs cover header parsing, archive writing, the `list` output or
`Main.lean`. Only the tests cover those, and no fault is planted there.

For each fault, this script copies the project into a temporary
directory and makes the change there. On the copy it runs `lake build`,
`lake comparator --paranoid`, `#print axioms` for each theorem
`comparator.json` lists, `python3 tests/run_tests.py --count N`, and,
with `--bar CHECK`, `python3 CHECK COPY --offline`. The first row is the
copy left as it is, and it must pass all of these. A fault is caught
when the comparator rejects it, the tests report failures, or the bar
check gives an item another status than it gives the unchanged copy.
The project itself is never changed.

The script writes the results to tests/PLANTED-BUGS.md. It stops with
an error, and writes no record, if a test run gives no check count or a
count that does not match its exit status. It exits with 1 if a fault is
caught by nothing it ran and is not marked as equivalent.

Usage: python3 tests/planted_bugs.py [--count N] [--bar PATH/TO/mission/bar/check.py]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COUNT = 1000  # random archives for each test run; the tests do not read the proofs
STANDARD = {"propext", "Classical.choice", "Quot.sound"}

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

ESCAPE_STMT = "    ∀ ch ∈ (escape s).toList, isSpecial ch = false := by\n"
ESCAPE_PROOF = ESCAPE_STMT + """  intro ch hch
  unfold escape at hch
  rw [String.toList_join, List.mem_flatMap] at hch
  obtain ⟨t, ht, hc⟩ := hch
  obtain ⟨c, _, rfl⟩ := List.mem_map.mp ht
  exact escapeChar_noSpecial c ch hc"""
ESCAPE_HEAD = ("/-- A printed name holds no special character, so it cannot break a line\n"
               "    or a field of the tool's output. -/\ntheorem escape_noSpecial (s : String) :\n")

SPEC_END = "(parseArchive data).map (extractAll dest) := sorry\n\nend TarPilot\n"
SPEC_EXTRA = ("(parseArchive data).map (extractAll dest) := sorry\n\n"
              "/-- Not a claim of the page. -/\n"
              "theorem extra_claim : gate \"..\" = none := sorry\n\nend TarPilot\n")
CONTAIN_END = "(extractAll dest) := rfl\n\nend TarPilot\n"
EXTRA_STMT = "\ntheorem TarPilot.extra_claim : TarPilot.gate \"..\" = none :="
EXTRA_PROOF = (" by\n  rw [TarPilot.gate_eq]\n"
               "  simp only [Spec.cleanName, Spec.pathComponents, String.toList_split_char]\n"
               "  decide\n")
LIST_END = '    "TarPilot.extractArchive_eq"\n  ],'
LIST_EXTRA = '    "TarPilot.extractArchive_eq",\n    "TarPilot.extra_claim"\n  ],'

# (name, [(file, text to replace, replacement)], why it is equivalent or None)
BUGS = [
    ("none: the copy as it is", [], None),
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
    # An extra theorem that comparator.json lists, with its statement in
    # Spec.lean, but that the page does not claim. The first row proves
    # it by `sorry`; the second proves it, so only a check of the names
    # against the page can catch it.
    ("extra theorem the page does not claim, proved by sorry",
     [("Spec.lean", SPEC_END, SPEC_EXTRA),
      ("Proofs/Contain.lean", CONTAIN_END, CONTAIN_END + EXTRA_STMT + " sorry\n"),
      ("comparator.json", LIST_END, LIST_EXTRA)],
     None),
    ("extra theorem the page does not claim, proved",
     [("Spec.lean", SPEC_END, SPEC_EXTRA),
      ("Proofs/Contain.lean", CONTAIN_END, CONTAIN_END + EXTRA_STMT + EXTRA_PROOF),
      ("comparator.json", LIST_END, LIST_EXTRA)],
     None),
    # A statement of Spec.lean, claimed on the page, that comparator.json
    # leaves out, so nothing checks its proof.
    ("theorem of Spec.lean left out of comparator.json (manifest_lines)",
     [("comparator.json", '    "TarPilot.manifest_lines",\n', "")],
     None),
    # Spec.escape_noSpecial is not listed; the proof of manifest_lines
    # uses it.
    ("sorry in Spec.escape_noSpecial",
     [("Spec/Defs.lean", ESCAPE_PROOF, ESCAPE_STMT + "  sorry")],
     None),
    ("axiom cheat : False behind Spec.escape_noSpecial",
     [("Spec/Defs.lean", ESCAPE_HEAD + ESCAPE_PROOF,
       "axiom cheat : False\n\n" + ESCAPE_HEAD + ESCAPE_STMT + "  exact cheat.elim")],
     None),
]


def failures(out):
    """The failures the test script reports, or None if it gave no
    check count (for example, if the build failed)."""
    m = re.search(r"(\d+)/(\d+) checks passed", out)
    return int(m.group(2)) - int(m.group(1)) if m else None


def sorry_files(out):
    """The files `lake build` warns of a `sorry` in, other than
    Spec.lean, where every statement has one."""
    files = set(re.findall(r"warning: (\S+?):\d+:\d+: declaration uses `sorry`", out))
    return sorted(files - {"Spec.lean"})


def comparator(work):
    """(exit code, what it says) for `lake comparator --paranoid`."""
    r = subprocess.run(["lake", "comparator", "--paranoid"], cwd=work, capture_output=True,
                       text=True)
    out = r.stdout + r.stderr
    if r.returncode == 0:
        return 0, "accepts"
    errors = [l.strip() for l in out.splitlines() if l.strip().startswith("error")]
    return r.returncode, "rejects: " + (errors[-1] if errors else out.strip().splitlines()[-1])


def other_axioms(work):
    """The theorems comparator.json lists whose axioms go beyond the
    three standard ones, with those axioms."""
    names = json.loads((work / "comparator.json").read_text())["theorem_names"]
    src = work / "PlantedAxioms.lean"
    src.write_text("import Proofs\n" + "".join(f"#print axioms {n}\n" for n in names))
    r = subprocess.run(["lake", "env", "lean", src.name], cwd=work, capture_output=True,
                       text=True)
    src.unlink()
    out = r.stdout + r.stderr
    found = []
    for m in re.finditer(r"'([\w.]+)' depends on axioms: \[(.*?)\]", out, re.DOTALL):
        extra = sorted({a.strip() for a in m.group(2).split(",")} - STANDARD)
        if extra:
            found.append(f"{m.group(1)}: {', '.join(extra)}")
    if r.returncode != 0 and not found:
        found.append(f"`#print axioms` failed: {out.strip().splitlines()[-1]}")
    return found


def short(detail):
    """A bar check detail without the middle of a command's output: the
    check joins the last lines of that output with " / "."""
    if " / " not in detail:
        return detail
    return detail.split(": ", 1)[0] + ": ... " + detail.rsplit(" / ", 1)[1]


def bar_items(check, work, tmp):
    """{item: (status, detail)} from mission's bar check, offline."""
    report = Path(tmp) / "bar.json"
    subprocess.run([sys.executable, str(check), str(work), "--offline", "--json", str(report)],
                   capture_output=True, text=True)
    if not report.is_file():
        sys.exit(f"the bar check wrote no report for {work}")
    items = {r["item"]: (r["status"], r["detail"]) for r in json.loads(report.read_text())["items"]}
    report.unlink()
    return items


def run(count, check):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "project"
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git"))
        base_bar = None
        for name, edits, equivalent in BUGS:
            originals = {}
            for rel, old, new in edits:
                path = work / rel
                originals.setdefault(rel, (ROOT / rel).read_text())
                current = path.read_text()
                if current.count(old) != 1:
                    sys.exit(f"{name}: the text to replace is not in {rel} exactly once")
                path.write_text(current.replace(old, new))
            build = subprocess.run(["lake", "build"], cwd=work, capture_output=True, text=True)
            warned = sorry_files(build.stdout + build.stderr)
            cmp_code, cmp_says = comparator(work)
            axioms = other_axioms(work)
            test = subprocess.run([sys.executable, "tests/run_tests.py", "--count", str(count)],
                                  cwd=work, capture_output=True, text=True)
            out = test.stdout + test.stderr
            n = failures(out)
            if n is None:
                sys.exit(f"{name}: the tests gave no check count\n{out[-2000:]}")
            if (n > 0) != (test.returncode != 0):
                sys.exit(f"{name}: the tests report {n} failures but exit with "
                         f"{test.returncode}\n{out[-2000:]}")
            bar = None
            if check:
                items = bar_items(check, work, tmp)
                if base_bar is None:
                    base_bar = items
                bar = [f"item {i}: {base_bar.get(i, ('none',))[0]} to {s}: {short(d)}"
                       for i, (s, d) in sorted(items.items()) if base_bar.get(i, (None,))[0] != s]
            for rel, text in originals.items():
                (work / rel).write_text(text)
            if not edits and (build.returncode != 0 or cmp_code != 0 or n or axioms):
                sys.exit(f"the unchanged copy does not pass: build exit {build.returncode}, "
                         f"comparator {cmp_says}, {n} test failures, axioms {axioms}")
            rows.append((name, edits, equivalent, build.returncode, warned, cmp_code, cmp_says,
                         axioms, n, bar))
            print(f"{name}: build exit {build.returncode}, comparator exit {cmp_code}, "
                  f"{n} test failures" + (f", bar check items that differ: {len(bar)}" if check else ""),
                  flush=True)
    return rows, base_bar


def caught(row):
    _, edits, _, _, _, cmp_code, _, _, n, bar = row
    return bool(edits) and (cmp_code != 0 or n > 0 or bool(bar))


def write(rows, base_bar, count, check):
    steps = ["`lake build`", "`lake comparator --paranoid`",
             "`#print axioms` for each theorem `comparator.json` lists",
             f"`tests/run_tests.py --count {count}`"]
    if check:
        steps.append("mission's `bar/check.py --offline`")
    command = ("python3 tests/planted_bugs.py" + (f" --count {count}" if count != COUNT else "")
               + (" --bar <mission>/bar/check.py" if check else ""))
    lines = [
        "# Planted bugs",
        "",
        f"Written by `{command}`.",
        "",
        "Each row is one small change to the proofs, the statements, or the list of",
        "theorems checked, made in a copy. On each copy these ran, in this order:",
        "",
    ] + [f"- {step};" for step in steps[:-1]] + [f"- {steps[-1]}.", ""]
    if not check:
        lines += ["Mission's bar check was not run (no `--bar`).", ""]
    lines += [
        "The first row is the copy left as it is. A fault is caught when the comparator",
        "rejects it, the tests report failures, or the bar check gives an item another",
        "status than it gives the unchanged copy.",
        "",
    ]
    if base_bar:
        lines += ["On the unchanged copy, the bar check gives: "
                  + ", ".join(f"item {i} {s}" for i, (s, _) in sorted(base_bar.items())) + ".", ""]
    lines += [
        "| Fault | Files | `lake build` | `lake comparator --paranoid` | Axioms beyond the three | "
        "Test failures | Bar check, where it differs | Caught |",
        "|-------|-------|--------------|------------------------------|-------------------------|"
        "---------------|-----------------------------|--------|",
    ]
    for row in rows:
        name, edits, equivalent, code, warned, cmp_code, cmp_says, axioms, n, bar = row
        files = ", ".join(sorted({f"`{rel}`" for rel, _, _ in edits})) or "none"
        build = ("passes" if code == 0 else "fails") + (
            ", warns of a `sorry` in " + ", ".join(f"`{f}`" for f in warned) if warned else "")
        if bar is None:
            bar_cell = "not run"
        else:
            bar_cell = "; ".join(bar).replace("|", "\\|") or "the same"
        if not edits:
            verdict = "(none planted)"
        elif caught(row):
            verdict = "yes"
        else:
            verdict = "equivalent: " + equivalent if equivalent else "NOT CAUGHT"
        lines.append(f"| {name} | {files} | {build} | {cmp_says} | {'; '.join(axioms) or 'none'} "
                     f"| {n} | {bar_cell} | {verdict} |")
    lines += ["", "## The changes", ""]
    for name, edits, *_ in rows:
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
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--count", type=int, default=COUNT,
                    help="random archives for each run of the tests")
    ap.add_argument("--bar", type=Path, metavar="CHECK",
                    help="mission's bar/check.py, to run on each copy as well")
    args = ap.parse_args()
    check = args.bar.resolve() if args.bar else None
    if check and not check.is_file():
        sys.exit(f"no such file: {check}")
    # A run that stops early must not leave an earlier record.
    (ROOT / "tests" / "PLANTED-BUGS.md").unlink(missing_ok=True)
    rows, base_bar = run(args.count, check)
    write(rows, base_bar, args.count, check)
    planted = [r for r in rows if r[1]]
    missed = [r[0] for r in planted if not caught(r) and not r[2]]
    print(f"{sum(map(caught, planted))} of {len(planted)} planted faults caught; "
          "results in tests/PLANTED-BUGS.md")
    if missed:
        sys.exit("not caught by what ran: " + ", ".join(missed)
                 + ("" if check else " (pass --bar to run mission's bar check too)"))


if __name__ == "__main__":
    main()
