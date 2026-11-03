import { comoUTC, hoyMadrid, sumarDias } from "./fechasMadrid.js";

// Festivos de la ciudad de Madrid (Comunidad + los dos locales), en claves "AAAA-MM-DD" de Madrid. Se cobran como
// fin de semana. Añade aquí cada año. Fuentes (calendario laboral oficial):
//   2026: Decreto 75/2025 (BOCM 25-09-2025) y Resolución DG de Trabajo de 2-12-2025 (BOCM 12-12-2025, locales)
//   2027: Decreto 82/2026 (BOCM 01-10-2026); locales aprobados por el Pleno del Ayuntamiento el 29-09-2026
export const FESTIVOS = new Set([
  // 2026
  "2026-01-01", "2026-01-06", "2026-04-02", "2026-04-03", "2026-05-01", "2026-05-02", "2026-05-15", "2026-08-15",
  "2026-10-12", "2026-11-02", "2026-11-09", "2026-12-07", "2026-12-08", "2026-12-25",
  // 2027
  "2027-01-01", "2027-01-06", "2027-03-19", "2027-03-25", "2027-03-26", "2027-05-01", "2027-05-15", "2027-08-16",
  "2027-10-12", "2027-11-01", "2027-11-09", "2027-12-06", "2027-12-08", "2027-12-25",
]);

const DIAS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const FINDE = ["Sábado", "Domingo"];

// dia_espectador: {dias, precio} o una lista de ellos
export const reglasEspectador = (tarifas) => [tarifas?.dia_espectador ?? []].flat();

// Precio de una entrada el día `fecha` ("AAAA-MM-DD" de Madrid) según cine.tarifas: { precio, tipo } con tipo
// "espectador", "festivo", "finde", "laboral" o "entrada"; precio null si hay tarifas pero no un precio único
// (p. ej. según sala); null sin tarifas. Un festivo cuenta como fin de semana y anula el día del espectador.
export const precioDia = (tarifas, fecha) => {
  if (!tarifas) return null;
  const dia = DIAS[comoUTC(fecha).getUTCDay()];
  const festivo = FESTIVOS.has(fecha);
  const espectador = festivo ? [] : reglasEspectador(tarifas).filter((r) => r.dias.includes(dia));
  if (espectador.length) return { precio: Math.min(...espectador.map((r) => r.precio)), tipo: "espectador" };
  const finde = festivo || (tarifas.finde_dias ?? FINDE).includes(dia);
  if (finde && tarifas.entrada_finde != null) return { precio: tarifas.entrada_finde, tipo: festivo ? "festivo" : "finde" };
  if (!finde && tarifas.entrada_laboral != null) return { precio: tarifas.entrada_laboral, tipo: "laboral" };
  const precio = tarifas.entrada ?? tarifas.entrada_laboral ?? tarifas.entrada_finde ?? null;
  return { precio, tipo: "entrada" };
};

// El de hoy (Madrid) por defecto
export const precioHoy = (tarifas, fecha = hoyMadrid()) => precioDia(tarifas, fecha);

// ¿Día del espectador en ese cine? fechaHora de la API ("AAAA-MM-DDTHH:MM:SS", ya en hora de Madrid). Sin tarifas, no.
export const esDiaEspectador = (tarifas, fechaHora) =>
  !!fechaHora && precioDia(tarifas, fechaHora.slice(0, 10))?.tipo === "espectador";

export const euros = (n) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
export const ETIQUETA_TIPO = { festivo: "festivo", finde: "fin de semana", laboral: "día laborable", entrada: "entrada" };

// Precio que trae el pase si es real (casi siempre llega "Consultar")
export const precioReal = (precio) => (precio && precio !== "Consultar" ? precio : null);

// Texto del precio de una sesión: { texto, orientativo, nota } o null si aún no se sabe.
// tarifas: las del cine; undefined = todavía no han llegado (o fallaron): no se muestra nada; null = el cine no tiene.
// shortcut: la nota se enseña solo si habla de euros ("Salas Luxury: 15,50 €"); si hay notas sin € útiles, un campo propio.
export const precioSesion = ({ precio, tarifas, fechaHora }) => {
  const real = precioReal(precio);
  if (real) return { texto: real, orientativo: false, nota: null };
  if (tarifas === undefined || !fechaHora) return null;
  if (tarifas === null) return { texto: "Consulta el precio en la web del cine", orientativo: false, nota: null };
  const dia = precioDia(tarifas, fechaHora.slice(0, 10));
  const nota = tarifas.notas?.includes("€") ? tarifas.notas : null;
  const texto = dia.precio == null ? tarifas.precio_texto ?? "Precio según sala"
    : dia.tipo === "espectador" ? `Día del espectador: ${euros(dia.precio)}`
    : `Entrada: ${euros(dia.precio)}${dia.tipo === "entrada" ? "" : ` · ${ETIQUETA_TIPO[dia.tipo]}`}`;
  return { texto, orientativo: true, nota };
};

// "4,90 €–8,50 €" con los precios numéricos de la tabla de tarifas (las notas, texto libre, no cuentan); null sin ellos
export const rangoPrecios = (tarifas) => {
  const t = tarifas ?? {};
  const precios = [t.entrada, t.entrada_laboral, t.entrada_finde, ...[t.dia_espectador ?? []].flat().map((r) => r.precio)]
    .filter((p) => typeof p === "number" && p >= 0);
  if (!precios.length) return null;
  const eur = (p) => `${p.toFixed(2).replace(".", ",")} €`;
  const [min, max] = [Math.min(...precios), Math.max(...precios)];
  return min === max ? eur(min) : `${eur(min)}–${eur(max)}`;
};

// --- Página /dia-del-espectador-madrid. cines: los de GET /cines ({ slug, nombre, tarifas }) ---

// Los 7 días desde hoy: [{ fecha, festivo, cines: [{ slug, nombre, precio }] }] con los cines en día del espectador
// ese día (precioDia: un festivo lo anula), del más barato al más caro
export const semanaEspectador = (cines, hoy) =>
  Array.from({ length: 7 }, (_, i) => sumarDias(hoy, i)).map((fecha) => ({
    fecha,
    festivo: FESTIVOS.has(fecha),
    cines: cines
      .map((c) => ({ slug: c.slug, nombre: c.nombre, dia: precioDia(c.tarifas, fecha) }))
      .filter(({ dia }) => dia?.tipo === "espectador")
      .map(({ slug, nombre, dia }) => ({ slug, nombre, precio: dia.precio }))
      .sort((a, b) => a.precio - b.precio || a.nombre.localeCompare(b.nombre, "es")),
  }));

// Precio de hoy por cine: conPrecio (del más barato al más caro, con { precio, tipo }) y sinPrecio (tarifa sin precio
// único, p. ej. según la película, o sin tarifa verificada). Nada se calcula si no está en la tabla de tarifas.
export const cinesPorPrecio = (cines, hoy) => {
  const conPrecio = [];
  const sinPrecio = [];
  for (const c of cines) {
    const dia = precioDia(c.tarifas, hoy);
    (dia?.precio != null ? conPrecio : sinPrecio).push({ ...c, hoy: dia });
  }
  conPrecio.sort((a, b) => a.hoy.precio - b.hoy.precio || a.nombre.localeCompare(b.nombre, "es"));
  sinPrecio.sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  return { conPrecio, sinPrecio };
};

// Última revisión ("AAAA-MM-DD" o null) y los cines con tarifa pendientes de verificar (sin `revisado`)
export const revisionTarifas = (cines) => ({
  fecha: cines.map((c) => c.tarifas?.revisado).filter(Boolean).sort().at(-1) ?? null,
  pendientes: cines.filter((c) => c.tarifas && !c.tarifas.revisado),
});
