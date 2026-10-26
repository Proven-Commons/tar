/-
  Axiom check for the headline theorems. Building this file prints the
  axioms each proof depends on. The expected output is only the three
  standard Lean axioms: `propext`, `Classical.choice`, `Quot.sound`,
  or a subset of them. Any other name here breaks the verified bar.
-/

import Proofs

#print axioms TarPilot.gate_eq
#print axioms TarPilot.gate_plain
#print axioms TarPilot.manifest_eq
#print axioms TarPilot.manifest_extracted
#print axioms TarPilot.manifest_lines
#print axioms TarPilot.manifest_lines_eq
#print axioms TarPilot.extractAll_contained
#print axioms TarPilot.extractAll_joined
#print axioms TarPilot.extractAll_resolves_inside
#print axioms TarPilot.extractArchive_eq
#print axioms TarPilot.extractArchive_resolves_inside
#print axioms Spec.escape_noSpecial
