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
      <div className="col-span-full text-center py-24 bg-gray-800/30 rounded-3xl border border-gray-700/50 border-dashed max-w-9xl mx-auto">
        <p className="text-3xl text-gray-500 font-medium">
          {searchTerm 
            ? "🔍 No encuentro esa peli..." 
            : (selectedCinema !== "Todos" ? `😴 No hay sesiones en ${cleanCinemaName(selectedCinema)} hoy.` : "😴 No hay sesiones para este día.")
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
            bg-gray-800 rounded-3xl overflow-hidden shadow-2xl border flex flex-col sm:flex-row 
            h-auto sm:h-64 
            transition-all hover:bg-gray-750 group
            ${movie.es_especial ? "border-purple-500/60 shadow-purple-900/30" : "border-gray-700 hover:border-gray-500"}
          `}
        >
          {/* POSTER */}
          <Link href={`/pelicula/${movie.id}`} className="w-full sm:w-40 flex-shrink-0 relative h-64 sm:h-auto overflow-hidden bg-gray-900 flex items-center justify-center cursor-pointer">
            {movie.poster ? (
              <img
                src={movie.poster}
                alt={movie.titulo}
                className="w-full h-full object-cover opacity-95 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-gray-600 p-4 text-center">
                <span className="text-xs font-bold uppercase tracking-wider opacity-70">Sin Imagen</span>
              </div>
            )}
            
            {movie.nota > 0 && (
              <div className="absolute top-2 left-2 bg-black/80 backdrop-blur-md text-yellow-400 text-xs font-bold px-2 py-1 rounded-lg flex items-center gap-1 shadow-lg border border-white/10">
                ⭐ {movie.nota.toFixed(1)}
              </div>
            )}
          </Link>

          {/* INFO SECTION */}
          <div className="flex-1 p-4 flex flex-col min-w-0 overflow-y-auto custom-scrollbar bg-gray-800">
            
            <div className="mb-3 border-b border-gray-700 pb-2">
              <Link href={`/pelicula/${movie.id}`}>
                <h2 className="text-xl md:text-2xl font-kanit font-bold leading-tight text-yellow-400 mb-1 truncate hover:text-yellow-400 transition-colors cursor-pointer" title={movie.titulo}>
                  {movie.titulo}
                </h2>
              </Link>
              
              <div className="flex flex-wrap items-center gap-2">
                {movie.es_especial && (
                  <span className="bg-purple-600 text-white text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold tracking-wider shadow-lg shadow-purple-900/50">
                    Especial
                  </span>
                )}
                {movie.anio && (
                  <span className="text-gray-300 text-xs font-mono bg-gray-700 px-2 py-0.5 rounded-md border border-gray-600">
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
                      flex items-center justify-between px-2.5 py-1.5 rounded-lg border transition-all w-fit
                      ${isPromoDay 
                        ? "bg-gradient-to-r from-teal-400 to-teal-700 text-white border-gray-500/50 hover:border-gray-400" // ✨ TEAL STYLE
                        : "bg-gradient-to-r from-gray-300 to-gray-400 text-white border-gray-500/50 hover:border-gray-400" // NORMAL STYLE
                      }
                    `}>
                      <h3 className={`
                        text-xs font-bold uppercase tracking-wide flex items-center gap-2
                        ${isPromoDay ? "text-black" : "text-black"}
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
                            px-3 py-1 rounded-lg text-xs font-semibold transition-all transform hover:scale-105 active:scale-95 flex items-center gap-2 shadow-md border
                            ${session.es_evento_especial 
                              ? 'bg-gradient-to-r from-purple-900 to-indigo-900 text-white border-purple-500/50 hover:border-purple-400' 
                              : 'bg-gray-700 text-gray-300 hover:bg-gray-600 border-gray-600 hover:text-white' // Standard gray style
                            }
                          `}
                        >
                          <span className="text-sm">{extractTime(session.fecha_hora)}</span>
                          
                          {/* We only keep the VO tag, price tag removed as header implies discount */}
                          {session.idioma === 'VOSE' && (
                            <span className="text-[9px] bg-black/30 px-1 rounded font-medium text-gray-400 border border-white/5">VO</span>
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