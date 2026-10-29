// Self-check del formato del nombre (mismos casos que check_perfil.py). Uso: docker compose exec web node src/lib/usuario.check.mjs
import assert from "node:assert/strict";
import { motivoFormato } from "./usuario.js";

for (const valido of ["ana", "ana.diez", "a_b.c", "cine_fan", "x".repeat(20), "007", "Nacho", "Ana.Diez", "CINE_fan", "  Ana.Diez "]) {
  assert.equal(motivoFormato(valido), null, valido);
}
for (const [invalido, motivo] of [["ab", "entre 3 y 20"], ["x".repeat(21), "entre 3 y 20"], ["", "entre 3 y 20"], [null, "entre 3 y 20"],
  ["ana diez", "letras sin tildes"], ["añil", "letras sin tildes"], ["ana-diez", "letras sin tildes"], ["ana@x", "letras sin tildes"],
  [".ana", "empezar"], ["ana.", "empezar"], ["_ana", "empezar"], ["ana_", "empezar"], ["an..a", "dos puntos"]]) {
  assert.match(motivoFormato(invalido) ?? "", new RegExp(motivo), String(invalido));
}
console.log("OK: usuario.check");
