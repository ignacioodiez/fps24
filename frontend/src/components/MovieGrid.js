import Link from "next/link";
import { useRouter } from "next/navigation";
import { cleanCinemaName } from "@/utils/helpers";
import { REJILLA_CINES, SesionesCine } from "@/components/Sesiones";
import { useFavoritos } from "@/components/FavoritosProvider";
import { favoritosPrimero } from "@/lib/favoritos";
import { ChipDato } from "@/components/FichaPelicula";

const PALETTE_AQUAMARINE = "#42E2B8";

export default function MovieGrid({ 
  groupedMovies, 
  searchTerm, 
  selectedCinema,
  selectedDate
}) {
  const router = useRouter();
  const { favoritos } = useFavoritos();

  // Clic en la tarjeta: vista rápida (ruta interceptada, sin mover el scroll); Ctrl/Cmd o botón central: página
  // completa en pestaña nueva. Los enlaces y botones de dentro (título, póster, horas) gestionan su propio clic.
  // Es un onClick en la tarjeta y no una capa absolute encima: la capa tapaba la lista de pases y la rueda del
  // ratón desplazaba la página en vez de la lista.
  const abrirPelicula = (e, id) => {
    if (e.target.closest("a, button")) return;
    const url = `/pelicula/${id}`;
    if (e.ctrlKey || e.metaKey || e.button === 1) {
      window.open(url, "_blank", "noopener");
      return;
    }
    // Foco en el enlace del póster: al cerrar el modal vuelve ahí
    e.currentTarget.querySelector("a[data-vista-rapida]")?.focus({ preventScroll: true });
    router.push(url, { scroll: false });
  };

  // overscroll "contain" solo si la lista de pases desborda: en una lista corta bloquearía la rueda y la página
  // no bajaría con el cursor encima. Se recalcula en cada render (cambio de día, filtros).
  // shortcut: no se recalcula al redimensionar la ventana; si hiciera falta, un ResizeObserver.
  const contenerScroll = (lista) => {
    if (lista) lista.style.overscrollBehavior = lista.scrollHeight > lista.clientHeight ? "contain" : "";
  };

  // Día elegido como "YYYY-MM-DD" en hora local, para compararlo con fecha_estreno
  const diaElegido = selectedDate ? selectedDate.toLocaleDateString("sv-SE") : null;

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
          onClick={(e) => abrirPelicula(e, movie.id)}
          onAuxClick={(e) => e.button === 1 && abrirPelicula(e, movie.id)}
          className={`
            relative cursor-pointer bg-background rounded-3xl overflow-hidden border flex flex-col sm:flex-row 
            h-auto sm:h-64 
            transition-colors group
            ${movie.es_especial ? "border-primary" : "border-line hover:border-muted"}
          `}
        >
          {/* POSTER */}
          <div className="w-full sm:w-40 flex-shrink-0 relative h-64 sm:h-auto overflow-hidden bg-surface flex items-center justify-center">
            {/* Enlace accesible (teclado, lector de pantalla) a la vista rápida; con el ratón vale toda la tarjeta */}
            <Link href={`/pelicula/${movie.id}`} scroll={false} data-vista-rapida aria-label={`Vista rápida: ${movie.titulo}`} className="absolute inset-0" />
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

            {movie.fecha_estreno && movie.fecha_estreno === diaElegido && (
              <div className="absolute bottom-2 left-2 bg-estreno text-foreground text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full">
                Estreno
              </div>
            )}
          </div>

          {/* INFO SECTION */}
          {/* Lista de pases con scroll propio; si desborda, al llegar al final no arrastra la página */}
          <div ref={contenerScroll} className="flex-1 p-4 flex flex-col min-w-0 overflow-y-auto custom-scrollbar bg-background">
            
            <div className="mb-3 border-b border-line pb-2">
              {/* Título: <a> normal (navegación completa del documento, Next no la intercepta) a la página entera */}
              <h2 className="text-xl md:text-2xl font-display font-bold leading-tight text-foreground mb-1 truncate" title={movie.titulo}>
                <a href={`/pelicula/${movie.id}`} onClick={(e) => e.stopPropagation()} className="hover:text-primary transition-colors">
                  {movie.titulo}
                </a>
              </h2>
              
              <div className="flex flex-wrap items-center gap-2">
                {movie.es_especial && (
                  <span className="bg-primary text-white text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold tracking-wider">
                    Especial
                  </span>
                )}
                {movie.anio && <ChipDato>{movie.anio}</ChipDato>}
              </div>
            </div>

            {/* CINES Y SESIONES (mismo bloque que la vista rápida y la página completa) */}
            <div className="@container">
              <div className={REJILLA_CINES}>
                {/* Mis cines favoritos primero; el resto, en su orden (por primera sesión) */}
                {favoritosPrimero(Object.entries(movie.cines), ([, sessions]) => sessions[0].cine_slug, favoritos).map(([cinemaName, sessions]) => (
                  <SesionesCine key={cinemaName} cine={cinemaName} pases={sessions} />
                ))}
              </div>
            </div>

          </div>
        </div>
      ))}
    </div>
  );
}