/-
  Whole-archive parsing, extraction, and writing.

  The extraction rule is the proved part, together with the path gate
  in `Path.lean`: `extractAll` only emits a path built as `dest ++ rel`,
  where `rel` passed the gate. `manifest` is what `tar-pilot manifest`
  prints, and its extracted entries are exactly the output of
  `extractAll`. The proofs are in `Proofs/Contain.lean`.

  Parsing, where an archive ends included, and writing are covered by
  differential tests against Python's `tarfile` module and a model of
  the format (see `tests/`), not by a proof.
-/

import TarPilot.Path
import TarPilot.Header

namespace TarPilot

/-- One archive entry as parsed: a name, a typeflag, and its data. -/
structure RawEntry where
  name : String
  typeflag : Char
  data : ByteArray

/-- Whether every byte of `data` from offset `off` to its end is zero. -/
def zerosFrom (data : ByteArray) (off : Nat) : Bool :=
  (data.extract off data.size).toList.all (· = 0)

/-- Blocks of the archive, read from offset `off`. `fuel` counts down
    the blocks that can remain, which keeps the function total on
    hostile input: a size field that points past the end, or a block
    count that never reaches a full zero block, gives `none`. An
    archive that ends without its zero blocks is truncated, and a
    truncated archive is rejected whole, not read as a clean prefix.

    Where a header is due, a block of zeros ends the archive. It must be
    followed by at least one more block of zeros, and nothing but zero
    bytes may follow it to the end of the input. A lone zero block, or
    anything that is not zero after the end, makes the whole archive
    fail to parse: GNU tar's `--ignore-zeros` and Python's `tarfile`
    with `ignore_zeros=True` read on past zero blocks, so entries after
    them, as in two archives joined with `cat`, would be extracted by
    those readers and never seen here. -/
def parseBlocks (data : ByteArray) (off : Nat) : Nat → Option (List RawEntry)
  | 0 => none
  | fuel + 1 =>
    if off + 512 > data.size then none
    else
      let block := data.extract off (off + 512)
      if block.toList.all (· = 0) then
        if off + 1024 ≤ data.size ∧ zerosFrom data off then some [] else none
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

/-- Parse a whole archive. Its length must be a whole number of 512-byte
    blocks, and it must end as `parseBlocks` says: at least two blocks
    of zeros, then only zero bytes. -/
def parseArchive (data : ByteArray) : Option (List RawEntry) :=
  if data.size % 512 ≠ 0 then none
  else parseBlocks data 0 (data.size / 512 + 1)

/-- Regular files only: typeflag `0`, NUL, or `7` (a contiguous file,
    which POSIX lets a reader treat as regular, as Python's `tarfile`
    does), and a name that does not end in `/`. Older archives mark a
    directory with that `/`, and GNU tar reads any entry named so as a
    directory. Directories, links, and everything else are never
    extracted, so a link entry cannot be used to place a later entry
    outside the destination. -/
def isRegular (e : RawEntry) : Bool :=
  (e.typeflag == '0' || e.typeflag == Char.ofNat 0 || e.typeflag == '7') &&
    e.name.toList.getLast? != some '/'

/-- Extract entries into a list of `(path, data)` pairs, in memory.
    The path of each pair is the destination components followed by the
    gated relative components of the entry name. -/
def extractAll (dest : List String) (entries : List RawEntry) :
    List (List String × ByteArray) :=
  entries.filterMap fun e =>
    if isRegular e then
      (gate e.name).map fun rel => (dest ++ rel, e.data)
    else none

/-- Parse, then extract. -/
def extractArchive (dest : List String) (data : ByteArray) :
    Option (List (List String × ByteArray)) :=
  (parseArchive data).map (extractAll dest)

/-- What extraction does with one entry. -/
inductive Outcome where
  /-- A regular file, written at this path. -/
  | extract (path : List String) (data : ByteArray)
  /-- A regular file whose name fails the gate. -/
  | reject (name : String)
  /-- An entry that is not a regular file. -/
  | skip (name : String) (typeflag : Char)

/-- The outcome for one entry, under the destination `dest`. -/
def outcome (dest : List String) (e : RawEntry) : Outcome :=
  if isRegular e then
    match gate e.name with
    | some rel => .extract (dest ++ rel) e.data
    | none => .reject e.name
  else .skip e.name e.typeflag

/-- The path and data of an extracted entry. -/
def Outcome.extracted : Outcome → Option (List String × ByteArray)
  | .extract path data => some (path, data)
  | _ => none

/-- The outcome for every entry, in archive order: what
    `tar-pilot manifest` prints. -/
def manifest (dest : List String) (entries : List RawEntry) : List Outcome :=
  entries.map (outcome dest)

/-- The components of the destination the command-line tool is given.
    An empty destination means the current directory. A final `/` adds
    no empty component, so the path under `out/` is `out/a`, not
    `out//a`. -/
def destComponents (dest : String) : List String :=
  if dest = "" then []
  else if dest.toList.getLast? = some '/' then (splitPath dest).dropLast
  else splitPath dest

/-- A path as one string, its components joined with `/`. -/
def joinPath (path : List String) : String :=
  String.intercalate "/" path

/-- The sum of the bytes, printed as a check on the data. -/
def byteSum (b : ByteArray) : Nat :=
  b.toList.foldl (fun a x => a + x.toNat) 0

/-- One character of a printed name: a backslash as `\\`, a control
    character as `\x` and two hex digits, the line and paragraph
    separators as `\u2028` and `\u2029`, any other as itself. -/
def escapeChar (c : Char) : List Char :=
  if c = '\\' then ['\\', '\\']
  else if c.toNat == 0x2028 then "\\u2028".toList
  else if c.toNat == 0x2029 then "\\u2029".toList
  else if isSpecialChar c then
    let hex := "0123456789abcdef".toList
    ['\\', 'x', hex.getD (c.toNat / 16) '0', hex.getD (c.toNat % 16) '0']
  else [c]

/-- A name as the tool prints it, with no special character left, so it
    cannot break a line or a field. -/
def escapeName (s : String) : String :=
  String.ofList (s.toList.flatMap escapeChar)

/-- The line `tar-pilot manifest` prints for one outcome. -/
def Outcome.line : Outcome → String
  | .extract path data =>
    "OK\t" ++ joinPath path ++ "\t" ++ toString data.size ++ "\t" ++ toString (byteSum data)
  | .reject name => "REJECT\t" ++ escapeName name
  | .skip name typeflag => "SKIP\t" ++ escapeName name ++ "\t" ++ toString typeflag.toNat

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
