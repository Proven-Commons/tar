import TarPilot

open TarPilot

-- UTF-8 decoding distinguishes an empty field from an invalid field.
#guard bytesToName [] == some ""
#guard bytesToName [195, 169, 0] == some "é"
#guard bytesToName [255] == none
#guard bytesToName [195] == none
#guard bytesToName [0, 255] == some ""

-- The writer must not create a header the supported-subset reader rejects.
#guard (buildBlock "safe.txt" 7 '7').isSome
#guard (buildBlock "link" 0 '2').isSome
#guard (buildBlock "link" 7 '2').isNone
#guard (buildBlock "extension" 0 'x').isNone
#guard (buildBlock ("safe" ++ String.singleton (Char.ofNat 0) ++ "hidden") 0 '0').isNone
#guard (buildBlock "legacy/" 0 (Char.ofNat 0)).isNone
