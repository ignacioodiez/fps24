// Self-check de la agrupación de /cine-vose-madrid. Uso: docker compose exec web node src/lib/vose.check.mjs
import assert from "node:assert/strict";
import { agruparVose, cinesConMasVose } from "./vose.js";

const peliculas = [{ id: 1, titulo: "Beta" }, { id: 2, titulo: "Alfa" }];
const pase = (id, pelicula_id, cine, fecha_hora) => ({ id, pelicula_id, cine, cine_slug: cine.toLowerCase(), fecha_hora });
const pases = [
  pase(1, 1, "Verdi", "2026-11-04T20:00:00"),
  pase(2, 2, "Golem", "2026-11-03T22:00:00"),
  pase(3, 2, "Verdi", "2026-11-03T18:00:00"),
  pase(4, 1, "Golem", "2026-11-03T21:00:00"),
  pase(5, 2, "Golem", "2026-11-03T16:00:00"),
  pase(6, 99, "Golem", "2026-11-03T16:00:00"), // sin película: fuera
];

const dias = agruparVose({ peliculas, pases });
assert.deepEqual(dias.map((d) => [d.fecha, d.sesiones]), [["2026-11-03", 4], ["2026-11-04", 1]]);
// Alfa (3 sesiones) antes que Beta (1); sus cines por primera sesión: Golem 16:00, Verdi 18:00
const [alfa, beta] = dias[0].peliculas;
assert.equal(alfa.pelicula.titulo, "Alfa");
assert.equal(beta.pelicula.titulo, "Beta");
assert.deepEqual(alfa.cines.map(([c, ps]) => [c, ps.map((p) => p.id)]), [["Golem", [5, 2]], ["Verdi", [3]]]);
assert.equal(alfa.cines[0][1][0].pelicula.titulo, "Alfa"); // cada pase lleva su película (modal)

assert.deepEqual(cinesConMasVose(pases, 2).map((c) => [c.slug, c.sesiones]), [["golem", 4], ["verdi", 2]]);
assert.deepEqual(agruparVose({ peliculas: [], pases: [] }), []);

console.log("OK: vose (días, orden de películas y cines, cines con más VOSE)");
