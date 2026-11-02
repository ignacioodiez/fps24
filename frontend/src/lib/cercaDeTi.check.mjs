// Self-check de "pases cerca de ti". Uso: docker compose exec web node src/lib/cercaDeTi.check.mjs
import assert from "node:assert/strict";
import {
  ahoraMadrid, buscarCerca, centroZona, cinesConPronto, distanciaKm, enVentana, finVentana, minutosAndando,
  pasesCerca, textoDistancia,
} from "./cercaDeTi.js";

const eje = (texto) => Date.parse(`${texto}Z`);  // "AAAA-MM-DDTHH:MM" de Madrid en el eje de la API

// Distancia: Sol -> Callao ~ 0,5 km; el mismo punto, 0
const sol = { lat: 40.4169, lng: -3.7035 }, callao = { lat: 40.4203, lng: -3.7058 };
assert.ok(Math.abs(distanciaKm(sol, callao) - 0.42) < 0.05);
assert.equal(distanciaKm(sol, sol), 0);
assert.equal(textoDistancia(0.648), "650 m");
assert.equal(textoDistancia(0.001), "10 m");
assert.equal(textoDistancia(1.24), "1,2 km");
assert.equal(minutosAndando(0.65), 11);

// "Ahora" en Madrid aunque el instante se dé en UTC: 2 nov 2026 (invierno, UTC+1) y 2 jul (verano, UTC+2)
assert.equal(ahoraMadrid(new Date("2026-11-02T19:30:00Z")), eje("2026-11-02T20:30"));
assert.equal(ahoraMadrid(new Date("2026-07-02T22:30:00Z")), eje("2026-07-03T00:30"));

// Ventanas; "noche" llega a las 6:00 del día siguiente, o del mismo si ya es de madrugada
const ahora = eje("2026-11-02T23:40");
assert.equal(finVentana(ahora, "1h"), eje("2026-11-03T00:40"));
assert.equal(finVentana(ahora, "2h"), eje("2026-11-03T01:40"));
assert.equal(finVentana(ahora, "noche"), eje("2026-11-03T06:00"));
assert.equal(finVentana(eje("2026-11-03T01:15"), "noche"), eje("2026-11-03T06:00"));

// Madrugada: a las 23:40 una sesión de las 00:30 (fecha del día siguiente) está en la próxima hora; la de las
// 23:00 ya pasó
const pases = [
  { id: 1, fecha_hora: "2026-11-02T23:00:00", cine_slug: "a" },
  { id: 2, fecha_hora: "2026-11-03T00:30:00", cine_slug: "b" },
  { id: 3, fecha_hora: "2026-11-03T00:30:00", cine_slug: "a" },
  { id: 4, fecha_hora: "2026-11-03T02:00:00", cine_slug: "a" },
  { id: 5, fecha_hora: "2026-11-03T04:00:00", cine_slug: "lejos" },
  { id: 6, fecha_hora: "2026-11-03T18:00:00", cine_slug: "a" },
];
assert.deepEqual(enVentana(pases, ahora, "1h").map((x) => [x.pase.id, x.minutos]), [[2, 50], [3, 50]]);
assert.deepEqual(enVentana(pases, ahora, "noche").map((x) => x.pase.id), [2, 3, 4, 5]);
assert.deepEqual([...cinesConPronto(pases, ahora)].sort(), ["a", "b"]);

// Orden por hora y, a igualdad, por distancia; radio y máximo
const cines = new Map([
  ["a", { slug: "a", ...sol }],
  ["b", { slug: "b", ...callao }],
  ["lejos", { slug: "lejos", lat: 40.45, lng: -3.70 }],  // ~3,7 km
]);
const cerca = (filtro, max) => pasesCerca(pases, cines, sol, ahora, filtro, max).map((x) => x.pase.id);
assert.deepEqual(cerca({ radioKm: 1, ventana: "1h" }), [3, 2]);
assert.deepEqual(cerca({ radioKm: 0.1, ventana: "1h" }), [3]);
assert.deepEqual(cerca({ radioKm: 1, ventana: "noche" }, 2), [3, 2]);
assert.deepEqual(cerca({ radioKm: 5, ventana: "noche" }), [3, 2, 4, 5]);

// Ampliación automática a 2 km y 2 h, solo si no hay nada
assert.equal(buscarCerca(pases, cines, sol, ahora, { radioKm: 1, ventana: "1h" }).ampliado, null);
const tarde = eje("2026-11-03T00:45");  // ya no hay nada en la próxima hora, sí a las 02:00
const r = buscarCerca(pases, cines, sol, tarde, { radioKm: 0.5, ventana: "1h" });
assert.deepEqual(r.ampliado, { radioKm: 2, ventana: "2h" });
assert.deepEqual(r.items.map((x) => x.pase.id), [4]);
// Ya en 2 km y 2 h: no hay a qué ampliar
assert.deepEqual(buscarCerca(pases, cines, sol, eje("2026-11-03T06:00"), { radioKm: 2, ventana: "2h" }), { items: [], ampliado: null });
// "Esta noche" no se recorta a 2 h al ampliar
assert.deepEqual(buscarCerca([], cines, sol, ahora, { radioKm: 1, ventana: "noche" }).ampliado, { radioKm: 2, ventana: "noche" });

// Centro de una zona
assert.deepEqual(centroZona([{ zona: "Centro", lat: 1, lng: 3 }, { zona: "Centro", lat: 3, lng: 5 }, { zona: "Otra", lat: 9, lng: 9 }], "Centro"), { lat: 2, lng: 4 });
assert.equal(centroZona([{ zona: "Centro", lat: null, lng: null }], "Centro"), null);

console.log("OK: cercaDeTi.check");
