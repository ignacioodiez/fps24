"use client";

import Link from "next/link";
import { imagenDe } from "@/components/TarjetaEspecial";
import { MarcaFavorito } from "@/components/BotonFavorito";
import { EnlaceCine } from "@/components/Sesiones";
import { useFavoritos } from "@/components/FavoritosProvider";
import { comoUTC, formato, sesionCorta } from "@/lib/fechasMadrid";
import { sesionSugerida } from "@/lib/favoritos";

// Tarjetas de /estrenos y /especiales (PaginaSemana). En el cliente para sugerir la sesión de un cine favorito.

const VOTOS_MIN = 10;

const ESTILOS = {
  estrenos: { borde: "border-line hover:border-muted", etiqueta: "bg-estreno text-foreground" },
  especiales: { borde: "border-primary", etiqueta: "bg-primary-soft text-primary" },
};

const enlaceDe = ({ pelicula, sesion }) => `/pelicula/${pelicula.id}?dia=${sesion.fecha_hora.slice(0, 10)}`; // abre en el día de la sesión
const notaFiableDe = ({ pelicula, sin_nota }) => !sin_nota && pelicula.nota_tmdb != null && (pelicula.votos ?? 0) >= VOTOS_MIN;

function Entradas({ href }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
       className="relative z-[2] shrink-0 rounded-full bg-primary text-white text-xs font-semibold px-3 py-1 hover:opacity-90 transition-opacity focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
      Entradas
    </a>
  );
}

// Capa sobre toda la tarjeta: vista rápida sin mover el scroll (ruta interceptada de @modal)
function VistaRapida({ href, titulo }) {
  return (
    <Link href={href} scroll={false} aria-label={`Vista rápida: ${titulo}`}
          className="absolute inset-0 z-[1] rounded-2xl focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary" />
  );
}

// Tarjeta: póster, título, director, etiqueta, cines/sesiones y la sesión sugerida. Como en la portada,
// la tarjeta abre la vista rápida; el título, la página completa; "Entradas", la compra.
// destacada: ocupa dos columnas, con el fotograma (horizontal: cabe en el alto de la fila) y la sinopsis.
export function Tarjeta({ item, tipo, destacada = false }) {
  const { pelicula, n_sesiones, n_cines } = item;
  const { favoritos } = useFavoritos();
  const sesion = sesionSugerida(item.sesion, item.alternativas, favoritos); // la de un cine favorito, si la hay ese día
  const href = enlaceDe(item);
  const nota = pelicula.nota_tmdb;
  const notaFiable = notaFiableDe(item);
  const estilo = ESTILOS[tipo];

  return (
    <li className={`relative group flex flex-col min-w-0 rounded-2xl overflow-hidden border bg-background transition-colors ${estilo.borde} ${destacada ? "col-span-2" : ""}`}>
      <div className={`relative bg-surface ${destacada ? "aspect-video" : "aspect-[2/3]"}`}>
        {pelicula.poster_url ? (
          <img src={destacada ? imagenDe(pelicula) : pelicula.poster_url} alt={pelicula.titulo} loading="lazy" className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center p-3 text-center">
            <span className="font-display font-bold text-muted leading-tight">{pelicula.titulo}</span>
          </div>
        )}
        {notaFiable && (
          <div className="absolute top-2 left-2 bg-background text-foreground text-xs font-bold px-2 py-1 rounded-lg border border-line">
            ★ {nota.toFixed(1)}
          </div>
        )}
      </div>

      <div className={`flex-1 min-w-0 flex flex-col gap-1.5 p-3 ${destacada ? "md:p-5" : ""}`}>
        <p>
          <span className={`inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${estilo.etiqueta}`}>
            {tipo === "estrenos" ? `Estreno ${formato(pelicula.fecha_estreno, { weekday: "long" })} ${comoUTC(pelicula.fecha_estreno).getUTCDate()}` : "Pase especial"}
          </span>
        </p>
        <h3 className={`font-display font-bold leading-tight text-foreground line-clamp-2 ${destacada ? "text-lg md:text-2xl" : "text-base md:text-lg"}`} title={pelicula.titulo}>
          <a href={href} className="relative z-[2] hover:text-primary transition-colors focus-visible:outline-2 focus-visible:outline-primary rounded">
            {pelicula.titulo}
          </a>
          {pelicula.anio && tipo === "especiales" && <span className="font-sans font-normal text-xs text-muted"> ({pelicula.anio})</span>}
        </h3>
        {pelicula.director && <p className="text-xs text-muted truncate">de {pelicula.director}</p>}
        {!notaFiable && (
          <p className="text-xs text-muted">
            {nota && pelicula.votos ? `★ ${nota.toFixed(1)} · ${pelicula.votos} ${pelicula.votos === 1 ? "voto" : "votos"}` : "Sin valoraciones aún"}
          </p>
        )}
        <p className="text-xs text-muted">
          {n_cines} {n_cines === 1 ? "cine" : "cines"} · {n_sesiones} {n_sesiones === 1 ? "sesión" : "sesiones"}
        </p>
        {destacada && pelicula.sinopsis && (
          <p className="hidden sm:block text-sm text-muted line-clamp-3 lg:line-clamp-4">{pelicula.sinopsis}</p>
        )}
        <div className="mt-auto pt-2 border-t border-line flex flex-wrap items-center gap-x-2 gap-y-1">
          {/* En móvil (2 columnas) el botón baja a su línea para que la sesión y el cine se lean enteros */}
          <div className="min-w-0 flex-1 basis-full sm:basis-auto">
            <p className={`text-xs font-bold uppercase tracking-wide ${tipo === "especiales" ? "text-primary" : "text-foreground"}`}>
              {tipo === "estrenos" && sesion === item.sesion ? "Primera: " : ""}{sesionCorta(sesion.fecha_hora)}
            </p>
            <p className="text-xs text-muted truncate" title={sesion.cine}><EnlaceCine slug={sesion.cine_slug} className="relative z-[2] hover:text-primary hover:underline focus-visible:outline-primary"><MarcaFavorito slug={sesion.cine_slug} /> {sesion.cine}</EnlaceCine></p>
          </div>
          {sesion.link_compra && <Entradas href={sesion.link_compra} />}
        </div>
      </div>
      <VistaRapida href={href} titulo={pelicula.titulo} />
    </li>
  );
}

// Celda del mosaico de /especiales: imagen a sangre con el texto encima. La celda (globals.css, .celda-mosaico)
// elige póster o fotograma según su forma y oculta lo accesorio si es pequeña. grande: la 1ª, con más datos.
export function CeldaMosaico({ item, grande, className }) {
  const { pelicula, n_sesiones, n_cines } = item;
  const { favoritos } = useFavoritos();
  const sesion = sesionSugerida(item.sesion, item.alternativas, favoritos); // la de un cine favorito, si la hay ese día
  const href = enlaceDe(item);
  const horizontal = imagenDe(pelicula);
  const vertical = pelicula.poster_url || horizontal;

  return (
    <li className={`celda-mosaico relative group min-w-0 rounded-2xl overflow-hidden border-2 border-primary bg-primary-soft ${className}`}>
      {vertical ? (
        <>
          <img src={horizontal} alt="" loading="lazy" className="solo-horizontal absolute inset-0 w-full h-full object-cover" />
          <img src={vertical} alt="" loading="lazy" className="solo-vertical absolute inset-0 w-full h-full object-cover object-top" />
        </>
      ) : (
        <span className="absolute inset-0 flex items-center justify-center font-display font-bold text-6xl text-primary" aria-hidden="true">
          {pelicula.titulo?.[0]}
        </span>
      )}
      <div className="absolute inset-0 bg-linear-to-t from-black/90 via-black/40 to-transparent" />
      <VistaRapida href={href} titulo={pelicula.titulo} />
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-1 p-2.5 @md:p-4 text-white">
        <p className="self-start bg-background text-primary text-[11px] @md:text-sm font-bold uppercase tracking-wide px-2 py-0.5 rounded-md">
          {sesionCorta(sesion.fecha_hora)}
        </p>
        <h3 className={`font-display font-bold leading-tight line-clamp-2 ${grande ? "text-lg @md:text-3xl" : "text-sm @[16rem]:text-base"}`} title={pelicula.titulo}>
          <a href={href} className="relative z-[2] hover:underline focus-visible:outline-2 focus-visible:outline-white rounded">{pelicula.titulo}</a>
          {pelicula.anio && <span className="si-hay-sitio font-sans font-normal text-xs text-white/70"> ({pelicula.anio})</span>}
        </h3>
        {pelicula.director && <p className="si-hay-sitio text-xs @md:text-sm text-white/80 truncate">de {pelicula.director}</p>}
        {grande && pelicula.sinopsis && <p className="hidden @md:line-clamp-2 text-sm text-white/80">{pelicula.sinopsis}</p>}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-white/90">
          {notaFiableDe(item) && <span className="shrink-0 font-semibold">★ {pelicula.nota_tmdb.toFixed(1)}</span>}
          {/* Si no caben 6rem, el cine baja a su línea en vez de cortarse en dos letras */}
          <EnlaceCine slug={sesion.cine_slug} title={sesion.cine} className="flex-[1_1_6rem] min-w-0 truncate relative z-[2] hover:underline focus-visible:outline-white"><MarcaFavorito slug={sesion.cine_slug} /> {sesion.cine}</EnlaceCine>
          {sesion.link_compra && <Entradas href={sesion.link_compra} />}
        </div>
        {grande && (
          <p className="si-hay-sitio text-[11px] text-white/70">
            {n_cines} {n_cines === 1 ? "cine" : "cines"} · {n_sesiones} {n_sesiones === 1 ? "sesión" : "sesiones"}
          </p>
        )}
      </div>
    </li>
  );
}
