"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/AuthProvider";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import { diaCompleto } from "@/lib/fechasMadrid";
import { cleanCinemaName } from "@/utils/helpers";

const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);

// Versión con el estilo neutro de ChipIdioma (Sesiones.js), pero también para el castellano: aquí es un dato más
function Version({ idioma }) {
  if (idioma === "VOSE") {
    return <span className="text-[10px] leading-none px-1 py-0.5 rounded border border-muted bg-background text-foreground font-bold uppercase tracking-wide">VOSE</span>;
  }
  return <span className="text-[11px] bg-surface px-1.5 py-0.5 rounded font-medium text-muted border border-line">{!idioma || idioma === "Español" ? "Castellano" : idioma}</span>;
}

// Detalle de una sesión al pulsar su hora: comprar (el enlace de siempre) o guardarla en "Mis sesiones".
// <dialog> nativo en modo modal (foco dentro, Esc cierra); en móvil, hoja desde abajo. Se monta abierto.
// fecha_hora llega en hora de Madrid sin zona: día y hora se leen del texto, sin pasar por el huso del navegador.
export default function ModalSesion({ sesion, origen, guardada, onAlternar, onCerrar }) {
  const { usuario, abrirLogin } = useAuth();
  const dialogo = useRef(null);
  const idTitulo = useId();
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");
  const { pelicula = {}, cine_slug: slug } = sesion;
  const dia = capitalizar(diaCompleto(sesion.fecha_hora.slice(0, 10)));
  const hora = sesion.fecha_hora.slice(11, 16);
  const precio = sesion.precio && sesion.precio !== "Consultar" ? sesion.precio : null;
  const cine = cleanCinemaName(sesion.cine);

  // Abrir, bloquear el scroll del fondo y, al desmontar, devolver el foco a la hora que lo abrió
  // (en Safari un clic no enfoca el botón: no basta con lo que hace el <dialog>)
  useEffect(() => {
    const overflowPrevio = document.body.style.overflow;
    const gutterPrevio = document.documentElement.style.scrollbarGutter;
    document.documentElement.style.scrollbarGutter = "stable";
    document.body.style.overflow = "hidden";
    dialogo.current?.showModal();
    return () => {
      document.body.style.overflow = overflowPrevio;
      document.documentElement.style.scrollbarGutter = gutterPrevio;
      if (origen instanceof HTMLElement && document.contains(origen)) origen.focus({ preventScroll: true });
    };
  }, [origen]);

  const cerrar = () => dialogo.current?.close();

  const alternar = async () => {
    if (!usuario) return abrirLogin("Inicia sesión para guardar esta sesión en tu agenda («Mis sesiones»)");
    setOcupado(true);
    setAviso("");
    try {
      await onAlternar(sesion.id);
      setAviso(guardada ? "Quitada de «Mis sesiones»" : "Guardada en «Mis sesiones»");
    } catch (err) {
      setAviso(err.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <dialog
      ref={dialogo}
      aria-labelledby={idTitulo}
      aria-modal="true"
      onClose={onCerrar}
      onClick={(e) => e.target === e.currentTarget && cerrar()}
      className="w-full max-w-none max-h-[90dvh] mx-0 mt-auto mb-0 md:m-auto md:w-[calc(100%-2rem)] md:max-w-md overflow-y-auto overscroll-contain
                 rounded-t-2xl md:rounded-2xl border border-line max-md:border-b-0 bg-background text-foreground p-0 backdrop:bg-black/50
                 motion-safe:transition-transform motion-safe:duration-200 max-md:starting:translate-y-full"
    >
      <div className="p-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] text-left">
        <div className="flex gap-4">
          <div className="w-16 aspect-[2/3] shrink-0 rounded-lg overflow-hidden border border-line bg-surface">
            {pelicula.poster_url && <img src={pelicula.poster_url} alt="" className="w-full h-full object-cover" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-3">
              <h2 id={idTitulo} className="text-lg font-display font-bold uppercase leading-tight break-words">
                {pelicula.id ? (
                  <Link href={`/pelicula/${pelicula.id}`} onClick={cerrar} className="hover:text-primary focus-visible:outline-2 focus-visible:outline-primary rounded">
                    {pelicula.titulo}
                  </Link>
                ) : pelicula.titulo}
              </h2>
              <button type="button" onClick={cerrar} aria-label="Cerrar" className="-mt-1 text-muted hover:text-primary text-2xl leading-none">×</button>
            </div>
            <p className="mt-1 text-sm font-bold uppercase tracking-wide break-words">
              {slug ? <Link href={`/cines/${slug}`} onClick={cerrar} className="hover:text-primary hover:underline">{cine}</Link> : cine}
            </p>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-muted">Día</dt>
          <dd className="text-foreground font-semibold">{dia}</dd>
          <dt className="text-muted">Hora</dt>
          <dd className="text-foreground font-semibold"><time dateTime={sesion.fecha_hora}>{hora}</time></dd>
          <dt className="text-muted">Versión</dt>
          <dd><Version idioma={sesion.idioma} /></dd>
          {precio && (
            <>
              <dt className="text-muted">Precio</dt>
              <dd className="text-foreground font-semibold">{precio}</dd>
            </>
          )}
        </dl>

        <div className="mt-5 flex flex-col sm:flex-row gap-2">
          {sesion.link_compra && (
            <a href={sesion.link_compra} target="_blank" rel="noopener noreferrer" className={`${BOTON_PRIMARIO} rounded-lg text-center flex-1`}>
              Comprar entradas<span className="sr-only"> (se abre en una pestaña nueva)</span>
            </a>
          )}
          {sesion.id != null && (
            <button type="button" onClick={alternar} disabled={ocupado}
                    className={`${BOTON_SECUNDARIO} rounded-lg flex-1 ${guardada ? "border-foreground" : ""}`}>
              {ocupado ? "Un momento…" : guardada ? "Guardada ✓" : "Guardar sesión"}
            </button>
          )}
        </div>
        <p role="status" aria-live="polite" className="mt-2 min-h-5 text-sm text-muted">{aviso}</p>
      </div>
    </dialog>
  );
}
