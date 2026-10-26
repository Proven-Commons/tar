# Planted bugs

Written by `python3 tests/planted_bugs.py --bar <mission>/bar/check.py`.

Each row is one small change to the proofs, the statements, or the list of
theorems checked, made in a copy. On each copy these ran, in this order:

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

## Not here

The review rounds the PR describes also built changes to the code under proof.
A change that alters an answer a statement fixes stops `lake build`, so it is
for the proofs to catch, not for these checks. Those changes were not kept in
the repo, so they are not planted here, and this record says nothing about them.
