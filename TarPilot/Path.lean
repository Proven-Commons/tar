/-
  Path safety for tar entry names. Plain names exclude empty, dot,
  dot-dot, slash and NUL. The lexical resolver models relative POSIX
  paths without symlinks; filesystem writes remain outside the model.

  Containment lemmas adapted from the F1 evidence in Proven-Commons/mission,
  reviews/tar/evidence/Contained.lean (98521c0).
-/

namespace TarPilot

/-- Split an untrusted archive name into path components. -/
def components (name : String) : List String :=
  name.splitOn "/"

/-- A component that names one entry inside its directory. -/
def PlainName (c : String) : Prop :=
  c ≠ "" ∧ c ≠ "." ∧ c ≠ ".." ∧ '/' ∉ c.toList ∧ Char.ofNat 0 ∉ c.toList

/-- Drop empty and dot components; reject dot-dot, embedded `/`, or NUL. -/
def cleanComponents : List String → Option (List String)
  | [] => some []
  | c :: cs =>
    if c = ".." ∨ '/' ∈ c.toList ∨ Char.ofNat 0 ∈ c.toList then none
    else (cleanComponents cs).map (fun rest =>
      if c = "" ∨ c = "." then rest else c :: rest)

theorem cleanComponents_plain : ∀ (cs out : List String),
    cleanComponents cs = some out → ∀ c ∈ out, PlainName c := by
  intro cs
  induction cs with
  | nil =>
    intro out h
    simp [cleanComponents] at h
    subst h
    simp
  | cons c cs ih =>
    intro out h
    unfold cleanComponents at h
    split at h
    · simp at h
    · rename_i hbad
      cases hrec : cleanComponents cs with
      | none =>
        rw [hrec] at h
        simp at h
      | some rest =>
        rw [hrec] at h
        simp only [Option.map_some, Option.some.injEq] at h
        have ih' := ih rest hrec
        split at h
        · subst h
          exact ih'
        · rename_i hskip
          subst h
          intro x hx
          simp only [List.mem_cons] at hx
          rcases hx with rfl | hx
          · simp only [not_or] at hbad hskip
            exact ⟨hskip.1, hskip.2, hbad.1, hbad.2.1, hbad.2.2⟩
          · exact ih' x hx

/-- Reject absolute names and require a nonempty cleaned relative path. -/
def gate (name : String) : Option (List String) :=
  if name.startsWith "/" then none
  else match cleanComponents (components name) with
    | some (r :: rs) => some (r :: rs)
    | _ => none

/-- Accepted relative paths are nonempty lists of plain names. -/
theorem gate_plain (name : String) (rel : List String) (h : gate name = some rel) :
    (∀ c ∈ rel, PlainName c) ∧ rel ≠ [] := by
  unfold gate at h
  split at h
  · simp at h
  · split at h
    · rename_i r rs hc
      injection h with h
      subst h
      exact ⟨cleanComponents_plain _ _ hc, by simp⟩
    · simp at h

/-- The original cleaner guarantee, retained for callers. -/
theorem cleanComponents_sound (cs out : List String) (h : cleanComponents cs = some out) :
    ".." ∉ out ∧ "" ∉ out ∧ "." ∉ out := by
  have hp := cleanComponents_plain cs out h
  exact ⟨fun hm => (hp _ hm).2.2.1 rfl,
    fun hm => (hp _ hm).1 rfl, fun hm => (hp _ hm).2.1 rfl⟩

/-- The original gate guarantee, retained for callers. -/
theorem gate_sound (name : String) (rel : List String) (h : gate name = some rel) :
    ".." ∉ rel ∧ "" ∉ rel ∧ "." ∉ rel ∧ rel ≠ [] := by
  obtain ⟨hp, hne⟩ := gate_plain name rel h
  exact ⟨fun hm => (hp _ hm).2.2.1 rfl,
    fun hm => (hp _ hm).1 rfl, fun hm => (hp _ hm).2.1 rfl, hne⟩

/-- The components a system sees in a path string: the parts between `/`. -/
def pathComponents (s : String) : List String :=
  (s.split '/').toList.map (·.copy)

/-- Render components with the POSIX separator. Used by the CLI and the theorems. -/
def joinPath (path : List String) : String :=
  String.intercalate "/" path

theorem pathComponents_join (l : List String) (hl : ∀ s ∈ l, '/' ∉ s.toList)
    (hne : l ≠ []) : pathComponents (joinPath l) = l := by
  have h := String.toList_split_intercalate (c := '/') hl
  simp only [hne, ite_false] at h
  exact h

/-- Resolve the components of a relative path as POSIX does, without
    symlinks: `..` drops the last component, or is kept when nothing is
    left to drop or the last is itself `..`; empty and `.` change nothing. -/
def resolve : List String → List String → List String
  | acc, [] => acc
  | acc, c :: cs =>
    if c = "" ∨ c = "." then resolve acc cs
    else if c = ".." then
      if acc = [] ∨ acc.getLast? = some ".." then resolve (acc ++ [".."]) cs
      else resolve acc.dropLast cs
    else resolve (acc ++ [c]) cs

theorem resolve_append : ∀ (xs ys acc : List String),
    resolve acc (xs ++ ys) = resolve (resolve acc xs) ys := by
  intro xs
  induction xs with
  | nil => intro ys acc; simp [resolve]
  | cons c cs ih =>
    intro ys acc
    simp only [List.cons_append, resolve]
    split
    · exact ih ys _
    · split
      · split
        · exact ih ys _
        · exact ih ys _
      · exact ih ys _

theorem resolve_plain : ∀ (rel acc : List String), (∀ c ∈ rel, PlainName c) →
    resolve acc rel = acc ++ rel := by
  intro rel
  induction rel with
  | nil => intro acc _; simp [resolve]
  | cons c cs ih =>
    intro acc h
    have ⟨h1, h2, h3, _, _⟩ := h c (by simp)
    have hcs : ∀ x ∈ cs, PlainName x := fun x hx => h x (by simp [hx])
    simp only [resolve, h1, h2, h3, or_self, ite_false]
    rw [ih _ hcs]
    simp

end TarPilot
