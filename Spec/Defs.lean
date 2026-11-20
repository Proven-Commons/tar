/-
  The definitions the statements in `Proofs/Contain.lean` use, written
  from the rules in `SPEC.md` and from POSIX.

  The statements are about these code definitions in `TarPilot/`, which
  a reviewer should read with them: `gate`, `manifest` and its
  `Outcome`s, `Outcome.line`, `destComponents`, `joinPath`,
  `extractAll`, and `extractArchive`; and `Main.lean`, which prints
  `o.line` for each outcome `o` of `manifest (destComponents dest)
  entries`. Where a statement says a code definition equals one of the
  definitions here, the one here is what to read.
-/

namespace Spec

/-- A special character: one the tool never prints raw. These are the
    control characters (C0 below space, DEL, and C1; tab, line feed and
    carriage return among them) and the Unicode line separator U+2028
    and paragraph separator U+2029, which some readers take as line
    breaks. -/
def isSpecial (c : Char) : Bool :=
  c.toNat < 0x20 || (0x7F ≤ c.toNat && c.toNat < 0xA0) || c.toNat == 0x2028 ||
    c.toNat == 0x2029

/-- A component that names one entry inside its directory: not empty,
    not `.` or `..`, and free of `/` and of special characters (NUL
    among them). -/
def PlainName (c : String) : Prop :=
  c ≠ "" ∧ c ≠ "." ∧ c ≠ ".." ∧ ∀ ch ∈ c.toList, ch ≠ '/' ∧ isSpecial ch = false

/-- The components a system sees in a path string: the parts between `/`.
    An absolute path starts with an empty part. -/
def pathComponents (s : String) : List String :=
  (s.split '/').toList.map (·.copy)

/-- The path gate, from its rules: an absolute name (one that starts with
    `/`) is rejected; a name with a `..` component, or with a special
    character, is rejected;
    empty and `.` components are dropped; and a name with nothing left
    is rejected. Otherwise the result is the components that are left. -/
def cleanName (name : String) : Option (List String) :=
  if name.toList.head? = some '/' then none
  else
    let parts := pathComponents name
    if parts.any (fun c => c == ".." || c.toList.any isSpecial) then none
    else
      let kept := parts.filter (fun c => !(c == "" || c == "."))
      if kept = [] then none else some kept

/-- Whether an entry with typeflag `t` and name `name` is a regular file:
    typeflag `0`, NUL from older archives, or `7`, a contiguous file,
    which POSIX lets a reader treat as regular; and a name that does not
    end in `/`, which older archives use for a directory. -/
def regularType (t : Char) (name : String) : Bool :=
  (t == '0' || t == Char.ofNat 0 || t == '7') && name.toList.getLast? != some '/'

/-- A relative path `rel` under the destination `dest`, as a string: `rel`
    alone when `dest` is empty, `dest` then `rel` when `dest` ends in `/`,
    and `dest`, `/`, `rel` otherwise. -/
def under (dest rel : String) : String :=
  if dest = "" then rel
  else if dest.toList.getLast? = some '/' then dest ++ rel
  else dest ++ "/" ++ rel

/-- A hex digit, `0` to `9` then `a` to `f`. -/
def hexDigit (n : Nat) : Char :=
  "0123456789abcdef".toList.getD n '0'

/-- How the tool prints one character of a name: a backslash as two;
    U+2028 and U+2029 as `\u2028` and `\u2029`; any other special
    character, all of which are below 0xA0, as `\x` and two hex digits;
    and any other character as itself. -/
def escapeChar (c : Char) : String :=
  if c = '\\' then "\\\\"
  else if c.toNat = 0x2028 then "\\u2028"
  else if c.toNat = 0x2029 then "\\u2029"
  else if isSpecial c then
    String.ofList ['\\', 'x', hexDigit (c.toNat / 16), hexDigit (c.toNat % 16)]
  else c.toString

/-- How the tool prints a name. -/
def escape (s : String) : String :=
  String.join (s.toList.map escapeChar)

/-- A hex digit is never special. -/
theorem hexDigit_noSpecial (n : Nat) : isSpecial (hexDigit n) = false := by
  have hex : ∀ i : Fin 16, isSpecial (hexDigit i.val) = false := by decide
  by_cases h : n < 16
  · exact hex ⟨n, h⟩
  · have : hexDigit n = '0' := by
      unfold hexDigit
      rw [List.getD_eq_getElem?_getD, List.getElem?_eq_none (by simp; omega)]
      rfl
    rw [this]; decide

/-- A printed character of a name is never special. -/
theorem escapeChar_noSpecial (c : Char) :
    ∀ ch ∈ (escapeChar c).toList, isSpecial ch = false := by
  intro ch hch
  unfold escapeChar at hch
  split at hch
  · simp at hch; subst hch; decide
  · split at hch
    · simp at hch; rcases hch with rfl | rfl | rfl | rfl | rfl | rfl <;> decide
    · split at hch
      · simp at hch; rcases hch with rfl | rfl | rfl | rfl | rfl | rfl <;> decide
      · split at hch
        · simp only [String.toList_ofList, List.mem_cons, List.mem_nil_iff, or_false] at hch
          rcases hch with rfl | rfl | rfl | rfl
          · decide
          · decide
          · exact hexDigit_noSpecial _
          · exact hexDigit_noSpecial _
        · rename_i _ _ _ hc
          simp at hch
          subst hch
          simpa using hc

/-- A printed name holds no special character, so it cannot break a line
    or a field of the tool's output. -/
theorem escape_noSpecial (s : String) :
    ∀ ch ∈ (escape s).toList, isSpecial ch = false := by
  intro ch hch
  unfold escape at hch
  rw [String.toList_join, List.mem_flatMap] at hch
  obtain ⟨t, ht, hc⟩ := hch
  obtain ⟨c, _, rfl⟩ := List.mem_map.mp ht
  exact escapeChar_noSpecial c ch hc

/-- The sum of the bytes of a file. -/
def byteSum (b : ByteArray) : Nat :=
  (b.toList.map UInt8.toNat).sum

/-- The line `tar-pilot manifest <file> <dest>` prints for an entry with
    name `name`, typeflag `t`, and data `data`, with fields separated by
    tabs: `OK`, the path, the size, and the byte sum, for a regular file
    whose name passes the gate; `REJECT` and the name, for a regular file
    whose name fails; `SKIP`, the name, and the typeflag as a decimal
    code, for anything else. -/
def line (dest : String) (name : String) (t : Char) (data : ByteArray) : String :=
  if regularType t name then
    match cleanName name with
    | some rel =>
      "OK\t" ++ under dest (String.intercalate "/" rel) ++ "\t" ++ toString data.size ++
        "\t" ++ toString (byteSum data)
    | none => "REJECT\t" ++ escape name
  else "SKIP\t" ++ escape name ++ "\t" ++ toString t.toNat

/-- Resolve the components of a relative path lexically, as POSIX does
    when no component is a symlink, after the components already
    resolved in `acc`: an empty part and `.` change nothing, `..` removes
    the last component (or is kept when there is none to remove, or the
    last is itself `..`), and any other part is appended. An absolute
    path's leading empty part changes nothing, so the root is dropped:
    read an absolute path's result from `/`. -/
def resolve : List String → List String → List String
  | acc, [] => acc
  | acc, c :: cs =>
    if c = "" ∨ c = "." then resolve acc cs
    else if c = ".." then
      if acc = [] ∨ acc.getLast? = some ".." then resolve (acc ++ [".."]) cs
      else resolve acc.dropLast cs
    else resolve (acc ++ [c]) cs

example : pathComponents "out/a//b/" = ["out", "a", "", "b", ""] := by
  simp only [pathComponents, String.toList_split_char]; decide

example : resolve [] (pathComponents "out/a/../../../etc/./passwd") =
    ["..", "etc", "passwd"] := by
  simp only [pathComponents, String.toList_split_char]; decide

example : cleanName "a/./b//c" = some ["a", "b", "c"] := by
  simp only [cleanName, pathComponents, String.toList_split_char]; decide

example : cleanName "a/../b" = none ∧ cleanName "/etc/passwd" = none ∧
    cleanName "./" = none ∧ cleanName "a\nb" = none ∧ cleanName "a\u2028b" = none := by
  simp only [cleanName, pathComponents, String.toList_split_char]; decide

example : under "out" "a/b" = "out/a/b" ∧ under "/" "a" = "/a" ∧ under "" "a" = "a" := by
  decide

example : escape "a\\b\tc\u2028d\u0085" = "a\\\\b\\x09c\\u2028d\\x85" := by
  decide

end Spec
