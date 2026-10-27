// Las fechas de la API son de Madrid sin zona: se leen y se escriben en UTC para que el huso del servidor no las mueva
export const comoUTC = (texto) => new Date(texto.length === 10 ? `${texto}T00:00Z` : `${texto}Z`);
export const formato = (texto, opciones) =>
  comoUTC(texto).toLocaleString("es-ES", { timeZone: "UTC", ...opciones }).replace(".", "");

// "sáb 24 · 17:30"
export const sesionCorta = (fechaHora) =>
  `${formato(fechaHora, { weekday: "short" })} ${comoUTC(fechaHora).getUTCDate()} · ${formato(fechaHora, { hour: "2-digit", minute: "2-digit" })}`;

// --- Selector de días: todo con claves "AAAA-MM-DD" de Madrid, operadas en UTC (el cambio de hora no las mueve) ---
const madrid = new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Madrid", year: "numeric", month: "2-digit", day: "2-digit" });
export const hoyMadrid = (ahora = new Date()) => madrid.format(ahora);

export const sumarDias = (clave, n) => {
  const d = comoUTC(clave);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};

// "Hoy", "Mañana" o null
export const etiquetaRelativa = (clave, hoy) => (clave === hoy ? "Hoy" : clave === sumarDias(hoy, 1) ? "Mañana" : null);

// 28 días, de lunes de la semana de hoy a domingo cuatro semanas después
export const cuatroSemanas = (hoy) => {
  const lunes = sumarDias(hoy, -((comoUTC(hoy).getUTCDay() + 6) % 7));
  return Array.from({ length: 28 }, (_, i) => sumarDias(lunes, i));
};

const mayuscula = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const anio = (clave) => clave.slice(0, 4);
const mes = (clave, month) => mayuscula(formato(clave, { month }));

// "Octubre 2026", "Oct – Nov 2026" o "Dic 2026 – Ene 2027"
export const rotuloMes = (desde, hasta = desde) => {
  if (desde.slice(0, 7) === hasta.slice(0, 7)) return `${mes(desde, "long")} ${anio(desde)}`;
  if (anio(desde) === anio(hasta)) return `${mes(desde, "short")} – ${mes(hasta, "short")} ${anio(hasta)}`;
  return `${mes(desde, "short")} ${anio(desde)} – ${mes(hasta, "short")} ${anio(hasta)}`;
};

// "martes 27 de octubre"
export const diaCompleto = (clave) =>
  `${formato(clave, { weekday: "long" })} ${comoUTC(clave).getUTCDate()} de ${formato(clave, { month: "long" })}`;
