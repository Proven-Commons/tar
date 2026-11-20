# Planted bugs

Written by `python3 tests/planted_bugs.py`. Each row is one small change to the
proofs or to the axiom check, made in a copy. `lake build` ran on the copy, then
`tests/run_tests.py`. A fault is caught when the tests report failures.

| Fault | Files | `lake build` | Failures | Failing checks |
|-------|-------|--------------|----------|----------------|
| sorry in a helper lemma (resolve_plain) | `Proofs/Contain.lean` | passes, warns of a `sorry` | 2 | axioms-TarPilot.extractAll_resolves_inside, axioms-TarPilot.extractArchive_resolves_inside |
| axiom cheat : False behind a helper lemma (resolve_plain) | `Proofs/Contain.lean` | passes | 2 | axioms-TarPilot.extractAll_resolves_inside, axioms-TarPilot.extractArchive_resolves_inside |
| extra unlisted theorem, proved by sorry | `Proofs/Contain.lean`, `TarPilot/Verify.lean` | passes, warns of a `sorry` | 2 | axioms-names, axioms-TarPilot.extra_claim |
| extra unlisted theorem, proved | `Proofs/Contain.lean`, `TarPilot/Verify.lean` | passes | 1 | axioms-names |
| listed theorem left out of Verify.lean (manifest_lines) | `TarPilot/Verify.lean` | passes | 1 | axioms-names |
| sorry in Spec.escape_noSpecial | `Spec/Defs.lean` | passes, warns of a `sorry` | 2 | axioms-Spec.escape_noSpecial, axioms-TarPilot.manifest_lines |

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

**extra unlisted theorem, proved by sorry** in `Proofs/Contain.lean`:

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

**extra unlisted theorem, proved by sorry** in `TarPilot/Verify.lean`:

```
- #print axioms Spec.escape_noSpecial
+ #print axioms Spec.escape_noSpecial
+ #print axioms TarPilot.extra_claim
```

**extra unlisted theorem, proved** in `Proofs/Contain.lean`:

```
- (extractAll dest) := rfl
- 
- end TarPilot
+ (extractAll dest) := rfl
+ 
+ end TarPilot
+ 
+ theorem TarPilot.extra_claim : True := trivial
```

**extra unlisted theorem, proved** in `TarPilot/Verify.lean`:

```
- #print axioms Spec.escape_noSpecial
+ #print axioms Spec.escape_noSpecial
+ #print axioms TarPilot.extra_claim
```

**listed theorem left out of Verify.lean (manifest_lines)** in `TarPilot/Verify.lean`:

```
- #print axioms TarPilot.manifest_lines
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

## Not here

The review rounds the PR describes also built changes to the code under proof.
A change that alters an answer a statement fixes stops `lake build`, so it is
for the proofs to catch, not for these checks. Those changes were not kept in
the repo, so they are not planted here, and this record says nothing about them.
