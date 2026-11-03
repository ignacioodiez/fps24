import Link from "next/link";
import TodayHeader from "@/components/TodayHeader";
import JsonLd, { Migas, SITIO, migas } from "@/components/JsonLd";
import { REJILLA_CINES, SesionesCine } from "@/components/Sesiones";
import { etiquetaRelativa, formato } from "@/lib/fechasMadrid";
import { DIAS_VOSE, MINIMO_SESIONES_VOSE, agruparVose, cinesConMasVose } from "@/lib/vose";

const RUTA = "/cine-vose-madrid";
const NOMBRE = "Cine en VOSE";

// ISR de 5 minutos, como /cines
export const revalidate = 300;

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// fetch con las mismas opciones: Next lo comparte con generateMetadata. Si falla, null (mensaje y noindex)
async function leerVose() {
  try {
    const res = await fetch(`${API}/pases/vose?dias=${DIAS_VOSE}`, { next: { revalidate } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Error loading /pases/vose:", err);
    return null;
  }
}

const ENLACE = "font-semibold text-foreground hover:text-primary underline underline-offset-2";
const plural = (n, una, varias) => `${n} ${n === 1 ? una : varias}`;

export async function generateMetadata() {
  const datos = await leerVose();
  const n = datos?.pases.length ?? 0;
  const title = "Cine en VOSE en Madrid: sesiones en versión original hoy y esta semana | fps24";
  const description = n
    ? `${plural(n, "sesión", "sesiones")} en versión original subtitulada de ${plural(datos.peliculas.length, "película", "películas")} en los cines de Madrid en los próximos ${DIAS_VOSE} días, por día y película, con el cine y la hora.`
    : "Sesiones en versión original subtitulada (VOSE) en los cines de Madrid, por día y película, con el cine y la hora.";
  const url = `${SITIO}${RUTA}`;
  return {
    title,
    description,
    alternates: { canonical: url },
    // Pocas sesiones (o la API caída): página fina, fuera del índice y del sitemap (app/sitemap.js usa el mismo umbral)
    ...(n < MINIMO_SESIONES_VOSE && { robots: { index: false, follow: true } }),
    openGraph: { title, description, url },
  };
}

// "Hoy · martes 3 de noviembre"
const tituloDia = (fecha, hoy) => {
  const largo = formato(fecha, { weekday: "long", day: "numeric", month: "long" });
  const relativo = etiquetaRelativa(fecha, hoy);
  return relativo ? `${relativo} · ${largo}` : largo.charAt(0).toUpperCase() + largo.slice(1);
};

function Pelicula({ pelicula, cines }) {
  return (
    // self-start en el póster: en una fila flex se estiraría hasta el alto de la tarjeta (adiós 2:3, recortado)
    <li className="flex gap-4 rounded-2xl border border-line bg-background p-4">
      <Link href={`/pelicula/${pelicula.id}`} tabIndex={-1} aria-hidden="true"
            className="hidden sm:block self-start w-16 shrink-0 aspect-[2/3] rounded-lg overflow-hidden border border-line bg-surface">
        {pelicula.poster_url && <img src={pelicula.poster_url.replace("/w500/", "/w185/")} alt="" loading="lazy" className="w-full h-full object-cover" />}
      </Link>
      <div className="min-w-0 flex-1 space-y-3">
        <div>
          <h3 className="text-lg md:text-xl font-display font-bold leading-tight text-foreground">
            <Link href={`/pelicula/${pelicula.id}`} className="hover:text-primary transition-colors">{pelicula.titulo}</Link>
          </h3>
          {(pelicula.titulo_original || pelicula.director || pelicula.anio) && (
            <p className="text-xs text-muted mt-1">
              {[pelicula.titulo_original, pelicula.director, pelicula.anio].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>
        <div className="@container">
          <div className={REJILLA_CINES}>
            {cines.map(([cine, pases]) => <SesionesCine key={cine} cine={cine} pases={pases} />)}
          </div>
        </div>
      </div>
    </li>
  );
}

function Dia({ dia, hoy }) {
  return (
    <>
      <h2 className="text-xl md:text-2xl font-display font-bold uppercase text-foreground">
        {tituloDia(dia.fecha, hoy)} <span className="text-sm font-sans font-semibold normal-case text-muted">· {plural(dia.sesiones, "sesión", "sesiones")}</span>
      </h2>
      <ul className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
        {dia.peliculas.map((item) => <Pelicula key={item.pelicula.id} {...item} />)}
      </ul>
    </>
  );
}

export default async function CineVosePage() {
  const datos = await leerVose();
  const dias = datos ? agruparVose(datos) : [];
  const top = datos ? cinesConMasVose(datos.pases) : [];
  const cines = new Set(datos?.pases.map((p) => p.cine_slug)).size;

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <JsonLd datos={migas(NOMBRE, RUTA)} />
      <TodayHeader showTitle={false} />

      <div className="max-w-9xl mx-auto px-4 md:px-8 space-y-8">
        <Migas nombre={NOMBRE} />

        <header className="space-y-2">
          <h1 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground">Cine en VOSE en Madrid</h1>
          <p className="text-muted">
            {datos?.pases.length
              ? `${plural(datos.pases.length, "sesión", "sesiones")} en versión original de ${plural(datos.peliculas.length, "película", "películas")} en ${plural(cines, "cine", "cines")}, hoy y los próximos ${DIAS_VOSE - 1} días. `
              : `Sesiones en versión original, hoy y los próximos ${DIAS_VOSE - 1} días. `}
            <Link href="/dia-del-espectador-madrid" className={ENLACE}>¿Más barato? Día del espectador</Link>
          </p>
        </header>

        {!datos ? (
          <p className="text-center text-muted py-16">No se han podido cargar las sesiones. Vuelve a intentarlo en unos minutos.</p>
        ) : dias.length === 0 ? (
          <p className="text-center text-muted py-16">No hay sesiones en VOSE en los próximos {DIAS_VOSE} días.</p>
        ) : (
          // Hoy y mañana abiertos; el resto plegado (<details>: en el HTML para buscadores, sin JavaScript)
          dias.map((dia, i) => i < 2 ? (
            <section key={dia.fecha} className="pt-6 border-t border-line">
              <Dia dia={dia} hoy={datos.desde} />
            </section>
          ) : (
            <details key={dia.fecha} className="pt-6 border-t border-line group">
              <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                <h2 className="inline text-xl md:text-2xl font-display font-bold uppercase text-foreground">{tituloDia(dia.fecha, datos.desde)}</h2>
                <span className="ml-2 text-sm font-semibold text-muted">· {plural(dia.sesiones, "sesión", "sesiones")} <span className="group-open:hidden">· Ver</span></span>
              </summary>
              <ul className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-4">
                {dia.peliculas.map((item) => <Pelicula key={item.pelicula.id} {...item} />)}
              </ul>
            </details>
          ))
        )}

        {/* Explicación al final, en letra pequeña: en el HTML para buscadores, sin empujar las sesiones hacia abajo */}
        <section aria-labelledby="sobre-vose" className="pt-6 border-t border-line max-w-3xl space-y-2 text-xs text-muted leading-relaxed">
          <h2 id="sobre-vose" className="font-bold uppercase tracking-wider">Sobre esta página</h2>
          <p>
            VOSE es versión original subtitulada en español: la película con sus voces y su idioma de origen, sin doblaje.
            Aquí están todas las sesiones en VOSE de los cines de Madrid que recoge fps24, de hoy y de los próximos {DIAS_VOSE - 1} días.
          </p>
          {top.length > 0 && (
            <p>
              Los que más programan en versión original esta semana son{" "}
              {top.map((c, i) => (
                <span key={c.slug}>
                  {i > 0 && (i === top.length - 1 ? " y " : ", ")}
                  <Link href={`/cines/${c.slug}`} className="hover:text-primary underline underline-offset-2">{c.nombre}</Link> ({plural(c.sesiones, "sesión", "sesiones")})
                </span>
              ))}.
            </p>
          )}
          <p>
            Van por día y, dentro de cada día, primero las películas con más pases. Pulsa una hora para comprar la entrada o guardarla
            en Mis sesiones; el nombre del cine lleva a su cartelera y sus precios.
          </p>
        </section>
      </div>
    </main>
  );
}
