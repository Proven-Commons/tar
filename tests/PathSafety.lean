import TarPilot

open TarPilot

-- The old cleaner accepted a whole traversal path as one component.
#guard cleanComponents ["a/../../etc/passwd"] == none
#guard cleanComponents ["ok", "bad" ++ String.singleton (Char.ofNat 0)] == none
#guard gate "a/../../etc/passwd" == none
#guard gate "./a//b/./" == some ["a", "b"]
#guard gate "././" == none

-- The old statement holds of this component, yet its rendered path escapes.
example : ".." ∉ ["a/../../etc/passwd"] ∧ "" ∉ ["a/../../etc/passwd"] ∧
    "." ∉ ["a/../../etc/passwd"] := by decide
example : ¬ PlainName "a/../../etc/passwd" := by
  unfold PlainName
  decide
#guard resolve [] (pathComponents (joinPath ["out", "a/../../etc/passwd"])) ==
    ["etc", "passwd"]

-- The resolver must preserve leading parents and reduce internal parents.
#guard resolve [] ["..", "..", "out", ".", "", "nested", "..", "file"] ==
    ["..", "..", "out", "file"]
#guard pathComponents (joinPath ["out", "", "nested", "file"]) ==
    ["out", "", "nested", "file"]

-- Mixed outcomes must preserve the order and data of the accepted entries.
private def entry (name : String) (typeflag : Char := '0') : RawEntry :=
  { name, typeflag, data := ByteArray.mk #[65] }

#guard (extractAll ["out"] [entry "./a//b", entry "../evil", entry "link" '2',
    entry "./", entry "last" (Char.ofNat 0)]).map (fun p => (joinPath p.1, p.2.toList)) ==
    [("out/a/b", [65]), ("out/last", [65])]
