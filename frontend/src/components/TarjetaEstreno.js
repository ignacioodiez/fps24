import Link from "next/link";
import { MarcaFavorito } from "@/components/BotonFavorito";
import { EnlaceCine } from "@/components/Sesiones";

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
  // sugerida (SeccionDestacadas): la primera, o la de un cine favorito ese mismo día
  const sugerida = estreno.sugerida ?? primera_sesion;
  const href = `/pelicula/${pelicula.id}?dia=${primera_sesion.fecha_hora.slice(0, 10)}`; // abre en el día de la primera sesión
  const nota = pelicula.nota_tmdb;
  const notaFiable = !sin_nota && nota != null && (votos ?? 0) >= VOTOS_MIN;

  return (
    <li className={`relative group min-w-0 min-h-0 flex flex-col md:flex-row md:h-full gap-2 md:gap-3 ${className}`}>
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
          <h4 className="text-sm font-display font-bold leading-tight text-foreground line-clamp-2" title={pelicula.titulo}>
            <a href={href} onClick={(e) => e.stopPropagation()} className="relative z-[2] hover:text-primary transition-colors">
              {pelicula.titulo}
            </a>
          </h4>
          <p>
            <span className="inline-block text-[10px] font-semibold uppercase tracking-wider bg-estreno text-foreground px-2 py-0.5 rounded-full">
              Estreno {diaEstreno(fecha_estreno)}
            </span>
          </p>
          {!notaFiable && (
            <p className="text-xs text-muted">
              {nota != null && votos ? `★ ${nota.toFixed(1)} · ${votos} ${votos === 1 ? "voto" : "votos"}` : "Sin valoraciones aún"}
            </p>
          )}
          <p className="text-xs text-muted">
            {cines} {cines === 1 ? "cine" : "cines"} · {sugerida === primera_sesion
              ? <>Primera: {sesionCorta(primera_sesion.fecha_hora)}</>
              : <><EnlaceCine slug={sugerida.cine_slug} className="relative z-[2] hover:text-primary hover:underline focus-visible:outline-primary"><MarcaFavorito slug={sugerida.cine_slug} /> {sugerida.cine}</EnlaceCine>, {sesionCorta(sugerida.fecha_hora)}</>}
          </p>
        </div>
      {/* Capa sobre toda la celda: abre la vista rápida sin mover el scroll. El título (página completa) va encima */}
      <Link href={href} scroll={false} aria-label={`Vista rápida: ${pelicula.titulo}`} className="absolute inset-0 z-[1] rounded-2xl" />
    </li>
  );
}
