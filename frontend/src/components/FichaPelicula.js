// Datos de la ficha de una película con el estilo de la portada. Los usan la vista rápida (ModalPelicula)
// y la página completa, para que no haya dos versiones del mismo bloque.

const VOTOS_MIN = 10;

// Nota de TMDB: insignia como la del póster de la cartelera; apagada ("★ 9.0 · 6 votos") si hay menos de
// VOTOS_MIN votos; nada si no hay nota. Sin dato de votos se muestra normal.
export function NotaPelicula({ nota, votos }) {
  if (!(nota > 0)) return null;
  if (votos != null && votos < VOTOS_MIN) {
    return <span className="text-xs text-muted">★ {nota.toFixed(1)} · {votos} {votos === 1 ? "voto" : "votos"}</span>;
  }
  return (
    <span className="bg-background text-foreground text-xs font-bold px-2 py-1 rounded-lg border border-line">
      ★ {nota.toFixed(1)}
    </span>
  );
}

// Chip de dato (año, duración), como el del año en la tarjeta de la cartelera
export function ChipDato({ children }) {
  return <span className="text-muted text-xs bg-surface px-2 py-0.5 rounded-md border border-line">{children}</span>;
}

export const duracionTexto = (min) => (min >= 60 ? `${Math.floor(min / 60)} h ${min % 60} min` : `${min} min`);

export function LineaDireccion({ director, className = "" }) {
  if (!director) return null;
  return (
    <p className={`text-sm text-muted ${className}`}>
      Dirección: <span className="text-foreground font-semibold">{director}</span>
    </p>
  );
}

// Géneros ("Drama, Bélica") como chips redondos
export function ChipsGeneros({ generos, className = "" }) {
  if (!generos) return null;
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {generos.split(",").map((g) => (
        <span key={g} className="text-xs border border-line bg-surface px-2 py-1 rounded-full text-muted">{g.trim()}</span>
      ))}
    </div>
  );
}
