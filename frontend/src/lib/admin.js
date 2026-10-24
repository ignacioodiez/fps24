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
export const ocultar = (id) => pedir(`/admin/peliculas/${id}/ocultar`, { method: "POST" });
export const mostrar = (id) => pedir(`/admin/peliculas/${id}/ocultar`, { method: "DELETE" });
