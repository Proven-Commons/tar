/-
  Whole-archive parsing, extraction, and writing.

  The extraction rule is the proved part, together with the path gate
  in `Path.lean`: the CLI and `extractAll` both call `extractEntry`.
  Each emitted path is `dest ++ rel`, where `rel` is a nonempty list
  of plain names. The containment theorems also cover joining the
  components into a string and resolving that relative path lexically.

  Parsing and writing are covered by differential tests against
  Python's `tarfile` module (see `tests/`), not by a proof.
-/

import TarPilot.Path
import TarPilot.Header

namespace TarPilot

/-- One archive entry as parsed: a name, a typeflag, and its data. -/
structure RawEntry where
  name : String
  typeflag : Char
  data : ByteArray

/-- Blocks of the archive, read from offset `off`. `fuel` counts down
    the blocks that can remain, which keeps the function total on
    hostile input: a size field that points past the end, or a block
    count that never reaches a full zero block, gives `none`. An
    archive that ends without its zero blocks is truncated, and a
    truncated archive is rejected whole, not read as a clean prefix. -/
def parseBlocks (data : ByteArray) (off : Nat) : Nat → Option (List RawEntry)
  | 0 => none
  | fuel + 1 =>
    if off + 512 > data.size then none
    else
      let block := data.extract off (off + 512)
      if block.toList.all (· = 0) then some []
      else match parseBlock block with
        | none => none
        | some h =>
          let dataOff := off + 512
          let padded := ((h.size + 511) / 512) * 512
          if dataOff + h.size > data.size then none
          else match parseBlocks data (dataOff + padded) fuel with
            | none => none
            | some rest =>
              some ({ name := h.name, typeflag := h.typeflag,
                      data := data.extract dataOff (dataOff + h.size) } :: rest)

/-- Parse a whole archive. -/
def parseArchive (data : ByteArray) : Option (List RawEntry) :=
  parseBlocks data 0 (data.size / 512 + 1)

/-- Regular files only: typeflag `0` or NUL. Directories, links, and
    everything else are never extracted, so a link entry cannot be used
    to place a later entry outside the destination. -/
def isRegular (e : RawEntry) : Bool :=
  e.typeflag == '0' || e.typeflag == Char.ofNat 0

/-- The extraction decision shared by the CLI and the in-memory model. -/
def extractEntry (dest : List String) (e : RawEntry) : Option (List String × ByteArray) :=
  if isRegular e then
    (gate e.name).map fun rel => (dest ++ rel, e.data)
  else none

/-- An accepted entry extends the destination by nonempty plain names. -/
theorem extractEntry_contained (dest : List String) (e : RawEntry)
    (path : List String) (bytes : ByteArray)
    (h : extractEntry dest e = some (path, bytes)) :
    ∃ rel, rel ≠ [] ∧ path = dest ++ rel ∧ ∀ c ∈ rel, PlainName c := by
  unfold extractEntry at h
  split at h
  · cases hg : gate e.name with
    | none => simp [hg] at h
    | some rel =>
      simp only [hg, Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
      obtain ⟨hp, hne⟩ := gate_plain e.name rel hg
      exact ⟨rel, hne, h.1.symm, hp⟩
  · simp at h

/-- Extract entries into a list of `(path, data)` pairs, in memory.
    The path of each pair is the destination components followed by the
    gated relative components of the entry name. -/
def extractAll (dest : List String) (entries : List RawEntry) :
    List (List String × ByteArray) :=
  entries.filterMap (extractEntry dest)

/-- Every emitted relative path is nonempty and contains only plain names,
    including the absence of embedded separators and NUL. -/
theorem extractAll_contained (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray)
    (h : (path, bytes) ∈ extractAll dest entries) :
    ∃ rel, rel ≠ [] ∧ path = dest ++ rel ∧ ∀ c ∈ rel, PlainName c := by
  obtain ⟨e, _, he⟩ := List.mem_filterMap.mp h
  exact extractEntry_contained dest e path bytes he

/-- Every path `extractAll` emits is the destination followed by a
    gated relative path: no `..`, no empty component, no `.`, and the
    relative path is not empty. This is the original component-list
    guarantee; see `extractAll_resolves_inside` for the joined string. -/
theorem extractAll_safe : ∀ (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray),
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, path = dest ++ rel ∧
      ".." ∉ rel ∧ "" ∉ rel ∧ "." ∉ rel ∧ rel ≠ [] := by
  intro dest entries path bytes h
  obtain ⟨rel, hne, heq, hp⟩ := extractAll_contained dest entries path bytes h
  exact ⟨rel, heq, fun hm => (hp _ hm).2.2.1 rfl,
    fun hm => (hp _ hm).1 rfl, fun hm => (hp _ hm).2.1 rfl, hne⟩

/-- Rendering a path and splitting it again preserves the destination
    and plain relative names. Destination components must be slash-free. -/
theorem extractAll_joined (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray)
    (hdest : ∀ d ∈ dest, '/' ∉ d.toList)
    (h : (path, bytes) ∈ extractAll dest entries) :
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      pathComponents (joinPath path) = dest ++ rel := by
  obtain ⟨rel, hne, hpath, hplain⟩ := extractAll_contained dest entries path bytes h
  refine ⟨rel, hne, hplain, ?_⟩
  subst hpath
  apply pathComponents_join
  · intro s hs
    rcases List.mem_append.mp hs with hs | hs
    · exact hdest s hs
    · exact (hplain s hs).2.2.2.1
  · simp [hne]

/-- The rendered path resolves to the resolved destination followed by
    plain names. This is lexical containment of a relative POSIX path,
    without symlinks; it is not a theorem about filesystem writes. -/
theorem extractAll_resolves_inside (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray)
    (hdest : ∀ d ∈ dest, '/' ∉ d.toList)
    (h : (path, bytes) ∈ extractAll dest entries) :
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      resolve [] (pathComponents (joinPath path)) = resolve [] dest ++ rel := by
  obtain ⟨rel, hne, hplain, hjoin⟩ := extractAll_joined dest entries path bytes hdest h
  exact ⟨rel, hne, hplain, by rw [hjoin, resolve_append, resolve_plain rel _ hplain]⟩

/-- The same joined-string guarantee for the decision the CLI calls. -/
theorem extractEntry_resolves_inside (dest : List String) (e : RawEntry)
    (path : List String) (bytes : ByteArray)
    (hdest : ∀ d ∈ dest, '/' ∉ d.toList)
    (h : extractEntry dest e = some (path, bytes)) :
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      resolve [] (pathComponents (joinPath path)) = resolve [] dest ++ rel := by
  apply extractAll_resolves_inside dest [e] path bytes hdest
  exact List.mem_filterMap.mpr ⟨e, by simp, h⟩

/-- Parse, then extract. -/
def extractArchive (dest : List String) (data : ByteArray) :
    Option (List (List String × ByteArray)) :=
  (parseArchive data).map (extractAll dest)

/-- The same guarantee for a whole archive read from bytes. -/
theorem extractArchive_safe : ∀ (dest : List String) (data : ByteArray)
    (out : List (List String × ByteArray)) (path : List String)
    (bytes : ByteArray),
    extractArchive dest data = some out → (path, bytes) ∈ out →
    ∃ rel, path = dest ++ rel ∧
      ".." ∉ rel ∧ "" ∉ rel ∧ "." ∉ rel ∧ rel ≠ [] := by
  intro dest data out path bytes h hmem
  unfold extractArchive at h
  cases hp : parseArchive data with
  | none =>
    rw [hp] at h
    simp at h
  | some entries =>
    rw [hp] at h
    simp only [Option.map_some, Option.some.injEq] at h
    subst h
    exact extractAll_safe dest entries path bytes hmem

/-- Build an archive from `(name, data)` pairs as regular files.
    Ends with two zero blocks, as the format expects. -/
def buildArchive (files : List (String × ByteArray)) : Option ByteArray :=
  let step := fun (acc : ByteArray) (f : String × ByteArray) => do
    let block ← buildBlock f.1 f.2.size '0'
    let padLen := ((f.2.size + 511) / 512) * 512 - f.2.size
    pure (acc ++ block ++ f.2 ++ ByteArray.mk (List.replicate padLen 0).toArray)
  (files.foldlM step ByteArray.empty).map
    (· ++ ByteArray.mk (List.replicate 1024 0).toArray)

end TarPilot
