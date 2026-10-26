/-
  The specification as Lean statements: the challenge file.

  A reviewer who did not write this file approves it, together with
  `Spec/Defs.lean` and the other files `bar.toml` lists, and `bar.toml`
  records the hash they had then. The proofs live in `Proofs/`, under the
  same names; `lake comparator` checks that each one proves exactly the
  statement written here. The `sorry` below is expected in this file
  only.

  The statements are about the code in `TarPilot/`: the gate, the
  extraction rule, the manifest, and the lines the command-line tool
  prints. They do not cover how bytes are parsed into entries; the
  differential tests do.
-/

import TarPilot
import Spec.Defs

open Spec

namespace TarPilot

/-- The gate is exactly its rules (`Spec.cleanName`). -/
theorem gate_eq (name : String) : gate name = Spec.cleanName name := sorry

/-- The gate gives a non-empty list of plain names. -/
theorem gate_plain (name : String) (rel : List String) :
    gate name = some rel → rel ≠ [] ∧ ∀ c ∈ rel, PlainName c := sorry

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
      else .skip e.name e.typeflag := sorry

/-- Every path `extractAll` emits is the destination followed by a
    non-empty list of plain names. -/
theorem extractAll_contained (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray) :
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, rel ≠ [] ∧ path = dest ++ rel ∧ ∀ c ∈ rel, PlainName c := sorry

/-- Joined with `/`, an emitted path splits back into exactly the
    destination components and the plain names, when no destination
    component holds `/`. -/
theorem extractAll_joined (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray) :
    (∀ d ∈ dest, '/' ∉ d.toList) →
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      pathComponents (joinPath path) = dest ++ rel := sorry

/-- Resolved lexically, an emitted path is the resolved destination
    followed by the plain names: no `..` in an archive reaches above the
    destination. (`Spec.resolve` reads a relative path; for an absolute
    destination, read both sides from the root.) -/
theorem extractAll_resolves_inside (dest : List String) (entries : List RawEntry)
    (path : List String) (bytes : ByteArray) :
    (∀ d ∈ dest, '/' ∉ d.toList) →
    (path, bytes) ∈ extractAll dest entries →
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      resolve [] (pathComponents (joinPath path)) = resolve [] dest ++ rel := sorry

/-- The same for an archive read from bytes. -/
theorem extractArchive_resolves_inside (dest : List String) (data : ByteArray)
    (out : List (List String × ByteArray)) (path : List String) (bytes : ByteArray) :
    (∀ d ∈ dest, '/' ∉ d.toList) →
    extractArchive dest data = some out → (path, bytes) ∈ out →
    ∃ rel, rel ≠ [] ∧ (∀ c ∈ rel, PlainName c) ∧
      resolve [] (pathComponents (joinPath path)) = resolve [] dest ++ rel := sorry

/-- The entries the manifest extracts are exactly the output of
    `extractAll`, in the same order. -/
theorem manifest_extracted (dest : List String) (entries : List RawEntry) :
    (manifest dest entries).filterMap Outcome.extracted = extractAll dest entries := sorry

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
        o.line = "OK\t" ++ under dest (String.intercalate "/" rel) ++ "\t" ++ rest) := sorry

/-- What `tar-pilot manifest <file> <dest>` prints, exactly: the line
    for each entry is `Spec.line`, which `Spec/Defs.lean` writes out from
    the rules. -/
theorem manifest_lines_eq (dest : String) (entries : List RawEntry) :
    (manifest (destComponents dest) entries).map Outcome.line =
      entries.map fun e => Spec.line dest e.name e.typeflag e.data := sorry

/-- Extracting an archive read from bytes is parsing it, then
    `extractAll`. -/
theorem extractArchive_eq (dest : List String) (data : ByteArray) :
    extractArchive dest data = (parseArchive data).map (extractAll dest) := sorry

end TarPilot
