import { comoUTC, formato } from "@/lib/fechasMadrid";

// /estrenos: próximo estreno de TMDB que aún no tiene sesiones en Madrid (item.sin_sesiones). Sin cines, horarios ni
// botón de entradas. Al abrirla (details: sin JS, con teclado y lector de pantalla), la sinopsis encima del póster; el
// título sigue a la vista para cerrarla. Mismo marco que Tarjeta (TarjetasSemana).
export default function TarjetaSinSesiones({ item }) {
  const { titulo, titulo_original, poster_url, sinopsis, generos, fecha_estreno, fecha_confirmada } = item.pelicula;
  const dia = `${formato(fecha_estreno, { weekday: "long" })} ${comoUTC(fecha_estreno).getUTCDate()}`;
  const completa = formato(fecha_estreno, { weekday: "long", day: "numeric", month: "long" });

  return (
    <li className="min-w-0">
      <details className="group relative h-full rounded-2xl overflow-hidden border border-line bg-background hover:border-muted open:border-primary transition-colors">
        <summary className="list-none [&::-webkit-details-marker]:hidden h-full flex flex-col cursor-pointer rounded-2xl focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary">
          <div className="relative aspect-[2/3] bg-surface">
            {poster_url && <img src={poster_url} alt="" loading="lazy" className="absolute inset-0 w-full h-full object-cover" />}
          </div>
          <div className="flex-1 min-w-0 flex flex-col gap-1.5 p-3">
            <p>
              <span className="inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-estreno text-foreground">
                <time dateTime={fecha_estreno} title={completa}>{fecha_confirmada ? `Estreno ${dia}` : `Fecha prevista: ${dia}`}</time>
              </span>
            </p>
            <h3 className="font-display font-bold leading-tight text-foreground line-clamp-2 text-base md:text-lg group-open:text-primary" title={titulo}>
              {titulo}
            </h3>
            <p className="mt-auto pt-2 border-t border-line text-xs font-semibold text-muted">No hay sesiones disponibles todavía</p>
            <span className="sr-only">. Ver sinopsis</span>
          </div>
        </summary>
        <div className="absolute inset-x-0 top-0 aspect-[2/3] overflow-y-auto bg-background/95 p-3 flex flex-col gap-2 text-sm">
          {titulo_original && <p className="text-xs text-muted italic">{titulo_original}</p>}
          {generos && <p className="text-xs font-semibold text-foreground">{generos}</p>}
          <p className="text-muted line-clamp-[9] md:line-clamp-[11]">{sinopsis || "Aún no hay sinopsis en español."}</p>
        </div>
      </details>
    </li>
  );
}
