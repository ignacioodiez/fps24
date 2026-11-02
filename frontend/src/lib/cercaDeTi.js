// "Encuentra pases cerca de ti" (SalasYPrecios.js): todo en el cliente, la ubicación nunca sale del navegador.
// Las horas van en un eje "reloj de Madrid leído como UTC" (comoUTC), el mismo de fecha_hora de la API: así el
// huso del dispositivo no cuenta. shortcut: en la noche del cambio de hora el eje se desfasa 1 h; si molesta,
// pasar a instantes reales con el desfase de Europe/Madrid.
import { comoUTC } from "./fechasMadrid.js";

const MIN = 60000;

// Distancia en línea recta (haversine) en km entre dos { lat, lng }
export const distanciaKm = (a, b) => {
  const rad = Math.PI / 180;
  const h = Math.sin(((b.lat - a.lat) * rad) / 2) ** 2
    + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(((b.lng - a.lng) * rad) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
};

// "650 m" o "1,2 km"
export const textoDistancia = (km) => km < 1
  ? `${Math.max(10, Math.round(km * 100) * 10)} m`
  : `${km.toLocaleString("es-ES", { maximumFractionDigits: 1 })} km`;

// Minutos andando: 80 m/min y un 30 % más que la línea recta por las calles
export const minutosAndando = (km) => Math.max(1, Math.round((km * 1000 * 1.3) / 80));

// "Ahora" en el eje de Madrid (ms), sea cual sea el huso del dispositivo
export const ahoraMadrid = (fecha = new Date()) =>
  comoUTC(fecha.toLocaleString("sv-SE", { timeZone: "Europe/Madrid" }).replace(" ", "T")).getTime();

// La cartelera de un día llega hasta las 6:00 del siguiente (sesiones de madrugada)
const CIERRE_H = 6;

// Fin de la ventana: "1h", "2h" o "noche" (hasta el cierre del día de cartelera en curso)
export const finVentana = (ahora, ventana) => {
  if (ventana === "1h") return ahora + 60 * MIN;
  if (ventana === "2h") return ahora + 120 * MIN;
  const d = new Date(ahora);
  const cierre = Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), CIERRE_H);
  return d.getUTCHours() < CIERRE_H ? cierre : cierre + 24 * 60 * MIN;
};

// Pases que empiezan entre ahora y el fin de la ventana, con su instante (ms) y los minutos que faltan
export const enVentana = (pases, ahora, ventana) => {
  const fin = finVentana(ahora, ventana);
  return pases
    .map((pase) => ({ pase, inicio: comoUTC(pase.fecha_hora).getTime() }))
    .filter(({ inicio }) => inicio >= ahora && inicio <= fin)
    .map((x) => ({ ...x, minutos: Math.round((x.inicio - ahora) / MIN) }));
};

// Slugs de los cines con alguna sesión en la próxima hora
export const cinesConPronto = (pases, ahora) => new Set(enVentana(pases, ahora, "1h").map(({ pase }) => pase.cine_slug));

// Hasta `max` sesiones a `radioKm` o menos de `pos`, por hora y, a igualdad, por distancia.
// cines: Map slug -> cine (con lat/lng); los cines sin coordenadas no entran.
export const pasesCerca = (pases, cines, pos, ahora, { radioKm, ventana }, max = 5) =>
  enVentana(pases, ahora, ventana)
    .map((x) => {
      const cine = cines.get(x.pase.cine_slug);
      return { ...x, cine, distancia: cine?.lat != null && cine?.lng != null ? distanciaKm(pos, cine) : Infinity };
    })
    .filter(({ distancia }) => distancia <= radioKm)
    .sort((a, b) => a.inicio - b.inicio || a.distancia - b.distancia)
    .slice(0, max);

// Como pasesCerca, pero si no hay nada amplía a 2 km y 2 h (sin estrechar lo elegido). ampliado: el filtro usado
// si se ha ampliado, o null.
export const buscarCerca = (pases, cines, pos, ahora, filtro, max = 5) => {
  const items = pasesCerca(pases, cines, pos, ahora, filtro, max);
  const amplio = { radioKm: Math.max(filtro.radioKm, 2), ventana: filtro.ventana === "1h" ? "2h" : filtro.ventana };
  if (items.length > 0 || (amplio.radioKm === filtro.radioKm && amplio.ventana === filtro.ventana)) {
    return { items, ampliado: null };
  }
  return { items: pasesCerca(pases, cines, pos, ahora, amplio, max), ampliado: amplio };
};

// Centro de los cines con coordenadas de una zona (alternativa sin geolocalización), o null
export const centroZona = (cines, zona) => {
  const conPunto = cines.filter((c) => c.zona === zona && c.lat != null && c.lng != null);
  if (conPunto.length === 0) return null;
  const media = (k) => conPunto.reduce((s, c) => s + c[k], 0) / conPunto.length;
  return { lat: media("lat"), lng: media("lng") };
};
