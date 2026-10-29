import Link from "next/link";
import Avatar, { AtribucionPoster } from "@/components/Avatar";
import { BOTON_PRIMARIO } from "@/components/DialogoDiario";
import NotaEstrellas from "@/components/NotaEstrellas";

// Piezas de /u/<usuario>, sin estado: las usan la vista pública (servidor, app/u/[usuario]) y la del dueño (Perfil.js).
// esDueno: se ven las secciones vacías con un texto de ayuda; a los visitantes se les ocultan.

// Fechas "YYYY-MM-DD" de la API: en UTC para que el huso del navegador no las mueva (como en CarteleraCine)
export const formato = (fecha, opciones) => new Date(`${fecha}T00:00Z`).toLocaleDateString("es-ES", { timeZone: "UTC", ...opciones });
const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);
export const nombreMes = (fecha, mes = "long") => capitalizar(formato(fecha, { month: mes, year: "numeric" }).replace(" de ", " "));

// Entradas (ya ordenadas) en grupos por mes: [{ clave: "YYYY-MM", entradas }]
export function porMes(entradas) {
  const meses = [];
  for (const e of entradas) {
    const clave = e.fecha_vista.slice(0, 7);
    if (meses.at(-1)?.clave !== clave) meses.push({ clave, entradas: [] });
    meses.at(-1).entradas.push(e);
  }
  return meses;
}

export const TITULO_SECCION = "text-xl font-display font-bold uppercase text-foreground";
const TITULO_LATERAL = "text-sm font-bold uppercase tracking-wider text-muted border-b border-line pb-2";
const ENLACE = "font-bold text-primary hover:underline";

export const PESTANAS = [
  { clave: "perfil", etiqueta: "Perfil", ruta: "" },
  { clave: "diario", etiqueta: "Diario", ruta: "/diario" },
  { clave: "cines", etiqueta: "Cines", ruta: "/cines" },
  { clave: "sesiones", etiqueta: "Sesiones", ruta: "/sesiones" }, // solo el dueño: su agenda privada
  { clave: "amigos", etiqueta: "Amigos", ruta: "/amigos" }, // solo el dueño
];

// Texto de ayuda del dueño, con enlace a la edición o a donde se añade el contenido
export function Ayuda({ children }) {
  return <p className="mt-3 text-sm text-muted">{children}</p>;
}

// Solo para el dueño, bajo una sección que no ve todo el mundo: una nota discreta. nivel: "privado" o "amigos"
export function SoloTu({ que, nivel = "privado" }) {
  return (
    <p className="mt-1 text-xs text-muted">
      {nivel === "amigos" ? `Solo tú y tus amigos veis ${que}.` : `Solo tú ves ${que}.`}{" · "}
      <Link href="/perfil/editar" className="underline hover:text-primary">Cambiar quién lo ve</Link>
    </p>
  );
}

// Avatar grande, nombre, bio, Letterboxd y (dueño) "Editar mi perfil"; a la derecha, o debajo en móvil, las cifras.
// cifras: { entradas, este_anio, cines, amigos }; las que sean undefined no se ven (quien mira no puede ver ese dato).
// Amigos solo enlaza para el dueño: la lista de amigos de otra persona no es pública.
// children: debajo del nombre (el botón de amistad en el perfil de otra persona).
export function CabeceraPerfil({ perfil, cifras = {}, esDueno = false, children }) {
  const { usuario, bio, avatar, letterboxd_usuario: letterboxd } = perfil;
  const filas = [["Entradas", cifras.entradas], ["Este año", cifras.este_anio], ["Cines favoritos", cifras.cines],
    ["Amigos", cifras.amigos, esDueno && `/u/${usuario}/amigos`]]
    .filter(([, valor]) => valor !== undefined && valor !== null);
  return (
    <div className="flex flex-col md:flex-row md:items-center gap-6">
      <div className="flex min-w-0 flex-1 items-start gap-4 md:gap-6">
        <div className="flex shrink-0 flex-col items-center">
          <Avatar usuario={usuario} avatar={avatar} className="w-20 h-20 md:w-32 md:h-32 text-3xl md:text-5xl" />
          {avatar?.tipo === "pelicula" && <AtribucionPoster className="mt-1" />}
        </div>
        <div className="min-w-0">
          <h2 className="text-2xl md:text-4xl font-black font-display text-primary break-all">@{usuario}</h2>
          {/* Texto plano con sus saltos de línea: nunca HTML */}
          {bio && <p className="mt-2 text-foreground whitespace-pre-wrap break-words">{bio}</p>}
          {letterboxd && (
            <a href={`https://letterboxd.com/${letterboxd}/`} target="_blank" rel="noopener noreferrer"
               className={`mt-1 inline-flex items-center min-h-11 text-sm break-all ${ENLACE}`}>
              Letterboxd: @{letterboxd}<span className="sr-only"> (se abre en una pestaña nueva)</span>
            </a>
          )}
          {esDueno && <div className="mt-2"><Link href="/perfil/editar" className={`inline-block ${BOTON_PRIMARIO}`}>Editar mi perfil</Link></div>}
          {children}
        </div>
      </div>
      {filas.length > 0 && (
        // En móvil, columnas iguales y las etiquetas largas bajan de línea: cuatro cifras caben en 390 px
        <dl className="flex shrink-0 divide-x divide-line border-t border-line pt-4 md:border-t-0 md:pt-0">
          {filas.map(([etiqueta, valor, enlace]) => (
            <div key={etiqueta} className="flex min-w-0 flex-1 md:flex-none flex-col-reverse items-center justify-end px-2 md:px-4 text-center">
              <dt className="text-[11px] font-semibold uppercase tracking-wider text-muted">{etiqueta}</dt>
              <dd className="text-2xl md:text-3xl font-black font-display text-foreground">
                {enlace
                  ? <Link href={enlace} className="hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
                      {valor.toLocaleString("es-ES")}<span className="sr-only"> (ver tus amigos)</span>
                    </Link>
                  : valor.toLocaleString("es-ES")}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

// Fila de pestañas con URL propia: enlaces con aria-current, no role="tab" (cada una es otra página).
// contadores: { clave: n } para un número discreto junto a la pestaña (solicitudes de amistad recibidas)
export function PestanasPerfil({ usuario, actual, visibles, contadores = {} }) {
  return (
    <nav aria-label="Secciones del perfil" className="mt-6 border-b border-line">
      <ul className="flex overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {PESTANAS.filter((p) => visibles.includes(p.clave)).map((p) => (
          <li key={p.clave} className="shrink-0">
            <Link href={`/u/${usuario}${p.ruta}`} aria-current={p.clave === actual ? "page" : undefined}
                  className={`flex items-center min-h-11 px-4 text-xs md:text-[13px] font-semibold uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary ${p.clave === actual ? "text-primary shadow-[inset_0_-3px_0_var(--primary)]" : "text-muted hover:text-foreground"}`}>
              {p.etiqueta}
              {contadores[p.clave] > 0 && (
                <span className="ml-1.5 min-w-5 px-1 bg-primary-soft text-primary text-[11px] font-bold text-center tabular-nums">
                  {contadores[p.clave]}<span className="sr-only"> {contadores[p.clave] === 1 ? "solicitud pendiente" : "solicitudes pendientes"}</span>
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

// Póster grande con la nota y el día debajo. Enlaza a la ficha si hay id; si no, solo el título.
function Tarjeta({ entrada }) {
  const { pelicula } = entrada;
  const poster = (
    <div className="aspect-[2/3] overflow-hidden border border-line bg-surface">
      {pelicula.poster_url
        ? <img src={pelicula.poster_url} alt={pelicula.titulo} className="w-full h-full object-cover" loading="lazy" />
        : <span className="flex h-full items-center justify-center p-2 text-center text-xs font-bold text-foreground break-words">{pelicula.titulo}</span>}
    </div>
  );
  return (
    <li className="min-w-0">
      {pelicula.id
        ? <Link href={`/pelicula/${pelicula.id}`} title={pelicula.titulo} className="block hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">{poster}</Link>
        : poster}
      <div className="mt-1 flex flex-wrap items-center justify-between gap-x-2 text-xs text-muted">
        {entrada.nota ? <NotaEstrellas valor={entrada.nota} soloLectura /> : <span />}
        <time dateTime={entrada.fecha_vista}>{formato(entrada.fecha_vista, { day: "numeric", month: "short" })}</time>
      </div>
    </li>
  );
}

export function ActividadReciente({ entradas, esDueno, soloTu }) {
  if (!entradas.length && !esDueno) return null;
  return (
    <section aria-labelledby="actividad-reciente">
      <h3 id="actividad-reciente" className={TITULO_SECCION}>Actividad reciente</h3>
      {soloTu && <SoloTu que="tu actividad" nivel={soloTu} />}
      {entradas.length ? (
        <>
          <ul className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
            {entradas.slice(0, 8).map((e, i) => <Tarjeta key={e.id ?? i} entrada={e} />)}
          </ul>
          <AtribucionPoster className="mt-2" />
        </>
      ) : (
        <Ayuda>Aún no hay películas en tu diario. Pulsa <strong>+</strong> en la barra de arriba para añadir una que hayas visto.</Ayuda>
      )}
    </section>
  );
}

// Lateral: cines favoritos enlazados, con recuento
export function CinesLateral({ cines, esDueno, soloTu }) {
  return (
    <section aria-labelledby="cines-lateral">
      <h3 id="cines-lateral" className={TITULO_LATERAL}>
        {esDueno ? "Mis cines" : "Cines favoritos"} <span className="font-normal">({cines.length})</span>
      </h3>
      {soloTu && <SoloTu que="tus cines" nivel={soloTu} />}
      {cines.length ? (
        <ul className="mt-2">
          {cines.map((c) => (
            <li key={c.slug}>
              <Link href={`/cines/${c.slug}`} className="flex items-center min-h-11 text-sm font-bold text-foreground hover:text-primary">
                <span aria-hidden="true" className="mr-1 text-primary">★</span>{c.nombre}
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <Ayuda>Aún no tienes cines favoritos. Pulsa la ★ en un cine de <Link href="/cines" className={ENLACE}>Cines</Link>.</Ayuda>
      )}
    </section>
  );
}

// Lateral: las últimas entradas agrupadas por mes ("Oct 2026"; debajo, día y título), el total y "Ver todo el diario"
export function DiarioLateral({ usuario, entradas, total, soloTu }) {
  return (
    <section aria-labelledby="diario-lateral">
      <h3 id="diario-lateral" className={TITULO_LATERAL}>Diario <span className="font-normal">({total.toLocaleString("es-ES")})</span></h3>
      {soloTu && <SoloTu que="tu diario" nivel={soloTu} />}
      {entradas.length ? (
        <>
          {porMes(entradas.slice(0, 10)).map((m) => (
            <div key={m.clave} className="mt-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-primary">{nombreMes(`${m.clave}-01`, "short").replace(".", "")}</h4>
              <ul>
                {m.entradas.map((e, i) => (
                  <li key={e.id ?? i} className="flex gap-3 py-1 text-sm">
                    <time dateTime={e.fecha_vista} className="w-5 shrink-0 text-right tabular-nums text-muted">{Number(e.fecha_vista.slice(8))}</time>
                    {e.pelicula.id
                      ? <Link href={`/pelicula/${e.pelicula.id}`} className="min-w-0 break-words text-foreground hover:text-primary">{e.pelicula.titulo}</Link>
                      : <span className="min-w-0 break-words text-foreground">{e.pelicula.titulo}</span>}
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <Link href={`/u/${usuario}/diario`} className={`mt-2 inline-flex items-center min-h-11 text-sm ${ENLACE}`}>Ver todo el diario →</Link>
        </>
      ) : (
        <Ayuda>Tu diario está vacío.</Ayuda>
      )}
    </section>
  );
}

// Pestaña Perfil: actividad a la izquierda y, en escritorio, cines y diario en la barra lateral
export function PestanaPerfil({ usuario, entradas, total, cines, esDueno = false, diarioSoloTu = false, cinesSoloTu = false }) {
  const lateral = [
    cines && (esDueno || cines.length > 0) && <CinesLateral key="cines" cines={cines} esDueno={esDueno} soloTu={cinesSoloTu} />,
    entradas && (esDueno || entradas.length > 0) && <DiarioLateral key="diario" usuario={usuario} entradas={entradas} total={total} soloTu={diarioSoloTu} />,
  ].filter(Boolean);
  const actividad = entradas && (esDueno || entradas.length > 0) && <ActividadReciente entradas={entradas} esDueno={esDueno} soloTu={diarioSoloTu} />;
  if (!actividad && !lateral.length) {
    return <p className="mt-10 text-center text-muted">@{usuario} no comparte su diario ni sus cines.</p>;
  }
  return (
    <div className={`mt-8 grid gap-8 ${lateral.length ? "md:grid-cols-[minmax(0,1fr)_16rem]" : ""}`}>
      <div className="min-w-0">{actividad}</div>
      {lateral.length > 0 && <aside aria-label="Cines y diario" className="space-y-8 min-w-0">{lateral}</aside>}
    </div>
  );
}

// Pestaña Cines: tarjetas con el nombre enlazado a su ficha y la zona. onQuitar (solo el dueño): botón para quitarlo.
export function TarjetasCines({ cines, onQuitar }) {
  return (
    <ul className="mt-6 grid gap-3 sm:grid-cols-2">
      {cines.map((c) => (
        <li key={c.slug} className="flex items-stretch border border-line bg-surface">
          <div className="min-w-0 flex-1 p-4">
            <Link href={`/cines/${c.slug}`} className="font-display font-bold uppercase text-foreground hover:text-primary break-words">
              <span aria-hidden="true" className="mr-1 text-primary">★</span>{c.nombre}
            </Link>
            {c.zona && <p className="mt-1 text-sm text-muted">{c.zona}</p>}
          </div>
          {onQuitar && (
            <button type="button" onClick={() => onQuitar(c)} aria-label={`Quitar ${c.nombre} de mis cines`}
                    className="px-4 border-l border-line text-muted hover:text-red-600 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary">
              <span aria-hidden="true">×</span>
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}
