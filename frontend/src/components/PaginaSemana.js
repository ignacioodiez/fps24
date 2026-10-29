import Link from "next/link";
import TodayHeader from "@/components/TodayHeader";
import { CeldaMosaico, Tarjeta } from "@/components/TarjetasSemana";
import SelectorSemanas from "@/components/SelectorSemanas";
import TarjetaSinSesiones from "@/components/TarjetaSinSesiones";
import { clasesMosaico } from "@/lib/mosaico";
import { comoUTC, formato } from "@/lib/fechasMadrid";

// Última semana de cada página (la API rechaza las siguientes): /estrenos llega a la 8 con los estrenos de TMDB
const SEMANAS_MAX = { estrenos: 8, especiales: 3 };

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

// "lun 19 – dom 25 oct" o, si cambia de mes, "lun 26 oct – dom 1 nov"
const rango = (desde, hasta) => {
  const dia = (f) => `${formato(f, { weekday: "short" })} ${comoUTC(f).getUTCDate()}`;
  const mes = (f) => formato(f, { month: "short" });
  return mes(desde) === mes(hasta)
    ? `${dia(desde)} – ${dia(hasta)} ${mes(hasta)}`
    : `${dia(desde)} ${mes(desde)} – ${dia(hasta)} ${mes(hasta)}`;
};

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
  const semana = Number.isInteger(pedida) && pedida >= 0 && pedida <= SEMANAS_MAX[tipo] ? pedida : 0;
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
            {tipo === "estrenos" && <SelectorSemanas semana={semana} desde={datos.desde} maxima={SEMANAS_MAX.estrenos} />}

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
                {datos.peliculas.map((item, i, lista) => item.sin_sesiones ? (
                  <TarjetaSinSesiones key={`tmdb-${item.pelicula.tmdb_id}`} item={item} />
                ) : (
                  <Tarjeta key={item.pelicula.id} item={item} tipo={tipo} destacada={i < (lista.length === 2 ? 1 : 2)} />
                ))}
              </ul>
            )}
            {datos.peliculas.some((item) => item.sin_sesiones) && (
              <p className="mt-6 text-xs text-muted">
                Los estrenos aún sin sesiones en Madrid, con su fecha, póster y sinopsis, vienen de{" "}
                <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">TMDB</a>.
                Las fechas pueden cambiar; «fecha prevista» indica que la de España aún no es firme.
              </p>
            )}
          </>
        ) : (
          <p className="text-center text-muted py-16">No se ha podido cargar la cartelera. Vuelve a intentarlo en unos minutos.</p>
        )}
      </div>
    </main>
  );
}
