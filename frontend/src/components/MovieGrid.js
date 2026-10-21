import Link from "next/link";
import { cleanCinemaName, extractTime, isDiaEspectador } from "@/utils/helpers";

const PALETTE_AQUAMARINE = "#42E2B8";

export default function MovieGrid({ 
  groupedMovies, 
  searchTerm, 
  selectedCinema 
}) {
  if (groupedMovies.length === 0) {
    return (
      <div className="col-span-full text-center py-24 bg-surface rounded-3xl border border-line border-dashed max-w-9xl mx-auto">
        <p className="text-3xl text-muted font-medium">
          {searchTerm 
            ? "No encuentro esa peli..." 
            : (selectedCinema !== "Todos" ? `No hay sesiones en ${cleanCinemaName(selectedCinema)} hoy.` : "No hay sesiones para este día.")
          }
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 max-w-9xl mx-auto px-2 md:px-0">
      {groupedMovies.map((movie, index) => (
        <div
          key={index}
          className={`
            bg-background rounded-3xl overflow-hidden border flex flex-col sm:flex-row 
            h-auto sm:h-64 
            transition-colors group
            ${movie.es_especial ? "border-primary" : "border-line hover:border-muted"}
          `}
        >
          {/* POSTER */}
          <Link href={`/pelicula/${movie.id}`} className="w-full sm:w-40 flex-shrink-0 relative h-64 sm:h-auto overflow-hidden bg-surface flex items-center justify-center cursor-pointer">
            {movie.poster ? (
              <img
                src={movie.poster}
                alt={movie.titulo}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-muted p-4 text-center">
                <span className="text-xs font-bold uppercase tracking-wider opacity-70">Sin Imagen</span>
              </div>
            )}
            
            {movie.nota > 0 && (
              <div className="absolute top-2 left-2 bg-background text-foreground text-xs font-bold px-2 py-1 rounded-lg flex items-center gap-1 border border-line">
                {movie.nota.toFixed(1)}
              </div>
            )}
          </Link>

          {/* INFO SECTION */}
          <div className="flex-1 p-4 flex flex-col min-w-0 overflow-y-auto custom-scrollbar bg-background">
            
            <div className="mb-3 border-b border-line pb-2">
              <Link href={`/pelicula/${movie.id}`}>
                <h2 className="text-xl md:text-2xl font-display font-bold leading-tight text-foreground mb-1 truncate hover:text-primary transition-colors cursor-pointer" title={movie.titulo}>
                  {movie.titulo}
                </h2>
              </Link>
              
              <div className="flex flex-wrap items-center gap-2">
                {movie.es_especial && (
                  <span className="bg-primary text-white text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold tracking-wider">
                    Especial
                  </span>
                )}
                {movie.anio && (
                  <span className="text-muted text-xs bg-surface px-2 py-0.5 rounded-md border border-line">
                    {movie.anio}
                  </span>
                )}
              </div>
            </div>

            {/* CINEMAS & SESSIONS */}
            <div className="space-y-3">
              {Object.entries(movie.cines).map(([cinemaName, sessions]) => {
                
                // --- 🧠 LOGIC CHANGE: Check discount on the Cinema Header instead of per session ---
                // We take the first session date to determine if today is Spectator Day for this cinema
                const firstSession = sessions[0]; 
                const isPromoDay = isDiaEspectador(cinemaName, firstSession?.fecha_hora);

                return (
                  <div key={cinemaName} className="flex flex-col gap-1.5">
                    
                    {/* CINEMA HEADER CARD */}
                    <div className={`
                      flex items-center justify-between px-2.5 py-1.5 rounded-lg border w-fit
                      ${isPromoDay 
                        ? "bg-accent text-foreground border-accent" // ✨ TEAL STYLE
                        : "bg-surface text-foreground border-line" // NORMAL STYLE
                      }
                    `}>
                      <h3 className={`
                        text-xs font-bold uppercase tracking-wide flex items-center gap-2
                        ${isPromoDay ? "text-foreground" : "text-foreground"}
                      `}>
                        {cleanCinemaName(cinemaName)}
                      </h3>

                      {/* PROMO BADGE IN HEADER */}
                      
                    </div>
                    
                    {/* TIME BUTTONS */}
                    <div className={`flex flex-wrap gap-2 `}>
                      {sessions.map((session) => (
                        <a
                          key={session.id}
                          href={session.link_compra}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`
                            px-3 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 border
                            ${session.es_evento_especial 
                              ? 'bg-primary-soft text-primary border-primary hover:bg-primary hover:text-white' 
                              : 'bg-background text-foreground border-line hover:border-primary hover:text-primary' // Standard gray style
                            }
                          `}
                        >
                          <span className="text-sm">{extractTime(session.fecha_hora)}</span>
                          
                          {/* We only keep the VO tag, price tag removed as header implies discount */}
                          {session.idioma === 'VOSE' && (
                            <span className="text-[9px] bg-surface px-1 rounded font-medium text-muted border border-line">VO</span>
                          )}
                        </a>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

          </div>
        </div>
      ))}
    </div>
  );
}