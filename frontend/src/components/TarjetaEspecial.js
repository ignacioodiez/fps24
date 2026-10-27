import Link from "next/link";
import { MarcaFavorito } from "@/components/BotonFavorito";
import { EnlaceCine } from "@/components/Sesiones";

// "SÁB 24 · 22:00"
const fechaDestacada = (fechaHora) => {
  const d = new Date(fechaHora);
  const dia = d.toLocaleDateString("es-ES", { weekday: "short" }).replace(".", "");
  return `${dia} ${d.getDate()} · ${d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`;
};

// El backdrop se guarda en tamaño "original" (varios MB): para una tarjeta basta w780
export const imagenDe = (pelicula) =>
  pelicula.backdrop_url?.replace("/t/p/original/", "/t/p/w780/") || pelicula.poster_url || null;

function Entradas({ href, className }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer"
       className={`relative z-10 shrink-0 rounded-full bg-primary text-white font-semibold hover:opacity-90 transition-opacity ${className}`}>
      Entradas
    </a>
  );
}

// grande: imagen a sangre con el texto encima (la de mayor nota). Si no, compacta: miniatura a la izquierda y
// solo fecha, título y cine. La tarjeta abre la vista rápida; el título, la página completa; "Entradas", la compra.
export default function TarjetaEspecial({ especial, grande = false, amplia = false, className = "" }) {
  const { pelicula, pase, nota } = especial;
  const href = `/pelicula/${pelicula.id}?dia=${pase.fecha_hora.slice(0, 10)}`; // abre en el día del pase
  const imagen = imagenDe(pelicula);
  const precio = pase.precio && pase.precio !== "Consultar" ? pase.precio : null;
  const idioma = pase.idioma && pase.idioma !== "Español" ? pase.idioma : null;
  // Título: <a> normal (navegación completa) a la página entera. El resto de la tarjeta abre la vista rápida.
  const enlace = (
    <a href={href} onClick={(e) => e.stopPropagation()} className="relative z-[2] hover:underline">{pelicula.titulo}</a>
  );
  const capa = (
    <Link href={href} scroll={false} aria-label={`Vista rápida: ${pelicula.titulo}`} className="absolute inset-0 z-[1]" />
  );

  if (grande) {
    return (
      <li className={`relative group min-h-56 md:min-h-0 rounded-2xl overflow-hidden border-2 border-primary bg-primary-soft ${className}`}>
        {imagen ? (
          <img src={imagen} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <span className="absolute inset-0 flex items-center justify-center font-display font-bold text-6xl text-primary" aria-hidden="true">
            {pelicula.titulo?.[0]}
          </span>
        )}
        <div className="absolute inset-0 bg-linear-to-t from-black/85 via-black/30 to-transparent" />
        {capa}
        <p className="absolute top-3 left-3 bg-background text-primary text-sm md:text-base font-bold uppercase tracking-wide px-2.5 py-1 rounded-lg">
          {fechaDestacada(pase.fecha_hora)}
        </p>
        <div className="absolute inset-x-0 bottom-0 p-3 text-white">
          <h4 className="text-lg md:text-xl font-display font-bold leading-tight line-clamp-2" title={pelicula.titulo}>
            {enlace}
            {pelicula.anio && <span className="font-sans font-normal text-xs text-white/70"> ({pelicula.anio})</span>}
          </h4>
          {amplia && pelicula.sinopsis && <p className="mt-1 text-sm text-white/80 line-clamp-2">{pelicula.sinopsis}</p>}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-white/90">
            <EnlaceCine slug={pase.cine_slug} className="truncate min-w-0 relative z-[2] hover:underline focus-visible:outline-white"><MarcaFavorito slug={pase.cine_slug} /> {pase.cine}</EnlaceCine>
            {idioma && <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-white/20">{idioma}</span>}
            {nota != null && <span className="font-semibold">★ {nota.toFixed(1)}</span>}
            {precio && <span>{precio}</span>}
            {pase.link_compra && <Entradas href={pase.link_compra} className="ml-auto px-3 py-1 text-xs" />}
          </div>
        </div>
      </li>
    );
  }

  return (
    <li className={`relative group flex min-w-0 min-h-0 rounded-xl overflow-hidden border border-primary bg-background ${className}`}>
      {/* Sin miniatura entre 768 y 1023 px: la celda es tan estrecha que el texto no cabría */}
      <div className="relative w-12 lg:w-16 shrink-0 bg-primary-soft flex md:hidden lg:flex items-center justify-center">
        {imagen ? (
          <img src={imagen} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover" />
        ) : (
          <span className="font-display font-bold text-xl text-primary" aria-hidden="true">{pelicula.titulo?.[0]}</span>
        )}
      </div>
      {capa}
      <div className="flex-1 min-w-0 px-2 py-1.5 flex flex-col justify-center gap-0.5">
        <div className="flex flex-wrap items-center justify-between gap-1">
          <p className="text-xs font-bold uppercase tracking-wide text-primary">{fechaDestacada(pase.fecha_hora)}</p>
          {pase.link_compra && <Entradas href={pase.link_compra} className="px-2 py-0.5 text-[10px]" />}
        </div>
        <h4 className="text-sm font-display font-bold leading-tight text-foreground line-clamp-2 md:line-clamp-1 lg:line-clamp-2 group-hover:text-primary transition-colors" title={pelicula.titulo}>
          {enlace}
        </h4>
        {/* En móvil el cine va en su propia línea para que no se corte */}
        <p className="flex flex-wrap md:flex-nowrap items-center gap-x-1 text-[11px] text-muted min-w-0">
          <EnlaceCine slug={pase.cine_slug} title={pase.cine} className="truncate basis-full md:basis-auto relative z-[2] hover:text-primary hover:underline focus-visible:outline-primary"><MarcaFavorito slug={pase.cine_slug} /> {pase.cine}</EnlaceCine>
          {nota != null && <span className="shrink-0 font-semibold text-foreground">★ {nota.toFixed(1)}</span>}
          {idioma && <span className="shrink-0">· {idioma}</span>}
        </p>
      </div>
    </li>
  );
}
