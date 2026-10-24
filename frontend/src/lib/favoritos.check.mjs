// Self-check del orden por favoritos. Uso: docker compose exec web node src/lib/favoritos.check.mjs
import assert from "node:assert/strict";
import { favoritosPrimero, sesionSugerida } from "./favoritos.js";

const slug = (x) => x.s;
const lista = [{ s: "a", i: 0 }, { s: "b", i: 1 }, { s: "c", i: 2 }, { s: "b", i: 3 }, { s: "d", i: 4 }];
assert.deepEqual(favoritosPrimero(lista, slug, new Set()).map((x) => x.i), [0, 1, 2, 3, 4]);
assert.deepEqual(favoritosPrimero(lista, slug, new Set(["b", "d"])).map((x) => x.i), [1, 3, 4, 0, 2]); // estable
assert.deepEqual(favoritosPrimero(lista, slug, new Set(["zz"])).map((x) => x.i), [0, 1, 2, 3, 4]);

const sesion = { cine_slug: "a" }, alt = [{ cine_slug: "b" }, { cine_slug: "c" }];
assert.equal(sesionSugerida(sesion, alt, new Set()), sesion);
assert.equal(sesionSugerida(sesion, alt, new Set(["a", "c"])), sesion); // la de siempre ya es de un favorito
assert.equal(sesionSugerida(sesion, alt, new Set(["c", "b"])), alt[0]); // la primera (por hora) de un favorito
assert.equal(sesionSugerida(sesion, undefined, new Set(["c"])), sesion);
console.log("OK: favoritos.check");
