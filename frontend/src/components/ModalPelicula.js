"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import LiteYouTubeEmbed from "react-lite-youtube-embed";
import "react-lite-youtube-embed/dist/LiteYouTubeEmbed.css";
import { SelectorAgrupacion, SesionesPorDias, claveDia, useAgrupacion } from "@/components/Sesiones";
import { ChipDato, ChipsGeneros, LineaDireccion, NotaPelicula, duracionTexto } from "@/components/FichaPelicula";
import { diaGuardado } from "@/lib/diaSeleccionado";

const DURACION_ANIMACION = 200; // ms, igual que duration-200
const ENFOCABLES = 'a[href], button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])';

// El backdrop se guarda en tamaño "original" (varios MB): para el modal basta w1280
const backdropDe = (url) => url?.replace("/t/p/original/", "/t/p/w1280/");

function Contenido({ movie, idTitulo }) {
  const [verTrailer, setVerTrailer] = useState(false);
  const [modo, setModo] = useAgrupacion();
  const elegido = claveDia(diaGuardado() || new Date());

  return (
    <>
      {/* Cabecera: backdrop (o fondo violeta suave) y póster superpuesto */}
      <div className="relative h-44 md:h-64 bg-primary-soft shrink-0">
        {movie.backdrop_url && (
          <img src={backdropDe(movie.backdrop_url)} alt="" className="absolute inset-0 w-full h-full object-cover" />
        )}
        <div className="absolute inset-0 bg-linear-to-t from-background via-background/20 to-transparent" />
      </div>

      <div className="px-5 md:px-8 pb-8 -mt-20 md:-mt-24 relative">
        <div className="flex gap-4 md:gap-6 items-end">
          <div className="w-24 md:w-36 aspect-[2/3] shrink-0 rounded-2xl overflow-hidden border border-line bg-surface flex items-center justify-center">
            {movie.poster_url ? (
              <img src={movie.poster_url} alt={movie.titulo} className="w-full h-full object-cover" />
            ) : (
              <span className="p-2 text-center text-xs font-display font-bold text-muted">{movie.titulo}</span>
            )}
          </div>
          <div className="min-w-0 pb-1">
            <h2 id={idTitulo} className="text-2xl md:text-3xl font-display font-bold uppercase leading-tight text-foreground">{movie.titulo}</h2>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {movie.anio && <ChipDato>{movie.anio}</ChipDato>}
              {movie.duracion > 0 && <ChipDato>{duracionTexto(movie.duracion)}</ChipDato>}
              <NotaPelicula nota={movie.nota_tmdb} votos={movie.votos} />
            </div>
          </div>
        </div>

        <ChipsGeneros generos={movie.generos} className="mt-4" />
        <LineaDireccion director={movie.director} className="mt-3" />
        <p className="mt-3 text-foreground leading-relaxed">{movie.sinopsis || "No hay sinopsis disponible."}</p>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          {movie.youtube_id && (
            <button type="button" onClick={() => setVerTrailer((v) => !v)} aria-expanded={verTrailer}
                    className="px-4 py-2 rounded-full bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity">
              {verTrailer ? "Ocultar tráiler" : "▶ Ver tráiler"}
            </button>
          )}
          {/* <a> y no <Link>: carga la página completa en vez de volver a abrir el modal */}
          <a href={`/pelicula/${movie.id}`} className="px-4 py-2 rounded-full border border-line text-sm font-bold text-foreground hover:border-primary hover:text-primary transition-colors">
            Ver página completa
          </a>
        </div>
        {verTrailer && (
          <div className="mt-4 rounded-xl overflow-hidden border border-line">
            <LiteYouTubeEmbed id={movie.youtube_id} title={`Tráiler de ${movie.titulo}`} poster="hqdefault" noCookie />
          </div>
        )}

        <div className="mt-8 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-bold uppercase tracking-wider text-muted">Sesiones</p>
            <SelectorAgrupacion modo={modo} onCambiar={setModo} />
          </div>
          <SesionesPorDias pases={movie.pases || []} modo={modo} contexto="modal" diaElegido={elegido} />
        </div>
      </div>
    </>
  );
}

// Vista rápida de una película sobre la portada. Cerrar = volver atrás en el historial (la URL vuelve a "/").
export default function ModalPelicula({ id }) {
  const router = useRouter();
  const panel = useRef(null);
  const cerrando = useRef(false);
  const [abierto, setAbierto] = useState(false);
  const [movie, setMovie] = useState(null);
  const [fallo, setFallo] = useState(false);
  const idTitulo = `modal-pelicula-${id}`;

  const cerrar = useCallback(() => {
    if (cerrando.current) return;
    cerrando.current = true;
    setAbierto(false);
    setTimeout(() => router.back(), DURACION_ANIMACION);
  }, [router]);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/pelicula/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setMovie)
      .catch((err) => {
        console.error("Error loading movie:", err);
        setFallo(true);
      });
  }, [id]);

  // Animación de entrada, bloqueo del scroll del fondo y foco: al abrir, en el panel; al cerrar, de vuelta a la tarjeta
  useEffect(() => {
    const origen = document.activeElement;
    const overflowPrevio = document.body.style.overflow;
    const gutterPrevio = document.documentElement.style.scrollbarGutter;
    // Se bloquea el scroll sin tocar su posición; el hueco de la barra se reserva para que la portada no se mueva
    document.documentElement.style.scrollbarGutter = "stable";
    document.body.style.overflow = "hidden";
    const frame = requestAnimationFrame(() => setAbierto(true));
    panel.current?.focus({ preventScroll: true });
    return () => {
      cancelAnimationFrame(frame);
      document.body.style.overflow = overflowPrevio;
      document.documentElement.style.scrollbarGutter = gutterPrevio;
      if (origen instanceof HTMLElement && document.contains(origen)) origen.focus({ preventScroll: true });
    };
  }, []);

  // Esc cierra; Tab no sale del panel
  useEffect(() => {
    const alPulsar = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        cerrar();
      } else if (e.key === "Tab" && panel.current) {
        const enfocables = [...panel.current.querySelectorAll(ENFOCABLES)];
        if (enfocables.length === 0) return e.preventDefault();
        const [primero, ultimo] = [enfocables[0], enfocables[enfocables.length - 1]];
        if (e.shiftKey && (document.activeElement === primero || document.activeElement === panel.current)) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && document.activeElement === ultimo) {
          e.preventDefault();
          primero.focus();
        }
      }
    };
    document.addEventListener("keydown", alPulsar);
    return () => document.removeEventListener("keydown", alPulsar);
  }, [cerrar]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-end md:items-center justify-center md:p-6 bg-black/50 backdrop-blur-sm motion-safe:transition-opacity duration-200 ${abierto ? "opacity-100" : "opacity-0"}`}
      onClick={(e) => e.target === e.currentTarget && cerrar()}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        className={`relative w-full md:max-w-3xl h-[92dvh] md:h-auto md:max-h-[90vh] overflow-y-auto overscroll-contain bg-background rounded-t-3xl md:rounded-3xl outline-none
          motion-safe:transition-all duration-200 ease-out
          ${abierto ? "translate-y-0 md:scale-100 opacity-100" : "translate-y-full md:translate-y-0 md:scale-95 md:opacity-0"}`}
      >
        {/* Asa de la hoja en móvil */}
        <div className="md:hidden absolute top-2 left-1/2 -translate-x-1/2 w-10 h-1 rounded-full bg-white/80 z-10" aria-hidden="true" />
        <button type="button" onClick={cerrar} aria-label="Cerrar"
                className="absolute top-3 right-3 z-10 w-9 h-9 rounded-full bg-background/90 border border-line text-foreground flex items-center justify-center hover:border-primary hover:text-primary transition-colors">
          <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>

        {movie ? (
          <Contenido movie={movie} idTitulo={idTitulo} />
        ) : fallo ? (
          <div className="p-10 text-center">
            <h2 id={idTitulo} className="text-lg font-bold text-foreground">No se pudo cargar la película</h2>
            <a href={`/pelicula/${id}`} className="mt-3 inline-block text-primary font-semibold">Abrir la página completa</a>
          </div>
        ) : (
          <div aria-busy="true">
            <h2 id={idTitulo} className="sr-only">Cargando película</h2>
            <div className="h-44 md:h-64 bg-surface animate-pulse" />
            <div className="p-6 space-y-3">
              <div className="h-8 w-2/3 rounded bg-surface animate-pulse" />
              <div className="h-4 w-1/3 rounded bg-surface animate-pulse" />
              <div className="h-20 rounded bg-surface animate-pulse" />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
