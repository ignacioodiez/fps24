import { fetchConAuth } from "@/lib/api";

// Panel admin (backend/app/admin.py). Para quien no es admin la API responde 404 en todo.

async function pedir(ruta, opciones = {}) {
  const res = await fetchConAuth(ruta, opciones);
  if (!res.ok) throw new Error(`${ruta}: HTTP ${res.status}`);
  return res.status === 204 ? null : res.json();
}

export const leerResumen = () => pedir("/admin/resumen");
export const leerUsuarios = (pagina) => pedir(`/admin/usuarios?pagina=${pagina}`);
export const buscarAdmin = (q) => pedir(`/admin/peliculas/buscar?q=${encodeURIComponent(q)}`);
export const leerOcultas = () => pedir("/admin/peliculas/ocultas");
// sin_ficha: próximo estreno de TMDB que aún no está en pelicula; se oculta de /estrenos por tmdb_id
const rutaOcultar = (p) => (p.sin_ficha ? `/admin/estrenos-proximos/${p.tmdb_id}/ocultar` : `/admin/peliculas/${p.id}/ocultar`);
export const claveAdmin = (p) => (p.sin_ficha ? `tmdb-${p.tmdb_id}` : p.id);
export const ocultar = (p) => pedir(rutaOcultar(p), { method: "POST" });
export const mostrar = (p) => pedir(rutaOcultar(p), { method: "DELETE" });
// Newsletter: la vista previa es HTML, no JSON
export async function vistaPreviaNewsletter() {
  const res = await fetchConAuth("/admin/newsletter/vista-previa");
  if (!res.ok) throw new Error(`vista previa: HTTP ${res.status}`);
  return res.text();
}
export const enviarPruebaNewsletter = () => pedir("/admin/newsletter/enviar-prueba", { method: "POST" });
