import Link from "next/link";
import TodayHeader from "@/components/TodayHeader";
import { imagenDe } from "@/components/TarjetaEspecial";
import { clasesMosaico } from "@/lib/mosaico";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const VOTOS_MIN = 10;

// Mismo patrón que /cines: caché de 5 min. Next solo guarda las respuestas 200, así que un fallo no se queda
async function leerSemana(ruta, semana) {
  try {
    const res = await fetch(`${API}/${ruta}?semana=${semana}`, { next: { revalidate: 300 } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Error loading ${ruta}:`, err);
    return null;
  }
}

// Las fechas de la API son de Madrid sin zona: se leen y se escriben en UTC para que el huso del servidor no las mueva
const comoUTC = (texto) => new Date(texto.length === 10 ? `${texto}T00:00Z` : `${texto}Z`);
const formato = (texto, opciones) =>
  comoUTC(texto).toLocaleString("es-ES", { timeZone: "UTC", ...opciones }).replace(".", "");

// "lun 19 – dom 25 oct" o, si cambia de mes, "lun 26 oct – dom 1 nov"
const rango = (desde, hasta) => {
  const dia = (f) => `${formato(f, { weekday: "short" })} ${comoUTC(f).getUTCDate()}`;
  const mes = (f) => formato(f, { month: "short" });
  return mes(desde) === mes(hasta)
    ? `${dia(desde)} – ${dia(hasta)} ${mes(hasta)}`
    : `${dia(desde)} ${mes(desde)} – ${dia(hasta)} ${mes(hasta)}`;
};

// "sáb 24 · 17:30"
const sesionCorta = (fechaHora) =>
  `${formato(fechaHora, { weekday: "short" })} ${comoUTC(fechaHora).getUTCDate()} · ${formato(fechaHora, { hour: "2-digit", minute: "2-digit" })}`;

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
function Tarjeta({ item, tipo, destacada = false }) {
  const { pelicula, n_sesiones, n_cines, sesion } = item;
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
              {tipo === "estrenos" ? "Primera: " : ""}{sesionCorta(sesion.fecha_hora)}
            </p>
            <p className="text-xs text-muted truncate" title={sesion.cine}>{sesion.cine}</p>
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
function CeldaMosaico({ item, grande, className }) {
  const { pelicula, n_sesiones, n_cines, sesion } = item;
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
          <span className="flex-[1_1_6rem] min-w-0 truncate" title={sesion.cine}>{sesion.cine}</span>
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

function Flecha({ semana, activa, children, etiqueta }) {
  const clase = "flex items-center justify-center w-11 h-11 rounded-full border text-lg font-bold transition-colors";
  if (!activa) {
    return <span aria-disabled="true" aria-label={etiqueta} className={`${clase} border-line text-line cursor-not-allowed`}>{children}</span>;
  }
  return (
    <Link href={`?semana=${semana}`} aria-label={etiqueta}
          className={`${clase} border-line text-foreground hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary`}>
      {children}
    </Link>
  );
}

// Página de /estrenos o /especiales (tipo = ruta de la API): una semana, con flechas a la anterior y la siguiente
export default async function PaginaSemana({ tipo, titulo, acento, intro, vacio, searchParams }) {
  const pedida = Number((await searchParams).semana);
  const semana = Number.isInteger(pedida) && pedida >= 0 && pedida <= 3 ? pedida : 0;
  const datos = await leerSemana(tipo, semana);

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />

      <div className="max-w-9xl mx-auto px-4 md:px-8">
        <div className="mb-6">
          <h2 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground">
            {titulo} <span className={acento}>de la semana</span>
          </h2>
          <p className="mt-2 text-muted md:text-lg max-w-2xl">{intro}</p>
        </div>

        {datos ? (
          <>
            <nav aria-label="Semanas" className="flex items-center gap-3 mb-6">
              <Flecha semana={semana - 1} activa={datos.hay_anterior} etiqueta="Semana anterior">←</Flecha>
              <p className="text-sm md:text-base font-bold uppercase tracking-wider text-foreground" aria-live="polite">
                {semana === 0 ? "Esta semana · " : ""}{rango(datos.desde, datos.hasta)}
              </p>
              <Flecha semana={semana + 1} activa={datos.hay_siguiente} etiqueta="Semana siguiente">→</Flecha>
            </nav>

            {datos.peliculas.length === 0 ? (
              <p className="text-center text-muted py-16">{vacio}</p>
            ) : tipo === "especiales" ? (
              <ul className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 grid-flow-row-dense auto-rows-[150px] md:auto-rows-[170px] lg:auto-rows-[190px] xl:auto-rows-[220px] gap-3 md:gap-4">
                {clasesMosaico(datos.peliculas.length).map((clases, i) => (
                  <CeldaMosaico key={datos.peliculas[i].pelicula.id} item={datos.peliculas[i]} grande={i === 0} className={clases} />
                ))}
              </ul>
            ) : (
              // dense: los huecos que dejan las 2 destacadas (2 columnas) los rellenan las siguientes. Con solo 2,
              // una: dos destacadas en 3 columnas dejarían la tercera vacía en ambas filas
              <ul className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 grid-flow-row-dense gap-3 md:gap-5">
                {datos.peliculas.map((item, i, lista) => (
                  <Tarjeta key={item.pelicula.id} item={item} tipo={tipo} destacada={i < (lista.length === 2 ? 1 : 2)} />
                ))}
              </ul>
            )}
          </>
        ) : (
          <p className="text-center text-muted py-16">No se ha podido cargar la cartelera. Vuelve a intentarlo en unos minutos.</p>
        )}
      </div>
    </main>
  );
}
