// Self-check de las fechas del selector de días (hoy/mañana en Madrid, 4 semanas, rótulo del mes, cambio de hora).
// Uso: docker compose exec web node src/lib/fechasMadrid.check.mjs
import assert from "node:assert/strict";
import { hoyMadrid, sumarDias, etiquetaRelativa, cuatroSemanas, rotuloMes, diaCompleto, comoUTC } from "./fechasMadrid.js";

// Hoy en Madrid, no en UTC ni en el huso del equipo
assert.equal(hoyMadrid(new Date("2026-10-27T22:30Z")), "2026-10-27"); // 23:30 en Madrid (CET)
assert.equal(hoyMadrid(new Date("2026-10-27T23:30Z")), "2026-10-28"); // 00:30
assert.equal(hoyMadrid(new Date("2026-07-15T22:30Z")), "2026-07-16"); // verano (CEST): 00:30
// Cambio de hora de octubre (domingo 25-10-2026 a las 3:00 vuelve a las 2:00)
assert.equal(hoyMadrid(new Date("2026-10-24T22:30Z")), "2026-10-25"); // 00:30 CEST
assert.equal(hoyMadrid(new Date("2026-10-25T22:30Z")), "2026-10-25"); // 23:30 CET
assert.equal(hoyMadrid(new Date("2026-10-25T23:00Z")), "2026-10-26");
assert.equal(sumarDias("2026-10-25", 1), "2026-10-26");
assert.equal(sumarDias("2026-10-24", 2), "2026-10-26");
assert.equal(sumarDias("2026-03-28", 2), "2026-03-30"); // cambio de marzo
assert.equal(sumarDias("2026-12-31", 1), "2027-01-01");

assert.equal(etiquetaRelativa("2026-10-27", "2026-10-27"), "Hoy");
assert.equal(etiquetaRelativa("2026-10-28", "2026-10-27"), "Mañana");
assert.equal(etiquetaRelativa("2026-10-29", "2026-10-27"), null);
assert.equal(etiquetaRelativa("2026-11-01", "2026-10-31"), "Mañana");

// 4 semanas completas de lunes a domingo, incluido hoy, también cruzando el cambio de hora
for (const hoy of ["2026-10-27", "2026-10-25", "2026-10-19", "2026-12-30", "2026-03-29"]) {
  const dias = cuatroSemanas(hoy);
  assert.equal(dias.length, 28);
  assert.equal(new Set(dias).size, 28, `${hoy}: días repetidos`);
  assert.ok(dias.includes(hoy) && dias.indexOf(hoy) < 7, `${hoy}: no está en la 1ª semana`);
  dias.forEach((d, i) => assert.equal(comoUTC(d).getUTCDay(), (i + 1) % 7, `${hoy}: ${d} fuera de su columna`));
  dias.slice(1).forEach((d, i) => assert.equal(sumarDias(dias[i], 1), d));
}
assert.deepEqual([cuatroSemanas("2026-10-25")[0], cuatroSemanas("2026-10-25")[27]], ["2026-10-19", "2026-11-15"]);

assert.equal(rotuloMes("2026-10-27"), "Octubre 2026");
assert.equal(rotuloMes("2026-10-01", "2026-10-31"), "Octubre 2026");
assert.equal(rotuloMes("2026-10-29", "2026-11-04"), "Oct – Nov 2026");
assert.equal(rotuloMes("2026-12-29", "2027-01-04"), "Dic 2026 – Ene 2027");
assert.equal(rotuloMes("2026-09-28", "2026-10-02"), "Sept – Oct 2026"); // es-ES abrevia septiembre como "sept"

assert.equal(diaCompleto("2026-10-27"), "martes 27 de octubre");
assert.equal(diaCompleto("2026-11-01"), "domingo 1 de noviembre");

console.log("OK: hoy/mañana en Madrid, 4 semanas lunes-domingo, rótulo del mes y cambio de hora");
