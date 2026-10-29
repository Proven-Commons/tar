/-
  The theorems about the path gate, extraction, and what
  `tar-pilot manifest` prints.

  The statements use the definitions in `Spec/Defs.lean`: what a plain
  name and a control character are, the components of a path string,
  the gate's rules, the regular typeflags, a path under a destination,
  and lexical path resolution. The helper lemmas are in
  `TarPilot.Contain`.
-/

import TarPilot.Archive
import Spec.Defs

open Spec

namespace TarPilot.Contain

theorem not_mem_of_mem_splitOn {α} [BEq α] [LawfulBEq α] (a : α) :
    ∀ (xs l : List α), l ∈ xs.splitOn a → a ∉ l := by
  intro xs
  induction xs with
  | nil => intro l h; simp [List.splitOn_nil] at h; subst h; simp
  | cons x xs ih =>
    intro l h
    rw [List.splitOn_cons_eq_ite_modifyHead] at h
    split at h
    · simp only [List.mem_cons] at h
      rcases h with rfl | h
      · simp
      · exact ih l h
    · rename_i hx
      obtain ⟨y, ys, hys⟩ := List.exists_cons_of_ne_nil (List.splitOn_ne_nil a xs)
      rw [hys] at h ih
      simp only [List.modifyHead_cons, List.mem_cons] at h
      rcases h with rfl | h
      · intro hmem
        simp only [List.mem_cons] at hmem
        rcases hmem with rfl | hmem
        · simp at hx
        · exact ih y (by simp) hmem
      · exact ih l (by simp [h])

theorem splitPath_eq (s : String) :
    splitPath s = (s.toList.splitOn '/').map String.ofList := by
  unfold splitPath
  rw [String.toList_split_char]

theorem splitPath_ne_nil (s : String) : splitPath s ≠ [] := by
  rw [splitPath_eq]; simp

theorem splitPath_noSlash (s : String) : ∀ d ∈ splitPath s, '/' ∉ d.toList := by
  intro d hd
  rw [splitPath_eq] at hd
  simp only [List.mem_map] at hd
  obtain ⟨l, hl, rfl⟩ := hd
  simpa using not_mem_of_mem_splitOn '/' _ l hl

theorem intercalate_ofList (L : List (List Char)) :
    String.intercalate "/" (L.map String.ofList) = String.ofList (['/'].intercalate L) := by
  apply String.toList_inj.mp
  simp [Function.comp_def]

theorem joinPath_splitPath (s : String) : joinPath (splitPath s) = s := by
  unfold joinPath
  rw [splitPath_eq, intercalate_ofList, List.intercalate_splitOn]
  simp

theorem mem_intercalate (L : List String) (ch : Char) :
    ch ∈ (String.intercalate "/" L).toList → ch = '/' ∨ ∃ s ∈ L, ch ∈ s.toList := by
  intro h
  rw [String.toList_intercalate] at h
  induction L with
  | nil => simp at h
  | cons s L ih =>
    cases L with
    | nil => exact Or.inr ⟨s, by simp, by simpa using h⟩
    | cons t L =>
      simp only [List.map_cons, List.intercalate_cons_cons, List.mem_append] at h
      rcases h with (h | h) | h
      · exact Or.inr ⟨s, by simp, h⟩
      · left; simpa using h
      · rcases ih (by simpa using h) with h | ⟨u, hu, hc⟩
        · exact Or.inl h
        · exact Or.inr ⟨u, by simp [hu], hc⟩

theorem isSpecialChar_eq : isSpecialChar = Spec.isSpecial := rfl

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
          · simp only [not_or, List.any_eq_true, not_exists, not_and, Bool.not_eq_true,
              isSpecialChar_eq] at hbad hskip
            exact ⟨hskip.1, hskip.2, hbad.1,
              fun ch hch => ⟨fun h => hbad.2.1 (h ▸ hch), hbad.2.2 ch hch⟩⟩
          · exact ih' x hx

theorem cleanComponents_eq : ∀ cs : List String, (∀ c ∈ cs, '/' ∉ c.toList) →
    cleanComponents cs =
      if cs.any (fun c => c == ".." || c.toList.any Spec.isSpecial) then none
      else some (cs.filter (fun c => !(c == "" || c == "."))) := by
  intro cs
  induction cs with
  | nil => intro _; rfl
  | cons c cs ih =>
    intro h
    have hc : '/' ∉ c.toList := h c (by simp)
    have hcs : ∀ x ∈ cs, '/' ∉ x.toList := fun x hx => h x (by simp [hx])
    rw [cleanComponents, ih hcs, isSpecialChar_eq]
    by_cases h1 : c = ".."
    · simp [h1]
    · by_cases h2 : c.toList.any Spec.isSpecial = true
      · simp [h1, h2]
      · by_cases h3 : ∃ x, x ∈ cs ∧ (x = ".." ∨ ∃ ch ∈ x.toList, Spec.isSpecial ch = true)
        · simp [h1, h2, hc, h3]
        · by_cases h4 : c = "" ∨ c = "."
          · rcases h4 with h4 | h4 <;> simp [h4, h3]
          · simp only [not_or] at h4
            simp only [Bool.not_eq_true] at h2
            simp [h1, h2, hc, h3, h4.1, h4.2]

theorem pathComponents_join (l : List String) (hl : ∀ s ∈ l, '/' ∉ s.toList)
    (hne : l ≠ []) : pathComponents (String.intercalate "/" l) = l := by
  have h := String.toList_split_intercalate (c := '/') hl
  simp only [hne, ite_false] at h
  exact h

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
    have ⟨h1, h2, h3, _⟩ := h c (by simp)
    have hcs : ∀ x ∈ cs, PlainName x := fun x hx => h x (by simp [hx])
    simp only [resolve, h1, h2, h3, or_self, ite_false]
    rw [ih _ hcs]
    simp

theorem destComponents_noSlash (dest : String) :
    ∀ d ∈ destComponents dest, '/' ∉ d.toList := by
  unfold destComponents
  split
  · simp
  · split
    · intro d hd
      exact splitPath_noSlash dest d (List.dropLast_subset _ hd)
    · exact splitPath_noSlash dest

/-- The path the tool prints for `rel` is the destination string, as
    given, followed by `rel`. -/
theorem joinPath_dest (dest : String) (rel : List String) (hrel : rel ≠ []) :
    joinPath (destComponents dest ++ rel) = under dest (joinPath rel) := by
  unfold destComponents under
  split
  · simp
  · rename_i hd
    split
    · rename_i hlast
      have hsplit : dest.toList = dest.toList.dropLast ++ ['/'] := by
        have hne : dest.toList ≠ [] := by intro h; simp [h] at hlast
        have := List.dropLast_concat_getLast hne
        rw [List.getLast?_eq_some_getLast hne] at hlast
        injection hlast with hl
        rw [hl] at this
        exact this.symm
      have hdl : splitPath dest = splitPath (String.ofList dest.toList.dropLast) ++ [""] := by
        rw [splitPath_eq, splitPath_eq, hsplit, List.splitOn_append_cons_self]
        simp
      rw [hdl, List.dropLast_concat]
      unfold joinPath
      rw [String.intercalate_append_of_ne_nil (splitPath_ne_nil _) hrel]
      have := joinPath_splitPath (String.ofList dest.toList.dropLast)
      unfold joinPath at this
      rw [this]
      apply String.toList_inj.mp
      conv => rhs; rw [String.toList_append, hsplit]
      simp
    · unfold joinPath
      rw [String.intercalate_append_of_ne_nil (splitPath_ne_nil _) hrel]
      have := joinPath_splitPath dest
      unfold joinPath at this
      rw [this]

theorem toString_noSpecial (n : Nat) : ∀ ch ∈ (toString n).toList, Spec.isSpecial ch = false := by
  intro ch hch
  have hrepr : (toString n) = String.ofList (Nat.toDigits 10 n) := Nat.repr_eq_ofList_toDigits
  rw [hrepr, String.toList_ofList] at hch
  have hd := Nat.isDigit_of_mem_toDigits (by decide) (by decide) hch
  simp only [Char.isDigit, Bool.and_eq_true, decide_eq_true_eq,
    UInt32.le_iff_toNat_le] at hd
  simp only [Char.reduceVal, UInt32.reduceToNat] at hd
  have h1 : 48 ≤ ch.toNat := hd.1
  have h2 : ch.toNat ≤ 57 := hd.2
  simp only [Spec.isSpecial, Bool.or_eq_false_iff, decide_eq_false_iff_not,
    Bool.and_eq_false_iff, beq_eq_false_iff_ne, ne_eq]
  omega

theorem escapeChar_eq (c : Char) : escapeChar c = (Spec.escapeChar c).toList := by
  unfold escapeChar Spec.escapeChar
  by_cases h1 : c = '\\'
  · subst h1; decide
  · by_cases h2 : c.toNat = 0x2028
    · simp [h1, h2]
    · by_cases h3 : c.toNat = 0x2029
      · simp [h1, h3]
      · by_cases h4 : Spec.isSpecial c = true
        · simp [h1, h2, h3, isSpecialChar_eq, h4, Spec.hexDigit]
        · simp only [Bool.not_eq_true] at h4
          simp [h1, h2, h3, isSpecialChar_eq, h4]

theorem escapeName_eq (s : String) : escapeName s = Spec.escape s := by
  apply String.toList_inj.mp
  unfold escapeName Spec.escape
  rw [String.toList_ofList, String.toList_join, List.flatMap_map]
  congr 1
  funext c
  exact escapeChar_eq c

theorem escapeName_noSpecial (s : String) :
    ∀ ch ∈ (escapeName s).toList, Spec.isSpecial ch = false := by
  rw [escapeName_eq]
  exact Spec.escape_noSpecial s

theorem byteSum_eq (b : ByteArray) : byteSum b = Spec.byteSum b := by
  unfold byteSum Spec.byteSum
  have : ∀ (l : List UInt8) (acc : Nat),
      l.foldl (fun a x => a + x.toNat) acc = acc + (l.map UInt8.toNat).sum := by
    intro l
    induction l with
    | nil => intro acc; simp
    | cons x xs ih => intro acc; simp [ih]; omega
  rw [this]; simp

end TarPilot.Contain

namespace TarPilot

open TarPilot.Contain

/-- The gate is exactly its rules (`Spec.cleanName`). -/
theorem gate_eq (name : String) : gate name = Spec.cleanName name := by
  unfold gate Spec.cleanName components
  split
  · rfl
  · have hp : splitPath name = pathComponents name := rfl
    rw [cleanComponents_eq _ (splitPath_noSlash name), hp]
    by_cases ha : (pathComponents name).any
        (fun c => c == ".." || c.toList.any Spec.isSpecial) = true
    · simp only [ha, ite_true]
    · simp only [ha]
      cases hk : (pathComponents name).filter (fun c => !(c == "" || c == ".")) with
      | nil => simp
      | cons r rs => simp

/-- The gate gives a non-empty list of plain names. -/
theorem gate_plain (name : String) (rel : List String) :
    gate name = some rel → rel ≠ [] ∧ ∀ c ∈ rel, PlainName c := by
  intro hg
  unfold gate at hg
  split at hg
  · simp at hg
  · split at hg
    · rename_i r rs hc
      injection hg with hg
      subst hg
      exact ⟨by simp, cleanComponents_plain _ _ hc⟩
    · simp at hg

/-- What the manifest says about each entry: a regular file whose name
    passes the gate is extracted at the destination followed by the
    gate's components, with its data; a regular file whose name fails
    is rejected; anything else is skipped. -/
theorem manifest_eq (dest : List String) (entries : List RawEntry) :
    manifest dest entries = entries.map fun e =>
      if regularType e.typeflag e.name then
        match cleanName e.name with
        | some rel => .extract (dest ++ rel) e.data
        | none => .reject e.name
      else .skip e.name e.typeflag := by
  unfold manifest
  congr 1
  funext e
  unfold outcome isRegular regularType
  rw [gate_eq]
  split
  · cases cleanName e.name <;> rfl
  · rfl

/-- Every path `extractAll` emits is the destination followed by a
    non-empty list of plain names. -/
theorem extractAll_contained (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray) :
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, rel ≠ [] ∧ path = dest ++ rel ∧ ∀ c ∈ rel, PlainName c := by
  intro h
  unfold extractAll at h
  rw [List.mem_filterMap] at h
  obtain ⟨e, _, hfe⟩ := h
  split at hfe
  · cases hg : gate e.name with
    | none =>
      rw [hg] at hfe
      simp at hfe
    | some rel =>
      rw [hg] at hfe
      simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at hfe
      obtain ⟨hne, hplain⟩ := gate_plain e.name rel hg
      exact ⟨rel, hne, hfe.1.symm, hplain⟩
  · simp at hfe

/-- Joined with `/`, an emitted path splits back into exactly the
    destination components and the plain names, when no destination
    component holds `/`. -/
theorem extractAll_joined (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray) :
    (∀ d ∈ dest, '/' ∉ d.toList) →
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      pathComponents (joinPath path) = dest ++ rel := by
  intro hdest h
  obtain ⟨rel, hne, hpath, hplain⟩ := extractAll_contained dest entries path bytes h
  refine ⟨rel, hne, hplain, ?_⟩
  subst hpath
  apply pathComponents_join
  · intro s hs
    rcases List.mem_append.mp hs with hs | hs
    · exact hdest s hs
    · exact fun h => ((hplain s hs).2.2.2 '/' h).1 rfl
  · simp [hne]

/-- Resolved lexically, an emitted path is the resolved destination
    followed by the plain names: no `..` in an archive reaches above the
    destination. (`Spec.resolve` reads a relative path; for an absolute
    destination, read both sides from the root.) -/
theorem extractAll_resolves_inside (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray) :
    (∀ d ∈ dest, '/' ∉ d.toList) →
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      resolve [] (pathComponents (joinPath path)) = resolve [] dest ++ rel := by
  intro hdest h
  obtain ⟨rel, hne, hplain, hjoin⟩ := extractAll_joined dest entries path bytes hdest h
  exact ⟨rel, hne, hplain, by rw [hjoin, resolve_append, resolve_plain rel _ hplain]⟩

/-- The same for an archive read from bytes. -/
theorem extractArchive_resolves_inside (dest : List String) (data : ByteArray)
    (out : List (List String × ByteArray)) (path : List String) (bytes : ByteArray) :
    (∀ d ∈ dest, '/' ∉ d.toList) →
    extractArchive dest data = some out → (path, bytes) ∈ out →
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      resolve [] (pathComponents (joinPath path)) = resolve [] dest ++ rel := by
  intro hdest h hmem
  unfold extractArchive at h
  cases hp : parseArchive data with
  | none =>
    rw [hp] at h
    simp at h
  | some entries =>
    rw [hp] at h
    simp only [Option.map_some, Option.some.injEq] at h
    subst h
    exact extractAll_resolves_inside dest entries path bytes hdest hmem

/-- The entries the manifest extracts are exactly the output of
    `extractAll`, in the same order. -/
theorem manifest_extracted (dest : List String) (entries : List RawEntry) :
    (manifest dest entries).filterMap Outcome.extracted = extractAll dest entries := by
  have h : ∀ e : RawEntry, (outcome dest e).extracted =
      if isRegular e then (gate e.name).map fun rel => (dest ++ rel, e.data) else none := by
    intro e
    unfold outcome
    by_cases hr : isRegular e
    · cases gate e.name <;> simp [hr, Outcome.extracted]
    · simp [hr, Outcome.extracted]
  simp only [manifest, extractAll, List.filterMap_map]
  congr 1
  funext e
  exact h e

/-- What `tar-pilot manifest <file> <dest>` prints: one line, `o.line`,
    for each outcome `o` of the manifest, given a destination with no
    special character (the tool refuses any other). The only special
    characters in a line are its tab separators, so no name can break a
    line. And every line that starts with `OK` and a tab continues with
    the given destination, then a non-empty list of plain names joined
    by `/`, then a tab. (`manifest_lines_eq` gives each line exactly.) -/
theorem manifest_lines (dest : String) (entries : List RawEntry)
    (hdest : ∀ ch ∈ dest.toList, Spec.isSpecial ch = false)
    (o : Outcome) (ho : o ∈ manifest (destComponents dest) entries) :
    (∀ ch ∈ o.line.toList, Spec.isSpecial ch = true → ch = '\t') ∧
    (o.line.toList.take 3 = ['O', 'K', '\t'] →
      ∃ rel rest, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
        o.line = "OK\t" ++ under dest (String.intercalate "/" rel) ++ "\t" ++ rest) := by
  unfold manifest at ho
  obtain ⟨e, _, rfl⟩ := List.mem_map.mp ho
  unfold outcome
  split
  · split
    · rename_i rel hg
      obtain ⟨hne, hplain⟩ := gate_plain e.name rel hg
      have hjoin := joinPath_dest dest rel hne
      have hpath : ∀ ch ∈ (joinPath (destComponents dest ++ rel)).toList,
          Spec.isSpecial ch = false := by
        rw [hjoin]
        intro ch hch
        unfold under at hch
        have hrel : ∀ ch ∈ (joinPath rel).toList, Spec.isSpecial ch = false := by
          intro ch hch
          rcases mem_intercalate rel ch hch with rfl | ⟨s, hs, hcs⟩
          · decide
          · exact ((hplain s hs).2.2.2 ch hcs).2
        split at hch
        · exact hrel ch hch
        · split at hch
          · simp only [String.toList_append, List.mem_append] at hch
            rcases hch with h | h
            · exact hdest ch h
            · exact hrel ch h
          · simp only [String.toList_append, List.mem_append] at hch
            rcases hch with (h | h) | h
            · exact hdest ch h
            · simp at h; subst h; decide
            · exact hrel ch h
      constructor
      · intro ch hch hc
        simp only [Outcome.line, String.toList_append, List.mem_append] at hch
        rcases hch with ((((h | h) | h) | h) | h) | h
        · simp at h; rcases h with rfl | rfl | rfl <;> (revert hc; decide)
        · rw [hpath ch h] at hc; simp at hc
        · simpa using h
        · rw [toString_noSpecial _ ch h] at hc; simp at hc
        · simpa using h
        · rw [toString_noSpecial _ ch h] at hc; simp at hc
      · intro _
        refine ⟨rel, toString e.data.size ++ "\t" ++ toString (byteSum e.data), hne, hplain, ?_⟩
        simp only [Outcome.line]
        rw [hjoin]
        unfold joinPath
        simp only [String.append_assoc]
    · constructor
      · intro ch hch hc
        simp only [Outcome.line, String.toList_append, List.mem_append] at hch
        rcases hch with h | h
        · simp at h; rcases h with h | h | h | h | h | h | h <;> subst h <;> (revert hc; decide)
        · rw [escapeName_noSpecial _ ch h] at hc; simp at hc
      · intro h
        simp [Outcome.line] at h
  · constructor
    · intro ch hch hc
      simp only [Outcome.line, String.toList_append, List.mem_append] at hch
      rcases hch with ((h | h) | h) | h
      · simp at h; rcases h with h | h | h | h | h <;> subst h <;> (revert hc; decide)
      · rw [escapeName_noSpecial _ ch h] at hc; simp at hc
      · simpa using h
      · rw [toString_noSpecial _ ch h] at hc; simp at hc
    · intro h
      simp [Outcome.line] at h

/-- What `tar-pilot manifest <file> <dest>` prints, exactly: the line
    for each entry is `Spec.line`, which `Spec/Defs.lean` writes out from
    the rules. -/
theorem manifest_lines_eq (dest : String) (entries : List RawEntry) :
    (manifest (destComponents dest) entries).map Outcome.line =
      entries.map fun e => Spec.line dest e.name e.typeflag e.data := by
  unfold manifest
  rw [List.map_map]
  congr 1
  funext e
  simp only [Function.comp_apply]
  unfold outcome Spec.line
  have hreg : isRegular e = regularType e.typeflag e.name := rfl
  rw [hreg, gate_eq]
  split
  · split
    · rename_i rel hc
      have hne : rel ≠ [] := (gate_plain e.name rel (by rw [gate_eq]; exact hc)).1
      simp only [Outcome.line]
      rw [joinPath_dest dest rel hne, byteSum_eq, hc]
      rfl
    · rename_i hc
      simp only [Outcome.line, escapeName_eq, hc]
  · simp only [Outcome.line, escapeName_eq]

/-- Extracting an archive read from bytes is parsing it, then
    `extractAll`. -/
theorem extractArchive_eq (dest : List String) (data : ByteArray) :
    extractArchive dest data = (parseArchive data).map (extractAll dest) := rfl

end TarPilot
