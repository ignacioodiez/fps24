"use client";

import { useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { BloquePrecio, Boton, precioHoy } from "@/components/SalasYPrecios";
import { ChipHora } from "@/components/Sesiones";
import { NotaPelicula } from "@/components/FichaPelicula";

// Leaflet usa window: solo en cliente
const MapaCines = dynamic(() => import("@/components/MapaCines"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-surface" />,
});

// Fechas "YYYY-MM-DD" de la API (Madrid): se formatean en UTC para que el huso del servidor o del navegador no las mueva
const comoUTC = (fecha) => new Date(`${fecha}T00:00Z`);
const formato = (fecha, opciones) => comoUTC(fecha).toLocaleDateString("es-ES", { timeZone: "UTC", ...opciones });
const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);
const plural = (n, una, varias) => `${n} ${n === 1 ? una : varias}`;

// Selector de día: radiogroup con foco itinerante (Tab entra en el elegido; flechas, Inicio y Fin se mueven por
// los días con sesiones)
function SelectorDia({ dias, elegido, onElegir }) {
  const botones = useRef([]);
  const conSesiones = dias.map((d, i) => (d.peliculas.length ? i : null)).filter((i) => i != null);

  const tecla = (e) => {
    const pos = conSesiones.indexOf(dias.findIndex((d) => d.fecha === elegido));
    const destino = {
      ArrowRight: conSesiones[pos + 1], ArrowDown: conSesiones[pos + 1],
      ArrowLeft: conSesiones[pos - 1], ArrowUp: conSesiones[pos - 1],
      Home: conSesiones[0], End: conSesiones.at(-1),
    }[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    onElegir(dias[destino].fecha);
    botones.current[destino]?.focus();
  };

  return (
    <div role="radiogroup" aria-label="Día" onKeyDown={tecla} className="grid grid-cols-7 gap-1.5 md:gap-2">
      {dias.map((d, i) => {
        const activo = d.fecha === elegido;
        const vacio = d.peliculas.length === 0;
        return (
          <button key={d.fecha} ref={(el) => (botones.current[i] = el)} type="button" role="radio" aria-checked={activo}
                  disabled={vacio} tabIndex={activo ? 0 : -1} onClick={() => onElegir(d.fecha)}
                  aria-label={`${capitalizar(formato(d.fecha, { weekday: "long", day: "numeric", month: "long" }))}${vacio ? ", sin sesiones" : ""}`}
                  className={`flex flex-col items-center py-2 rounded-xl border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                    activo ? "bg-primary text-white border-primary"
                      : vacio ? "bg-surface text-muted border-line opacity-50 cursor-not-allowed"
                        : "bg-background text-foreground border-line hover:border-primary hover:text-primary"}`}>
            <span className="text-[11px] font-semibold uppercase tracking-wide">{i === 0 ? "Hoy" : formato(d.fecha, { weekday: "short" }).replace(".", "")}</span>
            <span className="text-lg font-display font-bold leading-tight">{comoUTC(d.fecha).getUTCDate()}</span>
          </button>
        );
      })}
    </div>
  );
}

// Película del día: la tarjeta abre la vista rápida en ese día (ruta interceptada de @modal); las horas, su sesión
function PeliculaDia({ pelicula, fecha, cine, cineSlug }) {
  const href = `/pelicula/${pelicula.id}?dia=${fecha}`;
  return (
    <li className="relative flex gap-3 md:gap-4 p-3 rounded-2xl border border-line bg-background hover:border-muted transition-colors min-w-0">
      <div className="w-20 md:w-24 aspect-[2/3] shrink-0 rounded-xl overflow-hidden bg-surface flex items-center justify-center">
        {pelicula.poster_url ? (
          <img src={pelicula.poster_url} alt="" loading="lazy" className="w-full h-full object-cover" />
        ) : (
          <span className="p-1 text-center text-[10px] font-display font-bold text-muted">{pelicula.titulo}</span>
        )}
      </div>
      <div className="min-w-0 flex-1 flex flex-col gap-1.5">
        <h3 className="font-display font-bold leading-tight text-foreground text-base md:text-lg line-clamp-2">{pelicula.titulo}</h3>
        {pelicula.director && <p className="text-xs text-muted truncate">de {pelicula.director}</p>}
        <div className="empty:hidden"><NotaPelicula nota={pelicula.nota_tmdb} votos={pelicula.votos} /></div>
        <div className="relative z-[2] mt-auto pt-1 flex flex-wrap gap-2">
          {pelicula.sesiones.map((s) => <ChipHora key={s.id} pase={s} cine={cine} cineSlug={cineSlug} pelicula={pelicula} conSala />)}
        </div>
      </div>
      <Link href={href} scroll={false} aria-label={`Vista rápida: ${pelicula.titulo}`}
            className="absolute inset-0 z-[1] rounded-2xl focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary" />
    </li>
  );
}

// Parte interactiva de /cines/{slug}: precios, selector de día con sus películas y el mini mapa
export default function CarteleraCine({ cine }) {
  const { dias, solo_hoy: soloHoy } = cine;
  // Por defecto hoy; si hoy ya no tiene nada en los datos, el primer día con sesiones
  const [elegido, setElegido] = useState((dias.find((d) => d.peliculas.length) ?? dias[0]).fecha);
  const dia = dias.find((d) => d.fecha === elegido);
  const hoy = precioHoy(cine.tarifas, capitalizar(formato(dias[0].fecha, { weekday: "long" })));
  const sesiones = dia.peliculas.reduce((n, p) => n + p.sesiones.length, 0);
  const algunDia = dias.some((d) => d.peliculas.length);

  return (
    <div className="space-y-8">
      <section aria-labelledby="titulo-precios">
        <h2 id="titulo-precios" className="text-sm font-bold uppercase tracking-wider text-muted mb-2">Precios</h2>
        <div className="max-w-xl"><BloquePrecio tarifas={cine.tarifas} hoy={hoy} /></div>
      </section>

      <section aria-labelledby="titulo-cartelera" className="space-y-4">
        <h2 id="titulo-cartelera" className="text-2xl md:text-3xl font-display font-bold text-foreground">Cartelera</h2>
        {!algunDia ? (
          <p className="text-muted py-10 text-center rounded-3xl border border-dashed border-line bg-surface">
            No tenemos sesiones de este cine para los próximos 7 días.
          </p>
        ) : (
          <>
            {soloHoy ? (
              <p role="note" className="text-sm text-muted px-3 py-2 rounded-lg bg-surface border border-line w-fit">
                De este cine solo tenemos las sesiones de hoy.
              </p>
            ) : (
              <SelectorDia dias={dias} elegido={elegido} onElegir={setElegido} />
            )}
            <p className="text-sm font-bold uppercase tracking-wider text-primary" aria-live="polite">
              {capitalizar(formato(dia.fecha, { weekday: "long", day: "numeric", month: "long" }))}
              <span className="text-muted font-semibold normal-case tracking-normal"> · {plural(dia.peliculas.length, "película", "películas")} · {plural(sesiones, "sesión", "sesiones")}</span>
            </p>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 md:gap-4">
              {dia.peliculas.map((p) => <PeliculaDia key={p.id} pelicula={p} fecha={dia.fecha} cine={cine.nombre} cineSlug={cine.slug} />)}
            </ul>
          </>
        )}
      </section>

      {cine.lat != null && cine.lng != null && (
        <section aria-labelledby="titulo-mapa">
          <h2 id="titulo-mapa" className="text-sm font-bold uppercase tracking-wider text-muted mb-2">Dónde está</h2>
          <div className="h-64 md:h-80 rounded-3xl overflow-hidden border border-line isolate">
            <MapaCines items={[{ cine, hoy }]} todos={false} activo={cine.id} onPin={() => {}}
                       popup={() => (
                         <div className="space-y-2 min-w-40 [&_p]:m-0">
                           <p className="font-display font-bold uppercase text-sm leading-tight text-foreground">{cine.nombre}</p>
                           {cine.direccion && <p className="text-xs text-muted">{cine.direccion}</p>}
                           <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}`} nueva>Cómo llegar</Boton>
                         </div>
                       )} />
          </div>
        </section>
      )}
    </div>
  );
}
