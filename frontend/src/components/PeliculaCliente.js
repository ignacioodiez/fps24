"use client";

import LiteYouTubeEmbed from "react-lite-youtube-embed";
import "react-lite-youtube-embed/dist/LiteYouTubeEmbed.css";
import { SelectorAgrupacion, SesionesPorDias, diaConSesiones, useAgrupacion } from "@/components/Sesiones";

// Partes interactivas de la página de película (app/pelicula/[id]), que se pinta en el servidor

export function Trailer({ id, titulo }) {
  return <LiteYouTubeEmbed id={id} title={`Tráiler de ${titulo}`} poster="maxresdefault" webp={true} />;
}

// Sesiones "Por cine" (por defecto) o "Por hora"; se recuerda en localStorage (igual que en la vista rápida)
export function SesionesPelicula({ movie, dia }) {
  const [modo, setModo] = useAgrupacion();
  return (
    <>
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 border-b border-line pb-4 gap-4">
        <h2 className="text-2xl font-bold font-display text-foreground flex items-center gap-2">
          Próximas Sesiones
        </h2>
        <SelectorAgrupacion modo={modo} onCambiar={setModo} />
      </div>
      {/* Primer día con sesiones abierto y "Otros días" plegados, con los límites de la página completa */}
      <SesionesPorDias pases={movie.pases} pelicula={movie} modo={modo} contexto="pagina" diaElegido={diaConSesiones(dia, movie.pases)} />
    </>
  );
}
