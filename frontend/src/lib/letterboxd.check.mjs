// Self-check del usuario de Letterboxd (mismos casos que check_perfil.py). Uso: docker compose exec web node src/lib/letterboxd.check.mjs
import assert from "node:assert/strict";
import { leerLetterboxd } from "./letterboxd.js";

for (const [entrada, esperado] of [["Ana_Diez", "Ana_Diez"], ["  @cine_fan ", "cine_fan"], ["https://letterboxd.com/Ana_Diez/", "Ana_Diez"],
  ["letterboxd.com/ana", "ana"], ["http://www.letterboxd.com/ana/films/diary/", "ana"], ["HTTPS://LETTERBOXD.COM/ana?x=1", "ana"]]) {
  assert.deepEqual(leerLetterboxd(entrada), { usuario: esperado }, entrada);
}
assert.deepEqual(leerLetterboxd("   "), {});
for (const malo of ["a", "x".repeat(21), "ana diez", "ana.diez", "añil", "<script>", "https://letterboxd.com/film/dune/",
  "https://letterboxd.com/", "https://boxd.it/abc", "letterboxd.com.mal.es/ana"]) {
  assert.ok(leerLetterboxd(malo).motivo, malo);
}
console.log("OK: letterboxd.check");
