// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITIO = "https://fps24.es";

// Se regenera cada hora; si la API no responde, solo las páginas fijas
export const revalidate = 3600;

export default async function sitemap() {
  let cines = [];
  try {
    const res = await fetch(`${API}/cines`, { next: { revalidate } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    cines = await res.json();
  } catch (err) {
    console.error("sitemap: error loading cines:", err);
  }
  return [
    ...["", "/cines", "/estrenos", "/especiales", "/newsletter", "/privacidad"].map((ruta) => ({ url: `${SITIO}${ruta}` })),
    ...cines.map(({ slug }) => ({ url: `${SITIO}/cines/${slug}` })),
  ];
}
