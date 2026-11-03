// Self-check del precio de hoy por cine (finde por cine, festivos, varios días del espectador).
// Uso: docker compose exec web node src/lib/tarifas.check.mjs
import assert from "node:assert/strict";
import { hoyMadrid } from "./fechasMadrid.js";
import { FESTIVOS, esDiaEspectador, precioDia, precioHoy, precioSesion } from "./tarifas.js";

// Copias de backend/app/services/cines.py (TARIFAS)
const RENOIR = { entrada_laboral: 8.5, entrada_finde: 9.8, finde_dias: ["Viernes", "Sábado", "Domingo"],
                 dia_espectador: { dias: ["Lunes", "Miércoles"], precio: 5.5 } };
const GOLEM = { entrada_laboral: 8.0, entrada_finde: 9.1, dia_espectador: { dias: ["Lunes", "Miércoles"], precio: 5.7 } };
const RIO = { entrada: 9.5, dia_espectador: [{ dias: ["Martes", "Jueves"], precio: 7.5 }, { dias: ["Miércoles"], precio: 5.9 }] };
const VERDI = { entrada: 8.5, dia_espectador: { dias: ["Lunes"], precio: 4.9 } };
const METROPOL = { precio_texto: "Según la película", notas: "Entre 3,50 y 7,50 € según la película" };

// Viernes en Renoir: finde; en un cine sin finde_dias (Golem): laborable; sábado en Golem: finde
assert.deepEqual(precioHoy(RENOIR, "2026-11-06"), { precio: 9.8, tipo: "finde" });
assert.deepEqual(precioHoy(RENOIR, "2026-11-05"), { precio: 8.5, tipo: "laboral" });
assert.deepEqual(precioHoy(GOLEM, "2026-11-06"), { precio: 8.0, tipo: "laboral" });
assert.deepEqual(precioHoy(GOLEM, "2026-11-07"), { precio: 9.1, tipo: "finde" });

// Festivo en martes (8-12-2026): precio de finde; con precio único, la entrada (sin día del espectador)
assert.deepEqual(precioHoy(RENOIR, "2026-12-08"), { precio: 9.8, tipo: "festivo" });
assert.deepEqual(precioHoy(RIO, "2026-12-08"), { precio: 9.5, tipo: "entrada" });
// Festivo en lunes (9-11-2026, Almudena): anula el día del espectador
assert.deepEqual(precioHoy(RENOIR, "2026-11-09"), { precio: 9.8, tipo: "festivo" });
assert.deepEqual(precioHoy(RENOIR, "2026-11-16"), { precio: 5.5, tipo: "espectador" });

// Embajadores Río: martes y jueves 7,50; miércoles 5,90; resto, entrada
assert.deepEqual(precioHoy(RIO, "2026-11-05"), { precio: 7.5, tipo: "espectador" });
assert.deepEqual(precioHoy(RIO, "2026-11-10"), { precio: 7.5, tipo: "espectador" });
assert.deepEqual(precioHoy(RIO, "2026-11-04"), { precio: 5.9, tipo: "espectador" });
assert.deepEqual(precioHoy(RIO, "2026-11-06"), { precio: 9.5, tipo: "entrada" });
// Dos reglas el mismo día: gana la más barata
const SOLAPE = { entrada: 9, dia_espectador: [{ dias: ["Lunes"], precio: 7 }, { dias: ["Lunes", "Martes"], precio: 6 }] };
assert.equal(precioHoy(SOLAPE, "2026-11-16").precio, 6);

// Formato antiguo de un solo precio, sin tarifas y sin precio único
assert.deepEqual(precioHoy(VERDI, "2026-11-16"), { precio: 4.9, tipo: "espectador" });
assert.equal(precioHoy(null, "2026-11-16"), null);
assert.deepEqual(precioHoy(METROPOL, "2026-11-16"), { precio: null, tipo: "entrada" });

// Hora de Madrid: verano (CEST) y invierno (CET), justo pasada la medianoche cuando en UTC aún es el día anterior
assert.deepEqual(precioHoy(RENOIR, hoyMadrid(new Date("2026-07-30T22:30Z"))), { precio: 9.8, tipo: "finde" }); // vie 31-7 00:30
assert.deepEqual(precioHoy(RENOIR, hoyMadrid(new Date("2026-07-30T21:30Z"))), { precio: 8.5, tipo: "laboral" }); // jue 23:30
assert.deepEqual(precioHoy(RENOIR, hoyMadrid(new Date("2026-12-07T23:30Z"))), { precio: 9.8, tipo: "festivo" }); // mar 8-12 00:30
assert.deepEqual(precioHoy(RIO, hoyMadrid(new Date("2026-12-08T23:30Z"))), { precio: 5.9, tipo: "espectador" }); // mié 9-12 00:30

// esDiaEspectador (chip "Espectador" y filtro de la portada), con la fecha_hora de la API (hora de Madrid)
assert.equal(esDiaEspectador(RIO, "2026-11-10T20:00:00"), true);   // martes
assert.equal(esDiaEspectador(RIO, "2026-11-11T20:00:00"), true);   // miércoles
assert.equal(esDiaEspectador(RIO, "2026-11-12T20:00:00"), true);   // jueves
assert.equal(esDiaEspectador(RIO, "2026-11-16T20:00:00"), false);  // lunes (antes salía como espectador)
assert.equal(esDiaEspectador(RIO, "2026-12-08T20:00:00"), false);  // martes festivo
assert.equal(esDiaEspectador(RENOIR, "2026-11-09T18:00:00"), false); // lunes festivo (Almudena)
assert.equal(esDiaEspectador(RENOIR, "2026-11-16T18:00:00"), true);  // lunes normal
assert.equal(esDiaEspectador(RENOIR, "2026-11-13T18:00:00"), false); // viernes: finde en Renoir
assert.equal(esDiaEspectador(undefined, "2026-11-16T18:00:00"), false); // cine sin tarifas
assert.equal(esDiaEspectador(METROPOL, "2026-11-16T18:00:00"), false);  // tarifas sin día del espectador
assert.equal(esDiaEspectador(VERDI, undefined), false);
assert.equal(esDiaEspectador(VERDI, "2026-11-17T00:30:00"), false); // martes 00:30: cuenta el día real, no el UTC

// precioDia para fechas concretas; precioHoy es el mismo cálculo con la fecha de hoy por defecto
assert.deepEqual(precioDia(RENOIR, "2026-11-13"), { precio: 9.8, tipo: "finde" });
assert.deepEqual(precioHoy(RENOIR), precioDia(RENOIR, hoyMadrid()));

// precioSesion (modal, Mis sesiones, pases cerca). Los importes en es-ES llevan espacio duro antes de €.
const sesion = (tarifas, fechaHora, precio = "Consultar") => {
  const r = precioSesion({ precio, tarifas, fechaHora });
  return r && { ...r, texto: r.texto.replace(/ /g, " ") };
};
const RENOIR_NOTA = { ...RENOIR, notas: "Precios de taquilla; en Pillalas.com, 0,10 € menos." };
assert.deepEqual(sesion(RENOIR_NOTA, "2026-11-13T20:00:00"),  // viernes en Renoir
  { texto: "Entrada: 9,80 € · fin de semana", orientativo: true, nota: RENOIR_NOTA.notas });
assert.equal(sesion(RENOIR, "2026-11-12T20:00:00").texto, "Entrada: 8,50 € · día laborable");
assert.equal(sesion(RENOIR, "2026-12-08T20:00:00").texto, "Entrada: 9,80 € · festivo");      // martes festivo
assert.equal(sesion(RENOIR, "2026-11-16T20:00:00").texto, "Día del espectador: 5,50 €");
assert.equal(sesion(RIO, "2026-11-12T20:00:00").texto, "Día del espectador: 7,50 €");          // jueves en Río
assert.equal(sesion(RIO, "2026-11-13T20:00:00").texto, "Entrada: 9,50 €");
assert.deepEqual(sesion(METROPOL, "2026-11-13T20:00:00"), { texto: "Según la película", orientativo: true, nota: METROPOL.notas });
assert.equal(sesion({ entrada: 9, notas: "Cine de culto." }, "2026-11-13T20:00:00").nota, null); // nota sin precios: fuera
// Cine sin tarifas, tarifas aún sin llegar (o fallidas) y pase con precio real
assert.deepEqual(sesion(null, "2026-11-13T20:00:00"), { texto: "Consulta el precio en la web del cine", orientativo: false, nota: null });
assert.equal(sesion(undefined, "2026-11-13T20:00:00"), null);
assert.deepEqual(sesion(undefined, "2026-11-13T20:00:00", "6,50 €"), { texto: "6,50 €", orientativo: false, nota: null });
assert.equal(sesion(RENOIR, "2026-11-13T20:00:00", "6,50 €").texto, "6,50 €");
// Hora de Madrid: la fecha_hora de la API ya es de Madrid; se lee del texto, sin depender del huso del equipo
process.env.TZ = "America/New_York";
assert.equal(sesion(RENOIR, "2026-07-31T00:30:00").texto, "Entrada: 9,80 € · fin de semana"); // vie 00:30, verano
assert.equal(sesion(RENOIR, "2026-07-30T23:30:00").texto, "Entrada: 8,50 € · día laborable"); // jue 23:30
assert.equal(sesion(RENOIR, "2026-12-08T00:15:00").texto, "Entrada: 9,80 € · festivo");       // invierno
assert.equal(sesion(RIO, "2026-12-09T00:30:00").texto, "Día del espectador: 5,90 €");
process.env.TZ = "Pacific/Auckland";
assert.equal(sesion(RIO, "2026-11-11T23:59:00").texto, "Día del espectador: 5,90 €");

// Lista de festivos: claves válidas, 14 por año
assert.ok([...FESTIVOS].every((f) => /^\d{4}-\d{2}-\d{2}$/.test(f) && !Number.isNaN(Date.parse(f))));
assert.equal([...FESTIVOS].filter((f) => f.startsWith("2026")).length, 14);
assert.equal([...FESTIVOS].filter((f) => f.startsWith("2027")).length, 14);

console.log("OK: tarifas (finde por cine, festivos, días del espectador, hora de Madrid)");
