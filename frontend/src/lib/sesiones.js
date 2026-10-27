import { fetchConAuth } from "@/lib/api";

// Sesiones guardadas, la agenda privada (backend/app/sesiones.py). Solo se manda el id del pase: el backend copia
// la sesión desde la BD y saca el usuario del token.

function mensajeError(status, detalle) {
  if (status === 401) return "Tu sesión ha caducado. Vuelve a iniciar sesión.";
  if ((status === 409 || status === 422) && typeof detalle === "string") return detalle; // tope, "La vi" sin película...
  if (status === 404) return "Esa sesión ya no está en la cartelera.";
  return "No hemos podido conectar con tu agenda. Inténtalo de nuevo.";
}

async function pedir(ruta, opciones = {}) {
  let res;
  try {
    res = await fetchConAuth(ruta, opciones);
  } catch {
    throw new Error(mensajeError(0));
  }
  if (res.ok) return res.status === 204 ? null : res.json();
  const cuerpo = await res.json().catch(() => ({}));
  throw new Error(mensajeError(res.status, cuerpo.detail));
}

export const listarSesiones = () => pedir("/me/sesiones"); // { proximas, pasadas }
export const marcasSesiones = () => pedir("/me/sesiones/ids"); // [{ id, sesion_id }]
export const guardarSesion = (sesionId) =>
  pedir("/me/sesiones", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ sesion_id: sesionId }) });
export const quitarSesion = (id) => pedir(`/me/sesiones/${id}`, { method: "DELETE" });
export const marcarVista = (id) => pedir(`/me/sesiones/${id}/vista`, { method: "POST" });
