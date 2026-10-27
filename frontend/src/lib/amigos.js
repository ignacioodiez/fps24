import { fetchConAuth } from "@/lib/api";

// Amigos y bloqueos (backend/app/amigos.py), siempre por nombre de usuario. Pedir amistad responde lo mismo exista o
// no la otra persona: aquí solo se enseña ese mensaje.

function mensajeError(status, detalle) {
  if (status === 401) return "Tu sesión ha caducado. Vuelve a iniciar sesión.";
  if ([404, 409, 422, 429].includes(status) && typeof detalle === "string") return detalle; // topes, sin perfil...
  return "No hemos podido conectar. Inténtalo de nuevo.";
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

const conUsuario = (usuario) => ({
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ usuario }),
});
const u = encodeURIComponent;

export const listarAmigos = () => pedir("/me/amigos"); // { amigos, recibidas, enviadas }
export const pedirAmistad = (usuario) => pedir("/me/amigos/solicitudes", conUsuario(usuario)); // { mensaje }
export const aceptarSolicitud = (id) => pedir(`/me/amigos/solicitudes/${id}/aceptar`, { method: "POST" });
export const rechazarSolicitud = (id) => pedir(`/me/amigos/solicitudes/${id}/rechazar`, { method: "POST" });
export const cancelarSolicitud = (id) => pedir(`/me/amigos/solicitudes/${id}`, { method: "DELETE" });
export const quitarAmigo = (usuario) => pedir(`/me/amigos/${u(usuario)}`, { method: "DELETE" });
export const listarBloqueos = () => pedir("/me/bloqueos");
export const bloquear = (usuario) => pedir("/me/bloqueos", conUsuario(usuario));
export const desbloquear = (usuario) => pedir(`/me/bloqueos/${u(usuario)}`, { method: "DELETE" });

// GET /u/<usuario> con mi token: lo que yo puedo ver (lo "solo amigos" incluido) y mi relación con esa persona.
// null si para mí no existe (404 neutro); lanza si falla la red.
export async function leerPerfilComoYo(usuario, pagina = 1) {
  const res = await fetchConAuth(`/u/${u(usuario)}?pagina=${pagina}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(mensajeError(res.status));
  return res.json();
}
