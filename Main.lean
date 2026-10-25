/-
  Command line front end for the tar pilot.

    tar-pilot list <file.tar>
      Print one line per entry: name (escaped as in `manifest`), data
      size, typeflag code.

    tar-pilot manifest <file.tar> <dest>
      Print what extraction would do, in archive order, without
      writing anything to disk. Each line is `o.line` for an outcome `o`
      of the proved `manifest` of the parsed archive, in order
      (`Proofs/Contain.lean`, `manifest_lines`). Names in REJECT and
      SKIP lines are escaped: a backslash as two, a control character
      as `\x` and two hex digits, U+2028 and U+2029 as `\u2028` and
      `\u2029`. A destination with a special character, or with U+FFFD
      (which the runtime puts for bytes that are not UTF-8), is
      refused:
        OK     <dest path> <size> <byte sum>   for an extracted file
        REJECT <name>                          for a regular file whose
                                               name fails the path gate
        SKIP   <name> <typeflag code>         for a non-regular entry

    tar-pilot create <out.tar> <file> [more files...]
      Build an archive. Each entry name is the path as given.
-/

import TarPilot

open TarPilot

def runList (file : String) : IO UInt32 := do
  let data ← IO.FS.readBinFile file
  match parseArchive data with
  | none =>
    IO.eprintln s!"error: cannot parse {file} as a ustar archive"
    return 1
  | some entries =>
    for e in entries do
      IO.println s!"{escapeName e.name}\t{e.data.size}\t{e.typeflag.toNat}"
    return 0

def runManifest (file dest : String) : IO UInt32 := do
  if dest.toList.any isSpecialChar then
    IO.eprintln "error: the destination holds a control character or a line separator"
    return 2
  if dest.toList.contains '\uFFFD' then
    IO.eprintln "error: the destination is not valid UTF-8, or holds U+FFFD"
    return 2
  let data ← IO.FS.readBinFile file
  match parseArchive data with
  | none =>
    IO.eprintln s!"error: cannot parse {file} as a ustar archive"
    return 1
  | some entries =>
    for o in manifest (destComponents dest) entries do
      IO.println o.line
    return 0

def runCreate (out : String) (files : List String) : IO UInt32 := do
  let mut pairs : List (String × ByteArray) := []
  for f in files do
    let data ← IO.FS.readBinFile f
    pairs := pairs ++ [(f, data)]
  match buildArchive pairs with
  | none =>
    IO.eprintln "error: a name does not fit the ustar name and prefix fields"
    return 1
  | some bytes =>
    IO.FS.writeBinFile out bytes
    return 0

def usage : IO UInt32 := do
  IO.eprintln "usage: tar-pilot list <file.tar>"
  IO.eprintln "       tar-pilot manifest <file.tar> <dest>"
  IO.eprintln "       tar-pilot create <out.tar> <file> [more files...]"
  return 2

def main (args : List String) : IO UInt32 := do
  match args with
  | ["list", file] => runList file
  | ["manifest", file, dest] => runManifest file dest
  | "create" :: out :: files =>
    if files.isEmpty then usage else runCreate out files
  | _ => usage
