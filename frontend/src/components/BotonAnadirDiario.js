"use client";

import { useEffect, useId, useRef, useState } from "react";
import BuscadorPeliculas from "@/components/BuscadorPeliculas";
import DialogoDiario from "@/components/DialogoDiario";
import { DIARIO_GUARDADO, hoyMadrid } from "@/lib/diario";

// Botón morado de la barra (también "Crear cuenta" en NavSecciones)
export const BOTON_BARRA = "self-center flex items-center justify-center gap-1.5 min-h-11 min-w-11 lg:min-h-9 mx-1 px-3 bg-primary text-white text-sm font-bold hover:opacity-90 active:opacity-75 transition-opacity focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";

// Diálogo con el buscador; se monta abierto. Al elegir se cierra y el padre abre DialogoDiario.
function DialogoBuscar({ onElegir, onCerrar }) {
  const dialogo = useRef(null);
  const id = useId();

  useEffect(() => {
    dialogo.current?.showModal();
    dialogo.current?.querySelector("input")?.focus();
  }, []);

  const cerrar = () => dialogo.current?.close();

  return (
    <dialog
      ref={dialogo} aria-labelledby={`${id}-titulo`} onClose={onCerrar}
      onClick={(e) => e.target === e.currentTarget && cerrar()}
      className="mx-auto mt-[10dvh] w-[calc(100%-2rem)] max-w-lg h-[min(32rem,80dvh)] border border-line bg-background text-foreground p-0 backdrop:bg-black/40"
    >
      <div className="p-5 md:p-6 space-y-4 text-left">
        <div className="flex items-start justify-between gap-4">
          <h2 id={`${id}-titulo`} className="text-xl font-display font-bold uppercase">Añadir al diario</h2>
          <button type="button" onClick={cerrar} aria-label="Cerrar" className="text-muted hover:text-primary text-xl leading-none">×</button>
        </div>
        <BuscadorPeliculas onElegir={(pelicula) => { onElegir(pelicula); cerrar(); }} />
      </div>
    </dialog>
  );
}

// "+" de la barra (solo con sesión): buscar una película y apuntarla. Avisa con DIARIO_GUARDADO para que
// la lista de mi diario, si está en pantalla, la añada.
export default function BotonAnadirDiario() {
  const [paso, setPaso] = useState(null); // null | "buscar" | película elegida
  const [aviso, setAviso] = useState("");
  const elegida = useRef(null);

  // El aviso se ve unos segundos y se va (para lectores de pantalla basta con que se anuncie)
  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(""), 4000);
    return () => clearTimeout(t);
  }, [aviso]);

  return (
    <>
      <button
        type="button" onClick={() => { setAviso(""); setPaso("buscar"); }} aria-haspopup="dialog"
        aria-label="Añadir a Mi Diario" title="Añadir a Mi Diario"
        className={BOTON_BARRA}
      >
        <span aria-hidden="true" className="text-xl leading-none">+</span>
        {/* Por debajo de lg no cabe junto a "Mi perfil" y "Cerrar sesión": solo el "+" (y el aria-label) */}
        <span aria-hidden="true" className="hidden lg:inline">Añadir a Mi Diario</span>
      </button>
      <p role="status" aria-live="polite" className={aviso ? "fixed z-50 bottom-4 left-1/2 -translate-x-1/2 w-max max-w-[calc(100%-2rem)] bg-primary px-4 py-2 text-sm font-bold text-white shadow-lg" : "sr-only"}>
        {aviso}
      </p>

      {paso === "buscar" && (
        <DialogoBuscar onElegir={(p) => (elegida.current = p)} onCerrar={() => setPaso(elegida.current)} />
      )}
      {paso && paso !== "buscar" && (
        <DialogoDiario
          pelicula={paso} fechaInicial={hoyMadrid()}
          onCerrar={() => { elegida.current = null; setPaso(null); }}
          onGuardado={(guardada) => {
            setAviso(`«${guardada.pelicula.titulo}» añadida a tu diario`);
            window.dispatchEvent(new CustomEvent(DIARIO_GUARDADO, { detail: guardada }));
          }}
        />
      )}
    </>
  );
}
