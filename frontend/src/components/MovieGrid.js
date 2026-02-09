import Link from "next/link";
import { cleanCinemaName, extractTime } from "@/utils/helpers";

export default function MovieGrid({ 
  groupedMovies, 
  searchTerm, 
  selectedCinema 
}) {
  // Manejo de estado vacío
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
          {/* PÓSTER (ENLAZADO A DETALLE) 🔗 */}
          <Link href={`/pelicula/${movie.id}`} className="w-full sm:w-40 flex-shrink-0 relative h-64 sm:h-auto overflow-hidden bg-gray-900 flex items-center justify-center cursor-pointer">
            {movie.poster ? (
              <img
                src={movie.poster}
                alt={movie.titulo}
                className="w-full h-full object-cover opacity-95 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-gray-600 p-4 text-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 mb-2 opacity-50">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                </svg>
                <span className="text-xs font-bold uppercase tracking-wider opacity-70">Sin Imagen</span>
              </div>
            )}
            
            {/* Nota TMDB */}
            {movie.nota > 0 && (
              <div className="absolute top-2 left-2 bg-black/80 backdrop-blur-md text-yellow-400 text-xs font-bold px-2 py-1 rounded-lg flex items-center gap-1 shadow-lg border border-white/10">
                ⭐ {movie.nota.toFixed(1)}
              </div>
            )}
          </Link>

          {/* Info */}
          <div className="flex-1 p-4 flex flex-col min-w-0 overflow-y-auto custom-scrollbar bg-gray-800">
            
            {/* Header (TÍTULO ENLAZADO A DETALLE) 🔗 */}
            <div className="mb-3 border-b border-gray-700 pb-2">
              <Link href={`/pelicula/${movie.id}`}>
                <h2 className="text-xl md:text-2xl font-raleway font-bold leading-tight text-white mb-1 truncate hover:text-yellow-400 transition-colors cursor-pointer" title={movie.titulo}>
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

            {/* Cinemas & Times */}
            <div className="space-y-3">
              {Object.entries(movie.cines).map(([cinemaName, sessions]) => (
                <div key={cinemaName} className="flex flex-col gap-1">
                  
                  <h3 className="text-yellow-500 font-semibold text-xs uppercase tracking-wide flex items-center gap-2">
                    📍 {cleanCinemaName(cinemaName)}
                  </h3>
                  
                  <div className="flex flex-wrap gap-2">
                    {sessions.map((session) => (
                      <a
                        key={session.id}
                        href={session.link_compra}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`
                          px-3 py-1 rounded-lg text-xs font-semibold transition-all transform hover:scale-105 active:scale-95 flex items-center gap-2 shadow-md
                          ${session.es_evento_especial 
                            ? 'bg-gradient-to-r from-purple-900 to-indigo-900 text-white border border-purple-500/50 hover:border-purple-400' 
                            : (session.idioma === 'VOSE' 
                              ? 'bg-gray-700 text-white hover:bg-gray-600 border border-gray-500'
                              : 'bg-gray-700 text-gray-300 hover:bg-gray-600 border border-gray-600')
                          }
                        `}
                      >
                        <span className="text-sm">{extractTime(session.fecha_hora)}</span>
                        {session.idioma === 'VOSE' && (
                          <span className="text-[9px] bg-black/30 px-1 rounded font-medium text-gray-400 border border-white/5">VO</span>
                        )}
                      </a>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}