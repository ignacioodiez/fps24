import { hoyMadrid } from "@/lib/fechasMadrid";

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITIO = "https://fps24.es";

// Se regenera cada hora; si la API no responde, esa parte se queda fuera (las páginas fijas siempre van)
export const revalidate = 3600;

async function leer(ruta) {
  try {
    const res = await fetch(`${API}${ruta}`, { next: { revalidate } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`sitemap: error loading ${ruta}:`, err);
    return [];
  }
}

// Solo páginas públicas e indexables: nunca perfiles (/u/...), ni privadas, ni películas sin sesiones (noindex).
// Sin lastmod: la API no expone cuándo cambian las sesiones de una película o un cine, y uno inventado resta más que suma.
export default async function sitemap() {
  const [cines, pases] = await Promise.all([leer("/cines"), leer("/pases")]);
  const hoy = hoyMadrid();
  const peliculas = new Set(pases.filter((p) => p.fecha_hora.slice(0, 10) >= hoy).map((p) => p.pelicula_id));
  return [
    ...["", "/cines", "/estrenos", "/especiales", "/newsletter", "/privacidad"].map((ruta) => ({ url: `${SITIO}${ruta}` })),
    ...cines.map(({ slug }) => ({ url: `${SITIO}/cines/${slug}` })),
    ...[...peliculas].map((id) => ({ url: `${SITIO}/pelicula/${id}` })),
  ];
}
