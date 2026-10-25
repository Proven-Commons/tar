/-
  Path safety for tar entry names.

  A tar entry name is untrusted input. Before an entry may be extracted,
  its name goes through `gate`, which gives a non-empty list of plain
  names: no component is empty, `.` or `..`, or holds `/` or a special
  character (a control character or a Unicode line or paragraph
  separator).
  Extraction puts those components after a destination, so every
  extracted path stays under the destination. The proofs are in
  `Proofs/Contain.lean`.
-/

namespace TarPilot

/-- The parts of a path string between `/`. Used for entry names and for
    the destination the command-line tool is given. -/
def splitPath (s : String) : List String :=
  (s.split '/').toList.map (·.copy)

/-- A special character: a control character (C0 below space, DEL, or
    C1), or the Unicode line separator U+2028 or paragraph separator
    U+2029. Any of these could make a printed name read as a line break. -/
def isSpecialChar (c : Char) : Bool :=
  c.toNat < 32 || (127 ≤ c.toNat && c.toNat < 160) || c.toNat == 0x2028 || c.toNat == 0x2029

/-- Split a tar entry name into path components. -/
def components (name : String) : List String :=
  splitPath name

/-- Drop empty and `.` components. Fail if any component is `..`, or
    holds `/` or a special character. Components from `splitPath` hold
    no `/`; that check makes the proof direct. A special character, such
    as a line break, could make a printed name read as a different line,
    so a name holding one is never extracted. -/
def cleanComponents : List String → Option (List String)
  | [] => some []
  | c :: cs =>
    if c = ".." ∨ '/' ∈ c.toList ∨ c.toList.any isSpecialChar then none
    else (cleanComponents cs).map (fun rest =>
      if c = "" ∨ c = "." then rest else c :: rest)

/-- The gate every entry name must pass before extraction.
    Absolute names are rejected. `..` and special characters are
    rejected. Empty and `.` components are dropped. A name with nothing
    left is rejected. -/
def gate (name : String) : Option (List String) :=
  if name.toList.head? = some '/' then none
  else match cleanComponents (components name) with
    | some (r :: rs) => some (r :: rs)
    | _ => none

end TarPilot
