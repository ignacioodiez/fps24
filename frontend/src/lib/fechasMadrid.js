// Las fechas de la API son de Madrid sin zona: se leen y se escriben en UTC para que el huso del servidor no las mueva
export const comoUTC = (texto) => new Date(texto.length === 10 ? `${texto}T00:00Z` : `${texto}Z`);
export const formato = (texto, opciones) =>
  comoUTC(texto).toLocaleString("es-ES", { timeZone: "UTC", ...opciones }).replace(".", "");

// "sáb 24 · 17:30"
export const sesionCorta = (fechaHora) =>
  `${formato(fechaHora, { weekday: "short" })} ${comoUTC(fechaHora).getUTCDate()} · ${formato(fechaHora, { hour: "2-digit", minute: "2-digit" })}`;
