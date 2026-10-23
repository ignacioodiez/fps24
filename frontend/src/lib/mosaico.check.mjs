// Self-check del mosaico de /especiales: de 1 a 30 películas, sin huecos en 2, 3 y 4 columnas y la 1ª grande.
// Uso: docker compose exec web node src/lib/mosaico.check.mjs
import assert from "node:assert/strict";
import { disposicion, huecos } from "./mosaico.js";

assert.equal(huecos(["grande", "normal"], 4), 3);
for (let n = 1; n <= 30; n++) {
  for (const cols of [2, 3, 4]) {
    const d = disposicion(n, cols);
    assert.equal(d.length, n);
    assert.equal(huecos(d, cols), 0, `${n} películas en ${cols} columnas: ${d}`);
    assert.ok(["grande", "completa"].includes(d[0]), `${n}/${cols}: la 1ª no es grande`);
  }
}
console.log("OK: mosaico sin huecos de 1 a 30 en 2, 3 y 4 columnas");
