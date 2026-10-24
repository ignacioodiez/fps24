import { fetchConAuth } from "@/lib/api";

// Perfil del usuario (backend/app/perfil.py). Las reglas del nombre solo están en el backend:
// aquí se enseña el motivo que devuelve /usuarios/disponible o el PUT.

export const BIO_MAX = 160; // el mismo que en el backend

export class ErrorPerfil extends Error {
  constructor(mensaje, status) {
    super(mensaje);
    this.status = status;
  }
}

function mensajeError(status, detalle) {
  if (status === 401) return "Tu sesión ha caducado. Vuelve a iniciar sesión.";
  if (typeof detalle === "string") return detalle; // 409, 422 y 429 traen el motivo en español
  if (status === 422) return "Revisa los datos.";
  return "No hemos podido conectar. Inténtalo de nuevo.";
}

async function pedir(ruta, opciones = {}) {
  let res;
  try {
    res = await fetchConAuth(ruta, opciones);
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ErrorPerfil(mensajeError(0), 0);
  }
  if (res.ok) return res.json();
  const cuerpo = await res.json().catch(() => ({}));
  throw new ErrorPerfil(mensajeError(res.status, cuerpo.detail), res.status);
}

export const leerPerfil = () => pedir("/me/perfil");
export const guardarPerfil = (datos) =>
  pedir("/me/perfil", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });
export const comprobarUsuario = (u, signal) => pedir(`/usuarios/disponible?u=${encodeURIComponent(u)}`, { signal });
