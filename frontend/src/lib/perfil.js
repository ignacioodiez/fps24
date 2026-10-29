import { useEffect, useState } from "react";
import { fetchConAuth } from "@/lib/api";
import { motivoFormato } from "@/lib/usuario";

// Perfil del usuario (backend/app/perfil.py). El formato del nombre (lib/usuario.js) se comprueba aquí para avisar al
// momento; la lista de reservados y la unicidad solo las sabe el backend (/usuarios/disponible y el PUT).

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
// Público; con sesión, el nombre propio sale libre. { disponible } y, si el formato no vale, { motivo }
export const comprobarUsuario = (nombre, signal) => pedir(`/usuarios/disponible?nombre=${encodeURIComponent(nombre)}`, { signal });

const ESPERA_MS = 400; // debounce de la comprobación

// Comprobación al instante (con debounce) de un nombre: { estado: nada | comprobando | libre | no | error, motivo }.
// propio: el nombre que ya tiene (no se comprueba). Hasta que pasa la espera, "comprobando" sin texto nuevo.
export function useDisponibilidad(nombre, propio = null) {
  const [resultado, setResultado] = useState({ nombre: null });
  const valor = (nombre ?? "").trim();
  const comprobar = Boolean(valor) && valor !== propio;
  useEffect(() => {
    if (!comprobar) return;
    const control = new AbortController();
    const t = setTimeout(() => {
      const formato = motivoFormato(valor);
      if (formato) return setResultado({ nombre: valor, estado: "no", motivo: formato });
      comprobarUsuario(valor, control.signal)
        .then((r) => setResultado({ nombre: valor, estado: r.disponible ? "libre" : "no", motivo: r.disponible ? "Disponible" : r.motivo ?? "No disponible" }))
        .catch((err) => err.name !== "AbortError" && setResultado({ nombre: valor, estado: "error", motivo: err.message }));
    }, ESPERA_MS);
    return () => {
      clearTimeout(t);
      control.abort();
    };
  }, [valor, comprobar]);
  if (!comprobar) return { estado: "nada", motivo: "" };
  return resultado.nombre === valor ? resultado : { estado: "comprobando", motivo: "" };
}
