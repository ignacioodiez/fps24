import { fetchConAuth } from "@/lib/api";

// Diario del usuario (backend/app/diario.py). Nunca se manda user_id: el backend lo saca del token.

export const COMENTARIO_MAX = 2000; // el mismo que en el backend
// Evento de window al añadir una entrada desde el "+" de la barra; detail = la entrada guardada
export const DIARIO_GUARDADO = "diario:guardado";

const CAMPOS = { fecha_vista: "Fecha", cine_slug: "Cine", nota: "Nota", comentario: "Comentario", repeticion: "Repetición" };

// Error con mensaje para el usuario; status 401 = hay que volver a iniciar sesión
export class ErrorDiario extends Error {
  constructor(mensaje, status) {
    super(mensaje);
    this.status = status;
  }
}

function mensajeError(status, detalle) {
  if (status === 401) return "Tu sesión ha caducado. Vuelve a iniciar sesión para seguir con tu diario.";
  if (status === 409) return "Ya tienes esta película en tu diario ese día.";
  if (status === 404) return "Esa entrada ya no existe en tu diario.";
  if (status === 422) {
    // FastAPI: lista de errores de validación ({loc, msg}) o un texto (cine o película desconocidos)
    if (!Array.isArray(detalle)) return detalle || "Revisa los datos.";
    return detalle.map((d) => `${CAMPOS[d.loc?.at(-1)] ?? "Dato"}: ${d.msg.replace(/^Value error, /, "")}`).join(". ");
  }
  return "No hemos podido conectar con el diario. Inténtalo de nuevo.";
}

async function pedir(ruta, opciones = {}) {
  let res;
  try {
    res = await fetchConAuth(ruta, opciones);
  } catch {
    throw new ErrorDiario(mensajeError(0), 0);
  }
  if (res.ok) return res.status === 204 ? null : res.json();
  const cuerpo = await res.json().catch(() => ({}));
  throw new ErrorDiario(mensajeError(res.status, cuerpo.detail), res.status);
}

const enviar = (metodo, datos) => ({ method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });

export const listar = (limite = 20, desplazamiento = 0) => pedir(`/diario?limite=${limite}&desplazamiento=${desplazamiento}`);
export const crear = (datos) => pedir("/diario", enviar("POST", datos));
export const editar = (id, datos) => pedir(`/diario/${id}`, enviar("PATCH", datos));
export const borrar = (id) => pedir(`/diario/${id}`, { method: "DELETE" });
export const entradasDePelicula = (peliculaId) => pedir(`/diario/pelicula/${peliculaId}`);
// Públicos
export const cinesDelDia = (peliculaId, fecha) => pedir(`/pelicula/${peliculaId}/cines?fecha=${fecha}`);
export const todosLosCines = () => pedir("/cines");
export const buscarPeliculas = (q, signal) => pedir(`/peliculas/buscar?q=${encodeURIComponent(q)}&limite=20`, { signal });

// Hoy en Madrid ("YYYY-MM-DD"), el mismo límite que aplica el backend a fecha_vista
export const hoyMadrid = () => new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Madrid" });
export const ayerMadrid = () => new Date(Date.parse(`${hoyMadrid()}T00:00Z`) - 864e5).toISOString().slice(0, 10);

// Fecha por defecto al apuntar: el día elegido si es hoy o pasado; si no, hoy
export const fechaPorDefecto = (dia) => {
  const hoy = hoyMadrid();
  return /^\d{4}-\d{2}-\d{2}$/.test(dia ?? "") && dia <= hoy ? dia : hoy;
};
