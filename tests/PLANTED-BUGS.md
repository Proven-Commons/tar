# Planted bugs

Written by `python3 tests/planted_bugs.py --bar <mission>/bar/check.py`.

Each row is one small change, made in a copy: to the proofs, the statements, or
the list of theorems checked, or, in the rows that start `parser:` or
`printer:`, to code no statement is about, which only the tests can catch. On
each copy these ran, in this order:

- `lake build`;
- `lake comparator --paranoid`;
- `#print axioms` for each theorem `comparator.json` lists;
- `tests/run_tests.py --count 1000`;
- mission's `bar/check.py --offline`.

The first row is the copy left as it is. A fault is caught when the comparator
rejects it, the tests report failures, or the bar check gives an item another
status than it gives the unchanged copy.

On the unchanged copy, the bar check gives: item 1 OPEN, item 2 PASS, item 3 PASS, item 4 PASS, item 5 PASS, item 6 PASS, item 7 SKIP.

| Fault | Files | `lake build` | `lake comparator --paranoid` | Axioms beyond the three | Test failures | Bar check, where it differs | Caught |
|-------|-------|--------------|------------------------------|-------------------------|---------------|-----------------------------|--------|
| none: the copy as it is | none | passes | accepts | none | 0 | the same | (none planted) |
| sorry in a helper lemma (resolve_plain) | `Proofs/Contain.lean` | passes, warns of a `sorry` in `Proofs/Contain.lean` | rejects: error: Illegal axiom detected: 'sorryAx' | TarPilot.extractAll_resolves_inside: sorryAx; TarPilot.extractArchive_resolves_inside: sorryAx | 0 | item 3: PASS to OPEN: `lake comparator --paranoid`: a proof is still `sorry`, which an in-progress project may have; item 4: PASS to OPEN: unfinished proofs, which an in-progress project may have: Proofs/Contain.lean:174 sorry | yes |
| axiom cheat : False behind a helper lemma (resolve_plain) | `Proofs/Contain.lean` | passes | rejects: error: Illegal axiom detected: 'TarPilot.Contain.cheat' | TarPilot.extractAll_resolves_inside: TarPilot.Contain.cheat; TarPilot.extractArchive_resolves_inside: TarPilot.Contain.cheat | 0 | item 3: PASS to FAIL: `lake comparator --paranoid` exited 1: ... error: Illegal axiom detected: 'TarPilot.Contain.cheat'; item 4: PASS to FAIL: forbidden features: Proofs/Contain.lean:172 axiom | yes |
| extra theorem the page does not claim, proved by sorry | `Proofs/Contain.lean`, `Spec.lean`, `comparator.json` | passes, warns of a `sorry` in `Proofs/Contain.lean` | rejects: error: Illegal axiom detected: 'sorryAx' | TarPilot.extra_claim: sorryAx | 0 | item 2: PASS to OPEN: 'What is proved' does not name: TarPilot.extra_claim; item 3: PASS to OPEN: `lake comparator --paranoid`: a proof is still `sorry`, which an in-progress project may have; item 4: PASS to OPEN: unfinished proofs, which an in-progress project may have: Proofs/Contain.lean:537 sorry | yes |
| extra theorem the page does not claim, proved | `Proofs/Contain.lean`, `Spec.lean`, `comparator.json` | passes | accepts | none | 0 | item 2: PASS to OPEN: 'What is proved' does not name: TarPilot.extra_claim | yes |
| theorem of Spec.lean left out of comparator.json (manifest_lines) | `comparator.json` | passes | accepts | none | 0 | item 3: PASS to FAIL: `lake comparator --paranoid` passes, but comparator.json does not name these theorems of the challenge file: TarPilot.manifest_lines | yes |
| sorry in Spec.escape_noSpecial | `Spec/Defs.lean` | passes, warns of a `sorry` in `Spec/Defs.lean` | rejects: error: Illegal axiom detected: 'sorryAx' | TarPilot.manifest_lines: sorryAx | 0 | item 3: PASS to OPEN: `lake comparator --paranoid`: a proof is still `sorry`, which an in-progress project may have; item 4: PASS to OPEN: unfinished proofs, which an in-progress project may have: Spec/Defs.lean:123 sorry | yes |
| axiom cheat : False behind Spec.escape_noSpecial | `Spec/Defs.lean` | passes | rejects: error: Illegal axiom detected: 'Spec.cheat' | TarPilot.manifest_lines: Spec.cheat | 0 | item 3: PASS to FAIL: `lake comparator --paranoid` exited 1: ... error: Illegal axiom detected: 'Spec.cheat'; item 4: PASS to FAIL: forbidden features: Spec/Defs.lean:119 axiom | yes |
| parser: the first zero block ends the archive, whatever follows (the rule before tar#7) | `TarPilot/Archive.lean` | passes | accepts | none | 224 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 224 failures | yes |
| parser: a single zero block is an end | `TarPilot/Archive.lean` | passes | accepts | none | 4 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 4 failures | yes |
| parser: bytes after the end blocks are not read | `TarPilot/Archive.lean` | passes | accepts | none | 104 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 104 failures | yes |
| parser: an input of any length is read | `TarPilot/Archive.lean` | passes | accepts | none | 60 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 60 failures | yes |
| parser: a GNU header with something in bytes 345 to 499 is read | `TarPilot/Header.lean` | passes | accepts | none | 10 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 10 failures | yes |
| parser: a pax header (typeflag x) is read as an entry | `TarPilot/Header.lean` | passes | accepts | none | 2 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 2 failures | yes |
| parser: a name that is not UTF-8 is read as empty | `TarPilot/Header.lean` | passes | accepts | none | 8 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 8 failures | yes |
| parser: a link or directory is followed by its size in data (the rule before tar#5) | `TarPilot/Header.lean` | passes | accepts | none | 367 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 367 failures | yes |
| parser: a regular typeflag with a name ending in / and data is read | `TarPilot/Header.lean` | passes | accepts | none | 22 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 22 failures | yes |
| parser: a size field of spaces reads as zero | `TarPilot/Octal.lean` | passes | accepts | none | 2 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 2 failures | yes |
| printer: list prints names as they are, unescaped | `Main.lean` | passes | accepts | none | 293 | item 5: PASS to FAIL: tests/TEST-RESULTS.md records 293 failures | yes |

## The changes

**sorry in a helper lemma (resolve_plain)** in `Proofs/Contain.lean`:

```
- theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
-     resolve acc rel = acc ++ rel := by
-   intro rel
-   induction rel with
-   | nil => intro acc _; simp [resolve]
-   | cons c cs ih =>
-     intro acc h
-     have ⟨h1, h2, h3, _⟩ := h c (by simp)
-     have hcs : ∀ x ∈ cs, PlainName x := fun x hx => h x (by simp [hx])
-     simp only [resolve, h1, h2, h3, or_self, ite_false]
-     rw [ih _ hcs]
-     simp
+ theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
+     resolve acc rel = acc ++ rel := by
+   exact sorry
```

**axiom cheat : False behind a helper lemma (resolve_plain)** in `Proofs/Contain.lean`:

```
- theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
-     resolve acc rel = acc ++ rel := by
-   intro rel
-   induction rel with
-   | nil => intro acc _; simp [resolve]
-   | cons c cs ih =>
-     intro acc h
-     have ⟨h1, h2, h3, _⟩ := h c (by simp)
-     have hcs : ∀ x ∈ cs, PlainName x := fun x hx => h x (by simp [hx])
-     simp only [resolve, h1, h2, h3, or_self, ite_false]
-     rw [ih _ hcs]
-     simp
+ axiom cheat : False
+ 
+ theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
+     resolve acc rel = acc ++ rel := by
+   exact cheat.elim
```

**extra theorem the page does not claim, proved by sorry** in `Spec.lean`:

```
- (parseArchive data).map (extractAll dest) := sorry
- 
- end TarPilot
+ (parseArchive data).map (extractAll dest) := sorry
+ 
+ /-- Not a claim of the page. -/
+ theorem extra_claim : gate ".." = none := sorry
+ 
+ end TarPilot
```

**extra theorem the page does not claim, proved by sorry** in `Proofs/Contain.lean`:

```
- (extractAll dest) := rfl
- 
- end TarPilot
+ (extractAll dest) := rfl
+ 
+ end TarPilot
+ 
+ theorem TarPilot.extra_claim : TarPilot.gate ".." = none := sorry
```

**extra theorem the page does not claim, proved by sorry** in `comparator.json`:

```
-     "TarPilot.extractArchive_eq"
-   ],
+     "TarPilot.extractArchive_eq",
+     "TarPilot.extra_claim"
+   ],
```

**extra theorem the page does not claim, proved** in `Spec.lean`:

```
- (parseArchive data).map (extractAll dest) := sorry
- 
- end TarPilot
+ (parseArchive data).map (extractAll dest) := sorry
+ 
+ /-- Not a claim of the page. -/
+ theorem extra_claim : gate ".." = none := sorry
+ 
+ end TarPilot
```

**extra theorem the page does not claim, proved** in `Proofs/Contain.lean`:

```
- (extractAll dest) := rfl
- 
- end TarPilot
+ (extractAll dest) := rfl
+ 
+ end TarPilot
+ 
+ theorem TarPilot.extra_claim : TarPilot.gate ".." = none := by
+   rw [TarPilot.gate_eq]
+   simp only [Spec.cleanName, Spec.pathComponents, String.toList_split_char]
+   decide
```

**extra theorem the page does not claim, proved** in `comparator.json`:

```
-     "TarPilot.extractArchive_eq"
-   ],
+     "TarPilot.extractArchive_eq",
+     "TarPilot.extra_claim"
+   ],
```

**theorem of Spec.lean left out of comparator.json (manifest_lines)** in `comparator.json`:

```
-     "TarPilot.manifest_lines",
+ 
```

**sorry in Spec.escape_noSpecial** in `Spec/Defs.lean`:

```
-     ∀ ch ∈ (escape s).toList, isSpecial ch = false := by
-   intro ch hch
-   unfold escape at hch
-   rw [String.toList_join, List.mem_flatMap] at hch
-   obtain ⟨t, ht, hc⟩ := hch
-   obtain ⟨c, _, rfl⟩ := List.mem_map.mp ht
-   exact escapeChar_noSpecial c ch hc
+     ∀ ch ∈ (escape s).toList, isSpecial ch = false := by
+   sorry
```

**axiom cheat : False behind Spec.escape_noSpecial** in `Spec/Defs.lean`:

```
- /-- A printed name holds no special character, so it cannot break a line
-     or a field of the tool's output. -/
- theorem escape_noSpecial (s : String) :
-     ∀ ch ∈ (escape s).toList, isSpecial ch = false := by
-   intro ch hch
-   unfold escape at hch
-   rw [String.toList_join, List.mem_flatMap] at hch
-   obtain ⟨t, ht, hc⟩ := hch
-   obtain ⟨c, _, rfl⟩ := List.mem_map.mp ht
-   exact escapeChar_noSpecial c ch hc
+ axiom cheat : False
+ 
+ /-- A printed name holds no special character, so it cannot break a line
+     or a field of the tool's output. -/
+ theorem escape_noSpecial (s : String) :
+     ∀ ch ∈ (escape s).toList, isSpecial ch = false := by
+   exact cheat.elim
```

**parser: the first zero block ends the archive, whatever follows (the rule before tar#7)** in `TarPilot/Archive.lean`:

```
-         if off + 1024 ≤ data.size ∧ zerosFrom data off then some [] else none
+         some []
```

**parser: the first zero block ends the archive, whatever follows (the rule before tar#7)** in `TarPilot/Archive.lean`:

```
-   if data.size % 512 ≠ 0 then none
-   else parseBlocks data 0 (data.size / 512 + 1)
+   parseBlocks data 0 (data.size / 512 + 1)
```

**parser: a single zero block is an end** in `TarPilot/Archive.lean`:

```
-         if off + 1024 ≤ data.size ∧ zerosFrom data off then some [] else none
+         if zerosFrom data off then some [] else none
```

**parser: bytes after the end blocks are not read** in `TarPilot/Archive.lean`:

```
-         if off + 1024 ≤ data.size ∧ zerosFrom data off then some [] else none
+         if off + 1024 ≤ data.size then some [] else none
```

**parser: an input of any length is read** in `TarPilot/Archive.lean`:

```
-   if data.size % 512 ≠ 0 then none
-   else parseBlocks data 0 (data.size / 512 + 1)
+   parseBlocks data 0 (data.size / 512 + 1)
```

**parser: a GNU header with something in bytes 345 to 499 is read** in `TarPilot/Header.lean`:

```
- let gnuPlain := magic = gnuMagic ∧ (sliceList block 345 155).all (· = 0)
+ let gnuPlain := magic = gnuMagic
```

**parser: a pax header (typeflag x) is read as an entry** in `TarPilot/Header.lean`:

```
- t == Char.ofNat 0 || ('0' ≤ t && t ≤ '7')
+ t == Char.ofNat 0 || ('0' ≤ t && t ≤ '7') || t == 'x'
```

**parser: a name that is not UTF-8 is read as empty** in `TarPilot/Header.lean`:

```
-   String.fromUTF8? (ByteArray.mk raw.toArray)
+   some ((String.fromUTF8? (ByteArray.mk raw.toArray)).getD "")
```

**parser: a link or directory is followed by its size in data (the rule before tar#5)** in `TarPilot/Header.lean`:

```
- size := if regular then size else 0
+ size := size
```

**parser: a regular typeflag with a name ending in / and data is read** in `TarPilot/Header.lean`:

```
-     if regular && dirName && size != 0 then none else
+ 
```

**parser: a size field of spaces reads as zero** in `TarPilot/Octal.lean`:

```
-   if digits.isEmpty && bs.any (· == 32) then none else
+ 
```

**printer: list prints names as they are, unescaped** in `Main.lean`:

```
- IO.println s!"{escapeName e.name}\t
+ IO.println s!"{e.name}\t
```

## Not here

The review rounds the PR describes also built changes to the code under proof.
A change that alters an answer a statement fixes stops `lake build`, so it is
for the proofs to catch, not for these checks. Those changes were not kept in
the repo, so they are not planted here, and this record says nothing about them.

The text of tar#6 also said that a reviewer planted 37 bugs in the parser and
printer, that 36 of them still applied to that code, and that the tests caught
all 36. Those bugs were not kept in the repo either. So which one no longer
applied, and why, cannot be read from it, and that run cannot be repeated. The
`parser:` and `printer:` rows above take its place: the faults are in
`tests/planted_bugs.py`, and this record is what it wrote.
