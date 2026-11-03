import Link from "next/link";
import TodayHeader from "@/components/TodayHeader";
import JsonLd, { Migas, SITIO, migas } from "@/components/JsonLd";
import { ChipHora } from "@/components/Sesiones";
import { diaCompleto, etiquetaRelativa, formato, hoyMadrid } from "@/lib/fechasMadrid";
import { ETIQUETA_TIPO, cinesPorPrecio, euros, reglasEspectador, revisionTarifas, semanaEspectador } from "@/lib/tarifas";

const RUTA = "/dia-del-espectador-madrid";
const NOMBRE = "Día del espectador";

// ISR de 5 minutos, como /cines. shortcut: a medianoche, "hoy" puede ir hasta 5 min tarde (igual que /cines)
export const revalidate = 300;

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function leer(ruta) {
  try {
    const res = await fetch(`${API}${ruta}`, { next: { revalidate } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error(`Error loading ${ruta}:`, err);
    return null;
  }
}

const title = "Día del espectador en Madrid: cines baratos y precio de hoy | fps24";
const description = "Qué cines de Madrid tienen día del espectador cada día de la semana, cuánto cuesta la entrada hoy en cada sala, de la más barata a la más cara, y las sesiones de hoy a precio reducido.";

export const metadata = {
  title,
  description,
  alternates: { canonical: `${SITIO}${RUTA}` },
  openGraph: { title, description, url: `${SITIO}${RUTA}` },
};

const ENLACE = "text-foreground font-semibold hover:text-primary underline underline-offset-2";
const PENDIENTE = <span className="ml-2 text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded border border-line text-muted">Pendiente de verificar</span>;
const minuscula = (s) => s.charAt(0).toLowerCase() + s.slice(1);

// Día de la semana con más cines en día del espectador (según las reglas, sin festivos)
function diaConMasCines(cines) {
  const cuenta = {};
  for (const c of cines) for (const r of reglasEspectador(c.tarifas)) for (const d of r.dias) cuenta[d] = (cuenta[d] ?? 0) + 1;
  const [dia, n] = Object.entries(cuenta).sort((a, b) => b[1] - a[1])[0] ?? [];
  return dia ? { dia, n } : null;
}

// El día del espectador más barato de la tabla: { nombre, slug, dias, precio }
function masBarato(cines) {
  return cines
    .flatMap((c) => reglasEspectador(c.tarifas).map((r) => ({ nombre: c.nombre, slug: c.slug, dias: r.dias, precio: r.precio })))
    .sort((a, b) => a.precio - b.precio)[0] ?? null;
}

// Sesiones de hoy en un cine con día del espectador (de GET /cines/{slug})
function SesionesHoy({ cine, precio, hoy }) {
  const peliculas = cine.dias.find((d) => d.fecha === hoy)?.peliculas ?? [];
  if (!peliculas.length) return null;
  return (
    <li className="rounded-2xl border border-line bg-background p-4 space-y-3">
      <h3 className="text-lg font-display font-bold uppercase leading-tight text-foreground flex flex-wrap items-center gap-2">
        <Link href={`/cines/${cine.slug}`} className="hover:text-primary transition-colors">{cine.nombre}</Link>
        <span className="text-xs font-sans font-bold normal-case px-1.5 py-0.5 rounded bg-accent text-foreground">Espectador · {euros(precio)}</span>
      </h3>
      <ul className="space-y-3">
        {peliculas.map((p) => (
          <li key={p.id} className="space-y-1.5">
            <Link href={`/pelicula/${p.id}`} className="text-sm font-bold text-foreground hover:text-primary transition-colors">{p.titulo}</Link>
            <div className="flex flex-wrap gap-2">
              {p.sesiones.map((s) => (
                <ChipHora key={s.id} pase={{ ...s, cine_slug: cine.slug, pelicula: { id: p.id, titulo: p.titulo, poster_url: p.poster_url } }} cine={cine.nombre} />
              ))}
            </div>
          </li>
        ))}
      </ul>
    </li>
  );
}

export default async function DiaEspectadorPage() {
  const hoy = hoyMadrid();
  const cines = await leer("/cines");

  if (!cines) {
    return (
      <main className="min-h-screen bg-background text-foreground pb-20">
        <TodayHeader showTitle={false} />
        <div className="max-w-6xl mx-auto px-4 md:px-6">
          <h1 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground mb-4">Día del espectador en Madrid</h1>
          <p className="text-center text-muted py-16">No se han podido cargar los cines. Vuelve a intentarlo en unos minutos.</p>
        </div>
      </main>
    );
  }

  const semana = semanaEspectador(cines, hoy);
  const { conPrecio, sinPrecio } = cinesPorPrecio(cines, hoy);
  const revision = revisionTarifas(cines);
  const pendientes = new Set(revision.pendientes.map((c) => c.slug));
  const masCines = diaConMasCines(cines);
  const barato = masBarato(cines);
  // Hoy toca en estos cines: sus sesiones de hoy (una petición por cine, con la misma caché)
  const hoyEspectador = semana[0].cines;
  const fichas = (await Promise.all(hoyEspectador.map((c) => leer(`/cines/${c.slug}`)))).filter(Boolean);
  const precioDe = Object.fromEntries(hoyEspectador.map((c) => [c.slug, c.precio]));

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <JsonLd datos={migas(NOMBRE, RUTA)} />
      <TodayHeader showTitle={false} />

      <div className="max-w-6xl mx-auto px-4 md:px-6 space-y-10">
        <Migas nombre={NOMBRE} />

        <header className="space-y-2">
          <h1 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground">Día del espectador en Madrid</h1>
          <p className="text-muted">
            {hoyEspectador.length
              ? `Hoy hay día del espectador en ${hoyEspectador.length === 1 ? "1 cine" : `${hoyEspectador.length} cines`}, desde ${euros(hoyEspectador[0].precio)}. `
              : "Hoy ningún cine tiene día del espectador. "}
            {revision.fecha && `Tarifas revisadas el ${formato(revision.fecha, { day: "numeric", month: "short", year: "numeric" })}. `}
            <Link href="/cine-vose-madrid" className={ENLACE}>Sesiones en VOSE</Link>
          </p>
        </header>

        {/* Los 7 días desde hoy, con fecha: así se ve qué festivo anula el día del espectador */}
        <section className="space-y-4">
          <h2 className="text-2xl md:text-3xl font-display font-bold uppercase text-foreground">Esta semana, día a día</h2>
          <div className="overflow-x-auto rounded-2xl border border-line">
            <table className="w-full text-sm">
              <thead className="bg-surface text-left text-xs uppercase tracking-wider text-muted">
                <tr><th scope="col" className="px-3 md:px-4 py-3 w-24 md:w-40">Día</th><th scope="col" className="px-3 md:px-4 py-3">Cines con día del espectador</th></tr>
              </thead>
              <tbody>
                {semana.map((d) => (
                  <tr key={d.fecha} className="border-t border-line align-top">
                    <th scope="row" className="px-3 md:px-4 py-3 text-left font-bold text-foreground">
                      {etiquetaRelativa(d.fecha, hoy) && <span className="block text-xs text-primary uppercase">{etiquetaRelativa(d.fecha, hoy)}</span>}
                      {formato(d.fecha, { weekday: "long", day: "numeric", month: "short" })}
                    </th>
                    <td className="px-3 md:px-4 py-3">
                      {d.festivo && <p className="text-xs font-bold text-muted mb-1">Festivo: sin día del espectador, precio de fin de semana.</p>}
                      {d.cines.length ? (
                        <ul className="flex flex-wrap gap-2">
                          {d.cines.map((c) => (
                            <li key={c.slug}>
                              <Link href={`/cines/${c.slug}`} className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg border border-accent bg-accent-soft text-foreground text-xs font-semibold hover:bg-accent transition-colors">
                                {c.nombre} <span className="font-bold">{euros(c.precio)}</span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      ) : !d.festivo && <span className="text-muted">Ningún cine</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl md:text-3xl font-display font-bold uppercase text-foreground">Cines por precio de hoy</h2>
          <p className="text-sm text-muted">
            Precio de una entrada general hoy, {diaCompleto(hoy).toLowerCase()}, del más barato al más caro.
            {revision.pendientes.length > 0 && ` Las tarifas de ${revision.pendientes.length} cines están pendientes de verificar y van marcadas.`}
          </p>
          <ol className="divide-y divide-line rounded-2xl border border-line">
            {conPrecio.map((c, i) => (
              <li key={c.slug} className="flex items-baseline gap-3 px-4 py-3">
                <span className="w-6 shrink-0 text-xs font-bold text-muted">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <Link href={`/cines/${c.slug}`} className="font-bold text-foreground hover:text-primary transition-colors">{c.nombre}</Link>
                  {pendientes.has(c.slug) && PENDIENTE}
                  {c.tarifas.notas?.includes("€") && <p className="text-xs text-muted">{c.tarifas.notas}</p>}
                </div>
                <span className="shrink-0 text-right">
                  <span className={`text-sm font-bold text-foreground ${c.hoy.tipo === "espectador" ? "px-1.5 py-0.5 rounded bg-accent" : ""}`}>{euros(c.hoy.precio)}</span>
                  <span className="block text-xs text-muted">{c.hoy.tipo === "espectador" ? "día del espectador" : c.hoy.tipo === "entrada" ? "precio único" : ETIQUETA_TIPO[c.hoy.tipo]}</span>
                </span>
              </li>
            ))}
          </ol>
          {sinPrecio.length > 0 && (
            <p className="text-sm text-muted">
              Sin un precio único verificado (consulta su web):{" "}
              {sinPrecio.map((c, i) => (
                <span key={c.slug}>
                  {i > 0 && ", "}
                  <Link href={`/cines/${c.slug}`} className="hover:text-primary underline underline-offset-2">{c.nombre}</Link>
                  {c.tarifas?.precio_texto && ` (${minuscula(c.tarifas.precio_texto)})`}
                  {c.tipo === "cultural" && " (centro cultural: precio en cada sesión)"}
                  {pendientes.has(c.slug) && " (pendiente de verificar)"}
                </span>
              ))}.
            </p>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="text-2xl md:text-3xl font-display font-bold uppercase text-foreground">Sesiones de hoy a precio reducido</h2>
          {fichas.some((c) => c.dias.some((d) => d.fecha === hoy && d.peliculas.length)) ? (
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {fichas.map((c) => <SesionesHoy key={c.slug} cine={c} precio={precioDe[c.slug]} hoy={hoy} />)}
            </ul>
          ) : (
            <p className="text-muted">
              Hoy ningún cine tiene día del espectador{semana.find((d, i) => i > 0 && d.cines.length) ? (() => {
                const proximo = semana.find((d, i) => i > 0 && d.cines.length);
                return `. El próximo es el ${formato(proximo.fecha, { weekday: "long", day: "numeric" })}, en ${proximo.cines.map((c) => c.nombre).join(", ")}`;
              })() : ""}.
            </p>
          )}
        </section>

        {/* Explicación al final, en letra pequeña: en el HTML para buscadores, sin empujar las tablas hacia abajo */}
        <section aria-labelledby="sobre-espectador" className="pt-6 border-t border-line max-w-3xl space-y-2 text-xs text-muted leading-relaxed">
          <h2 id="sobre-espectador" className="font-bold uppercase tracking-wider">Sobre esta página</h2>
          <p>
            El día del espectador es el día de la semana en que un cine baja el precio de todas sus sesiones. Cada sala elige el suyo,
            y en Madrid un festivo lo anula: ese día se cobra como fin de semana.
            {masCines && <> El {minuscula(masCines.dia)} es el día con más cines a precio reducido ({masCines.n}).</>}
            {barato && <> El más barato de la tabla es el de <Link href={`/cines/${barato.slug}`} className="hover:text-primary underline underline-offset-2">{barato.nombre}</Link>: {euros(barato.precio)} los {barato.dias.map(minuscula).join(" y ")}.</>}
          </p>
          <p>
            {revision.fecha && <>Tarifas revisadas por última vez el {diaCompleto(revision.fecha).toLowerCase()}. </>}
            Son precios de taquilla orientativos: confírmalos en la web del cine antes de ir. Solo se muestran los precios de la tabla
            de tarifas de fps24; los cines sin un precio verificado remiten a su web.
          </p>
        </section>
      </div>
    </main>
  );
}
