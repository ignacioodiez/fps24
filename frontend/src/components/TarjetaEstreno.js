import Link from "next/link";

const VOTOS_MIN = 10;

// "viernes 23" a partir de "YYYY-MM-DD" (sin "T": new Date lo leería en UTC)
const diaEstreno = (fecha) => {
  const d = new Date(`${fecha}T00:00`);
  return `${d.toLocaleDateString("es-ES", { weekday: "long" })} ${d.getDate()}`;
};

// "vie 23, 16:00"
const sesionCorta = (fechaHora) => {
  const d = new Date(fechaHora);
  const dia = d.toLocaleDateString("es-ES", { weekday: "short" }).replace(".", "");
  return `${dia} ${d.getDate()}, ${d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`;
};

// Celda de la cuadrícula 2x2 de estrenos. Móvil: póster arriba. Escritorio: póster a la izquierda y la celda
// ocupa todo el alto de su fila. className: celdas extra cuando hay menos de 4 estrenos.
export default function TarjetaEstreno({ estreno, className = "" }) {
  const { pelicula, fecha_estreno, votos, cines, primera_sesion, sin_nota } = estreno;
  const nota = pelicula.nota_tmdb;
  const notaFiable = !sin_nota && nota != null && (votos ?? 0) >= VOTOS_MIN;

  return (
    <li className={`min-w-0 min-h-0 ${className}`}>
      <Link href={`/pelicula/${pelicula.id}`} className="group flex flex-col md:flex-row md:h-full gap-2 md:gap-3">
        {/* Póster de tamaño fijo: sin imagen, el título sobre fondo neutro */}
        <div className="relative aspect-[2/3] md:aspect-auto md:h-full md:w-2/5 md:max-w-[130px] shrink-0 rounded-2xl overflow-hidden border border-line bg-surface group-hover:border-muted transition-colors">
          {pelicula.poster_url ? (
            <img src={pelicula.poster_url} alt={pelicula.titulo} loading="lazy" className="absolute inset-0 w-full h-full object-cover" />
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

        <div className="min-w-0 flex flex-col gap-1 md:py-1">
          <h4 className="text-sm font-display font-bold leading-tight text-foreground line-clamp-2 group-hover:text-primary transition-colors" title={pelicula.titulo}>
            {pelicula.titulo}
          </h4>
          <p>
            <span className="inline-block text-[10px] font-semibold uppercase tracking-wider bg-accent-soft text-foreground px-2 py-0.5 rounded-full">
              Estreno {diaEstreno(fecha_estreno)}
            </span>
          </p>
          {!notaFiable && (
            <p className="text-xs text-muted">
              {nota != null && votos ? `★ ${nota.toFixed(1)} · ${votos} ${votos === 1 ? "voto" : "votos"}` : "Sin valoraciones aún"}
            </p>
          )}
          <p className="text-xs text-muted">
            {cines} {cines === 1 ? "cine" : "cines"} · Primera: {sesionCorta(primera_sesion.fecha_hora)}
          </p>
        </div>
      </Link>
    </li>
  );
}
