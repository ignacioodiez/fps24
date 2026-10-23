"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";

const PILDORA = "flex items-center gap-2 px-5 py-2 rounded-full border border-line bg-background text-foreground hover:border-primary hover:text-primary transition-colors text-sm font-bold uppercase tracking-wide";

function mensajeError(error) {
  if (error?.status === 429 || /rate limit/i.test(error?.message)) {
    return "Demasiados intentos. Espera unos minutos y vuelve a probar.";
  }
  if (error?.code === "email_address_invalid" || /email.*invalid/i.test(error?.message)) {
    return "Ese email no parece válido. Revísalo.";
  }
  return "No hemos podido enviar el enlace. Inténtalo de nuevo.";
}

// Botón "Iniciar sesión" de la cabecera: magic link por email (Supabase Auth). Sin variables de Supabase no se pinta.
export default function BotonEntrar() {
  const { usuario, cargando, entrar, salir } = useAuth();
  const dialogo = useRef(null);
  const [estado, setEstado] = useState("inicio"); // inicio | enviando | enviado
  const [error, setError] = useState("");

  if (!AUTH_DISPONIBLE || cargando) return null;

  if (usuario) {
    return (
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-sm font-bold text-foreground bg-background rounded-full px-3 py-2 truncate max-w-[10rem]" title={usuario.email}>
          {usuario.email?.split("@")[0]}
        </span>
        <button type="button" onClick={salir} className={PILDORA}>Cerrar sesión</button>
      </div>
    );
  }

  const enviar = async (e) => {
    e.preventDefault();
    setError("");
    setEstado("enviando");
    try {
      await entrar(new FormData(e.currentTarget).get("email").trim());
      setEstado("enviado");
    } catch (err) {
      setError(mensajeError(err));
      setEstado("inicio");
    }
  };

  // autoFocus de React no sirve en un <dialog> cerrado: se enfoca el email al abrir
  const abrir = () => {
    dialogo.current?.showModal();
    dialogo.current?.querySelector("input")?.focus();
  };
  const cerrar = () => dialogo.current?.close();

  return (
    <>
      <button type="button" onClick={abrir} aria-haspopup="dialog" className={PILDORA}>
        Iniciar sesión
      </button>

      {/* <dialog> nativo: Esc cierra, el foco queda dentro y vuelve al botón al cerrar */}
      <dialog
        ref={dialogo}
        aria-labelledby="titulo-entrar"
        onClose={() => { setEstado("inicio"); setError(""); }}
        onClick={(e) => e.target === e.currentTarget && cerrar()}
        className="m-auto w-[calc(100%-2rem)] max-w-sm rounded-2xl border border-line bg-background text-foreground p-0 backdrop:bg-black/40"
      >
        <div className="p-6 text-left">
          <div className="flex items-start justify-between gap-4">
            <h2 id="titulo-entrar" className="text-xl font-display font-bold uppercase">Iniciar sesión</h2>
            <button type="button" onClick={cerrar} aria-label="Cerrar" className="text-muted hover:text-primary text-xl leading-none">×</button>
          </div>

          {estado === "enviado" ? (
            <p role="status" className="mt-4 text-foreground leading-relaxed">
              Te hemos enviado un enlace a tu email. Ábrelo en este mismo navegador.
            </p>
          ) : (
            <form onSubmit={enviar} className="mt-4 space-y-3">
              <p className="text-sm text-muted">Sin contraseñas: te mandamos un enlace para iniciar sesión.</p>
              <label htmlFor="email-entrar" className="block text-xs font-bold uppercase tracking-wider text-muted">Email</label>
              <input
                id="email-entrar" name="email" type="email" required autoComplete="email"
                aria-invalid={Boolean(error)} aria-describedby={error ? "error-entrar" : undefined}
                className="w-full rounded-xl border border-line bg-background px-4 py-2 text-foreground focus:border-primary focus:outline-none"
              />
              {error && <p id="error-entrar" role="alert" className="text-sm text-red-600">{error}</p>}
              <button type="submit" disabled={estado === "enviando"}
                      className="w-full px-4 py-2 rounded-full bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-60">
                {estado === "enviando" ? "Enviando…" : "Enviarme el enlace"}
              </button>
              <p className="text-xs text-muted text-center">
                Al continuar aceptas la{" "}
                <Link href="/privacidad" onClick={cerrar} className="underline hover:text-primary">política de privacidad</Link>
              </p>
            </form>
          )}
        </div>
      </dialog>
    </>
  );
}
