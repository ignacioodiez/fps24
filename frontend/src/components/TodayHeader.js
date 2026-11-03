import Header from "@/components/Header";
import { backdropDeHoy } from "@/lib/peliculas";

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Header con el backdrop de hoy para páginas que no cargan los pases (p. ej. /cines). showTitle: ver Header.
// En el servidor: el navegador ya no descarga /pases (1,2 MB) solo para el fondo, y el fondo llega en el HTML.
// shortcut: la caché de datos de Next guarda respuestas de hasta 2 MB; si /pases pasa de ahí, se pide en cada render (un endpoint ligero lo arreglaría)
export default async function TodayHeader({ showTitle = true }) {
  let backdrop = null;
  try {
    const res = await fetch(`${API}/pases`, { next: { revalidate: 300 } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    backdrop = backdropDeHoy(await res.json());
  } catch (err) {
    console.error("Error loading sessions:", err); // sin backdrop: fondo blanco
  }
  return <Header backdrop={backdrop} showTitle={showTitle} />;
}
