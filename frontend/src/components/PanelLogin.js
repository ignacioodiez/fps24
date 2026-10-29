"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import CampoUsuario from "@/components/CampoUsuario";
import { guardarPerfil, useDisponibilidad } from "@/lib/perfil";
import { motivoFormato } from "@/lib/usuario";

const BOTON = "w-full px-4 py-2 rounded-full bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-60";

function mensajeError(error) {
  if (error?.status === 429 || /rate limit/i.test(error?.message)) {
    return "Demasiados intentos. Espera unos minutos y vuelve a probar.";
  }
  if (error?.code === "email_address_invalid" || /email.*invalid/i.test(error?.message)) {
    return "Ese email no parece válido. Revísalo.";
  }
  return "No hemos podido enviar el enlace. Inténtalo de nuevo.";
}

// Nombre elegido en "Crear cuenta" para entrar con Google (con el email viaja en los metadatos de la cuenta): se guarda
// aquí hasta el primer inicio de sesión, donde lo reclama ElegirUsuario. Sin almacenamiento (modo privado), se pide luego.
const CLAVE_ELEGIDO = "fps24:usuario-elegido";
function leerElegido() {
  try {
    return localStorage.getItem(CLAVE_ELEGIDO) ?? "";
  } catch {
    return "";
  }
}
function guardarElegido(nombre) {
  try {
    if (nombre) localStorage.setItem(CLAVE_ELEGIDO, nombre);
    else localStorage.removeItem(CLAVE_ELEGIDO);
  } catch {}
}

// Error con el que Google/Supabase devuelven al usuario (en la query o en el hash)
function errorOAuth() {
  const query = new URLSearchParams(window.location.search);
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const codigo = query.get("error") || hash.get("error");
  if (!codigo) return null;
  ["error", "error_code", "error_description"].forEach((k) => query.delete(k));
  const limpia = window.location.pathname + (query.size ? `?${query}` : "") + (hash.has("error") ? "" : window.location.hash);
  window.history.replaceState(window.history.state, "", limpia);
  return codigo === "access_denied"
    ? "Has cancelado el inicio de sesión con Google. Puedes volver a intentarlo o usar tu email."
    : "No hemos podido iniciar sesión con Google. Inténtalo de nuevo o usa tu email.";
}

// Botón oficial de Google Identity Services: el popup muestra fps24.es y no el dominio de Supabase.
// Sin Client ID, o si el script no carga, se usa el de redirección (signInWithOAuth).
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
const ESPERA_GIS = 5000;
let scriptGis; // promesa de carga del script, una vez por página
let gisIniciado; // promesa de initialize() con su nonce; se rehace tras usar el nonce
let alCredencial = () => {};

function cargarScriptGis() {
  scriptGis ??= new Promise((ok, mal) => {
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.onload = () => (window.google?.accounts?.id ? ok() : mal());
    s.onerror = mal;
    document.head.append(s);
    setTimeout(mal, ESPERA_GIS); // bloqueado o colgado: plan B
  });
  return scriptGis;
}

// Secuencia de nonce de Supabase: aleatorio, a Google su SHA-256 en hex y a signInWithIdToken el valor en claro
function iniciarGis() {
  gisIniciado ??= cargarScriptGis().then(async () => {
    const nonce = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32))));
    const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(nonce));
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      nonce: Array.from(new Uint8Array(hash), (b) => b.toString(16).padStart(2, "0")).join(""),
      callback: ({ credential }) => {
        gisIniciado = null; // un nonce por intento
        alCredencial(credential, nonce);
      },
    });
  });
  return gisIniciado;
}

// Panel de inicio de sesión (Google o magic link por email, Supabase Auth). Montado una vez en el layout; lo abre
// abrirLogin() del contexto (p. ej. "Iniciar sesión" de la barra). Sin variables de Supabase no se pinta.
// Con abrirLogin(mensaje, "crear") es "Crear cuenta": lo mismo y, arriba, el nombre de usuario que quiere.
export default function PanelLogin() {
  const { usuario, cargando, entrar, entrarConGoogle, entrarConTokenGoogle, peticionLogin } = useAuth();
  const dialogo = useRef(null);
  const [estado, setEstado] = useState("inicio"); // inicio | enviando | enviado
  const [error, setError] = useState("");
  const [google, setGoogle] = useState("inicio"); // inicio | redirigiendo | entrando
  const [gis, setGis] = useState(GOOGLE_CLIENT_ID ? "cargando" : "fallo"); // botón oficial: cargando | listo | fallo
  const [abierto, setAbierto] = useState(false);
  const botonGis = useRef(null);
  const [errorGoogle, setErrorGoogle] = useState("");
  const [motivo, setMotivo] = useState(""); // por qué se abre el panel desde fuera ("Inicia sesión para guardar tu diario")
  const atendida = useRef(peticionLogin); // la de antes de montar (otra página) no se atiende
  const [modo, setModo] = useState("entrar"); // entrar | crear
  const [nombre, setNombre] = useState("");
  const crear = modo === "crear";
  const comprobacion = useDisponibilidad(crear ? nombre : "");
  const id = useId();
  // Crear cuenta: las vías (Google y correo) solo con un nombre válido y libre. El libre se reclama tras entrar.
  const elegido = crear && comprobacion.estado === "libre" ? nombre.trim() : "";
  const vias = !crear || Boolean(elegido);

  // Al volver de Google con error: se avisa en el panel y se limpia la URL sin recargar
  useEffect(() => {
    if (!AUTH_DISPONIBLE || cargando || usuario) return;
    const mensaje = errorOAuth();
    if (!mensaje) return;
    setErrorGoogle(mensaje); // eslint-disable-line react-hooks/set-state-in-effect -- la URL solo se lee en el navegador
    dialogo.current?.showModal();
    setAbierto(true);
  }, [cargando, usuario]);

  // abrirLogin() del contexto: abre el panel con su mensaje
  useEffect(() => {
    if (!peticionLogin || peticionLogin === atendida.current || usuario) return;
    atendida.current = peticionLogin;
    setMotivo(peticionLogin.mensaje); // eslint-disable-line react-hooks/set-state-in-effect -- la petición llega por el contexto
    setModo(peticionLogin.modo ?? "entrar");
    dialogo.current?.showModal();
    setAbierto(true);
    dialogo.current?.querySelector("input")?.focus();
  }, [peticionLogin, usuario]);

  // Al abrir el panel (no antes) se carga GIS y se pinta el botón oficial; si falla, queda el de redirección
  // Callback de GIS (vive fuera de React): siempre apunta al render actual
  useEffect(() => {
    alCredencial = async (token, nonce) => {
      guardarElegido(elegido);
      setErrorGoogle("");
      setGoogle("entrando");
      try {
        await entrarConTokenGoogle(token, nonce);
        dialogo.current?.close(); // la sesión llega por onAuthStateChange, como con el magic link
      } catch {
        setGis("fallo");
        setGoogle("inicio");
        setErrorGoogle("No hemos podido iniciar sesión con Google desde aquí. Prueba con este botón o usa tu email.");
      }
    };
  });

  useEffect(() => {
    if (!abierto || !vias || gis === "fallo" || estado === "enviado") return;
    let vigente = true;
    iniciarGis()
      .then(() => {
        if (!vigente || !botonGis.current) return;
        window.google.accounts.id.renderButton(botonGis.current, {
          type: "standard", theme: "outline", size: "large", text: "continue_with", shape: "pill",
          logo_alignment: "center", locale: "es", width: Math.min(400, botonGis.current.offsetWidth),
        });
        setGis("listo");
      })
      .catch(() => {
        if (!vigente) return;
        setGis("fallo");
        setErrorGoogle("No se ha podido cargar el botón de Google (quizá lo impide un bloqueador). Usa este otro:");
      });
    return () => { vigente = false; };
  }, [abierto, vias, gis, estado]);

  if (!AUTH_DISPONIBLE || cargando || usuario) return null;

  const enviar = async (e) => {
    e.preventDefault();
    setError("");
    setEstado("enviando");
    try {
      await entrar(new FormData(e.currentTarget).get("email").trim(), elegido);
      setEstado("enviado");
    } catch (err) {
      setError(mensajeError(err));
      setEstado("inicio");
    }
  };

  const conGoogle = async () => {
    setErrorGoogle("");
    setGoogle("redirigiendo");
    guardarElegido(elegido);
    try {
      await entrarConGoogle();
    } catch {
      setErrorGoogle("No hemos podido conectar con Google. Inténtalo de nuevo.");
      setGoogle("inicio");
    }
  };

  const cerrar = () => dialogo.current?.close();

  return (
    <>
      {/* <dialog> nativo: Esc cierra, el foco queda dentro y vuelve al botón que lo abrió al cerrar */}
      <dialog
        ref={dialogo}
        aria-labelledby="titulo-entrar"
        onClose={() => { setAbierto(false); setEstado("inicio"); setError(""); setErrorGoogle(""); setGoogle("inicio"); setMotivo(""); setModo("entrar"); setNombre(""); }}
        onClick={(e) => e.target === e.currentTarget && cerrar()}
        className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl border border-line bg-background text-foreground p-0 backdrop:bg-black/40"
      >
        <div className="p-6 text-left">
          <div className="flex items-start justify-between gap-4">
            <h2 id="titulo-entrar" className="text-xl font-display font-bold uppercase">{crear ? "Crear cuenta" : "Iniciar sesión"}</h2>
            <button type="button" onClick={cerrar} aria-label="Cerrar" className="text-muted hover:text-primary text-xl leading-none">×</button>
          </div>

          {motivo && <p className="mt-2 text-sm font-semibold text-primary">{motivo}</p>}

          {crear && estado !== "enviado" && (
            <div className="mt-4">
              <CampoUsuario id={id} valor={nombre} onCambiar={setNombre} comprobacion={comprobacion} />
            </div>
          )}

          {estado === "enviado" ? (
            <p role="status" className="mt-4 text-foreground leading-relaxed">
              {crear
                ? "Te hemos enviado un enlace a tu email. Ábrelo en este mismo navegador."
                : "Si ese correo tiene cuenta, te hemos enviado el enlace (ábrelo en este mismo navegador). Si no, usa «Crear cuenta»."}
            </p>
          ) : !vias ? (
            <p className="mt-2 text-sm text-muted">Elige un nombre de usuario libre para continuar con Google o con tu email.</p>
          ) : (
            <>
            <div className="mt-4 space-y-2">
              {gis !== "fallo" && (
                // min-h: el hueco del botón (44px) se reserva mientras carga, sin saltos
                <div aria-busy={gis === "cargando"} className="flex min-h-11 w-full flex-col items-center justify-center">
                  {gis === "cargando" && <span className="text-sm text-muted">Cargando Google…</span>}
                  {/* GIS reescribe este div: React no le pone hijos */}
                  <div ref={botonGis} className="flex w-full justify-center" />
                </div>
              )}
              {google === "entrando" && <p role="status" className="text-sm text-muted text-center">Iniciando sesión con Google…</p>}
              {errorGoogle && <p role="alert" className="text-sm text-red-600">{errorGoogle}</p>}
              {gis === "fallo" && (
                <button type="button" onClick={conGoogle} disabled={google === "redirigiendo"} className={BOTON}>
                  {google === "redirigiendo" ? "Redirigiendo a Google…" : "Continuar con Google"}
                </button>
              )}
            </div>
            <div className="my-4 flex items-center gap-3 text-xs font-bold text-muted" aria-hidden="true">
              <span className="h-px flex-1 bg-line" />o<span className="h-px flex-1 bg-line" />
            </div>
            <form onSubmit={enviar} className="space-y-3">
              <p className="text-sm text-muted">Sin contraseñas: te mandamos un enlace para {crear ? "crear tu cuenta" : "iniciar sesión"}.</p>
              <label htmlFor="email-entrar" className="block text-xs font-bold uppercase tracking-wider text-muted">Email</label>
              <input
                id="email-entrar" name="email" type="email" required autoComplete="email"
                aria-invalid={Boolean(error)} aria-describedby={error ? "error-entrar" : undefined}
                className="w-full rounded-xl border border-line bg-background px-4 py-2 text-foreground focus:border-primary focus:outline-none"
              />
              {error && <p id="error-entrar" role="alert" className="text-sm text-red-600">{error}</p>}
              <button type="submit" disabled={estado === "enviando"} className={BOTON}>
                {estado === "enviando" ? "Enviando…" : "Enviarme el enlace"}
              </button>
            </form>
            </>
          )}
          {/* Abajo y pequeño, también mientras falta el nombre */}
          {estado !== "enviado" && (
            <p className="mt-3 text-xs text-muted text-center">
              {crear ? "Al crear tu cuenta aceptas la" : "Al continuar aceptas la"}{" "}
              <Link href="/privacidad" onClick={cerrar} className="underline hover:text-primary">política de privacidad</Link>
            </p>
          )}
        </div>
      </dialog>
    </>
  );
}

// Paso obligatorio tras el primer inicio de sesión sin nombre de usuario. Antes reclama (PUT /me/perfil) el elegido en
// "Crear cuenta" (de este navegador o de los metadatos de la cuenta); si ya está cogido, o no eligió ninguno, pide uno.
// La unicidad la decide el PUT (índice único de la BD), no la comprobación previa. Montado una vez en el layout.
export function ElegirUsuario() {
  const { usuario, miPerfil, setMiPerfil, cerrarSesion } = useAuth();
  const dialogo = useRef(null);
  const intentado = useRef(null); // uid cuyo nombre elegido ya se ha intentado reclamar
  const [pedir, setPedir] = useState(false);
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const id = useId();
  // Sin nombre de verdad: si GET /me/perfil falló (error) no se pide, para no pisar un perfil que sí existe
  const falta = Boolean(usuario) && miPerfil?.usuario === null && !miPerfil.error;
  const abierto = pedir && falta;
  const comprobacion = useDisponibilidad(abierto ? nombre : "");

  useEffect(() => {
    if (miPerfil?.usuario) guardarElegido(""); // ya tiene nombre: lo guardado en este navegador sobra
    if (!falta || intentado.current === usuario.id) return;
    intentado.current = usuario.id;
    const elegido = (leerElegido() || usuario.user_metadata?.usuario || "").trim();
    guardarElegido("");
    const preguntar = (mensaje = "") => {
      setNombre(elegido);
      setError(mensaje);
      setPedir(true);
    };
    if (!elegido || motivoFormato(elegido)) return preguntar();
    guardarPerfil({ usuario: elegido })
      .then(setMiPerfil)
      .catch((err) => preguntar(err.status === 409 ? `«${elegido}» ya no está libre. Elige otro.` : err.message));
  }, [falta, miPerfil, usuario, setMiPerfil]);

  useEffect(() => {
    if (abierto && !dialogo.current?.open) dialogo.current?.showModal();
  }, [abierto]);

  if (!abierto) return null;

  const enviar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError("");
    try {
      setMiPerfil(await guardarPerfil({ usuario: nombre.trim() }));
      setPedir(false);
    } catch (err) {
      setError(err.status === 409 ? "Ese nombre de usuario ya no está libre. Elige otro." : err.message);
    } finally {
      setGuardando(false);
    }
  };

  // Obligatorio: Esc no lo cierra (y si el navegador lo cierra igualmente, se vuelve a abrir). La salida es cerrar sesión.
  return (
    <dialog
      ref={dialogo} aria-labelledby={`${id}-titulo`} aria-describedby={`${id}-texto`}
      onCancel={(e) => e.preventDefault()} onClose={() => dialogo.current?.showModal()}
      className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl border border-line bg-background text-foreground p-0 backdrop:bg-black/40"
    >
      <form onSubmit={enviar} className="p-6 space-y-4 text-left">
        <h2 id={`${id}-titulo`} className="text-xl font-display font-bold uppercase">Elige tu nombre de usuario</h2>
        <p id={`${id}-texto`} className="text-sm text-muted">
          Es tu dirección en FPS24 (fps24.es/u/tu-nombre) y con él te encuentran tus amigos. Podrás cambiarlo en «Editar mi perfil».
        </p>
        <CampoUsuario id={id} valor={nombre} onCambiar={setNombre} comprobacion={comprobacion} required />
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button type="submit" disabled={guardando || comprobacion.estado === "no"} className={BOTON}>
          {guardando ? "Guardando…" : "Continuar"}
        </button>
        <p className="text-xs text-muted text-center">
          <button type="button" onClick={cerrarSesion} className="underline hover:text-primary">Cerrar sesión</button>
        </p>
      </form>
    </dialog>
  );
}
