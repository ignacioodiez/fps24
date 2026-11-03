import { useState, useRef, useEffect, useId } from "react";
import { cleanCinemaName } from "@/utils/helpers";

const CHIP = "px-3 py-1.5 rounded-lg text-xs font-bold border transition-colors";
const CHIP_ON = "bg-primary border-primary text-white";
const CHIP_OFF = "bg-background border-line text-foreground hover:bg-surface";
const ETIQUETA = "text-xs font-bold text-muted uppercase tracking-wider";

// Interruptor accesible: checkbox real (sr-only) delante del dibujo, para el foco y el lector de pantalla
function Interruptor({ checked, onChange, color, children }) {
  return (
    <label className="flex items-center justify-between gap-3 cursor-pointer group">
      <span className="flex items-center gap-2">{children}</span>
      <input type="checkbox" role="switch" className="sr-only peer" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span aria-hidden="true" className={`w-11 h-6 shrink-0 flex items-center rounded-full p-1 transition-colors peer-focus-visible:ring-2 peer-focus-visible:ring-primary peer-focus-visible:ring-offset-2 ${checked ? color : "bg-line"}`}>
        <span className={`bg-white w-4 h-4 rounded-full transform transition-transform ${checked ? "translate-x-5" : "translate-x-0"}`} />
      </span>
    </label>
  );
}

export default function FilterMenu({
  availableCinemas,
  selectedCinema,
  setSelectedCinema,
  timeRange,
  setTimeRange,
  spectatorOnly,
  setSpectatorOnly,
  onlySpecials,
  setOnlySpecials,
  resetFilters,
  sortBy,
  setSortBy
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [verCines, setVerCines] = useState(false);
  const [topPanel, setTopPanel] = useState(0);
  const menuRef = useRef(null);
  const idCines = useId();

  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const activeFiltersCount =
    (selectedCinema !== "Todos" ? 1 : 0) +
    (timeRange[0] > 6 || timeRange[1] < 24 ? 1 : 0) +
    (spectatorOnly ? 1 : 0) +
    (onlySpecials ? 1 : 0);

  return (
    <div className="relative z-50" ref={menuRef}>

      <style jsx>{`
        .range-slider-input {
          pointer-events: none;
          appearance: none;
          background: transparent;
        }
        .range-slider-input::-webkit-slider-thumb {
          pointer-events: auto;
          appearance: none;
          width: 20px;
          height: 20px;
          background: var(--primary);
          border: 2px solid white;
          border-radius: 50%;
          cursor: pointer;
          margin-top: -8px;
        }
        .range-slider-input::-moz-range-thumb {
          pointer-events: auto;
          width: 20px;
          height: 20px;
          background: var(--primary);
          border: 2px solid white;
          border-radius: 50%;
          cursor: pointer;
        }
      `}</style>

      {/* --- BOTÓN PRINCIPAL --- */}
      <button
        onClick={() => {
          let top = menuRef.current.getBoundingClientRect().top;
          // En móvil, al abrir, se sube la barra sticky hasta arriba para que el panel tenga todo el alto posible
          const barra = menuRef.current.closest(".sticky");
          if (!isOpen && barra && window.matchMedia("(max-width: 767px)").matches) {
            const bajada = barra.getBoundingClientRect().top;
            if (bajada > 0) {
              window.scrollBy({ top: bajada, behavior: "instant" });
              top -= bajada;
            }
          }
          // El panel cuelga de la barra: su alto debe caber en lo que queda de pantalla bajo él (top-14 = 56px)
          setTopPanel(top + 56);
          setIsOpen(!isOpen);
        }}
        aria-expanded={isOpen}
        className={`
          flex items-center gap-2 px-5 py-3 rounded-full font-bold transition-colors border
          ${isOpen || activeFiltersCount > 0
            ? "bg-primary text-white border-primary"
            : "bg-background text-foreground border-line hover:bg-surface"
          }
        `}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="4" x2="20" y1="21" y2="21"/><line x1="4" x2="20" y1="3" y2="3"/><line x1="10" x2="4" y1="14" y2="14"/><line x1="20" x2="14" y1="14" y2="14"/><line x1="14" x2="20" y1="7" y2="7"/><line x1="4" x2="10" y1="7" y2="7"/>
        </svg>
        <span>Filtros</span>

        {activeFiltersCount > 0 && (
          <span className="bg-white text-primary text-[10px] w-5 h-5 flex items-center justify-center rounded-full font-black">
            {activeFiltersCount}
          </span>
        )}
      </button>

      {/* --- MENÚ DESPLEGABLE --- */}
      {/* En móvil, sin dvh (iOS < 15.4) la regla max-md se descarta y queda max-h-[80vh] */}
      {isOpen && (
        <div style={{ "--top-panel": `${topPanel}px` }} className={`
          absolute top-14 right-0 w-80 md:w-96
          bg-background border border-line rounded-2xl
          animate-in fade-in slide-in-from-top-2 z-50
          max-h-[80vh] max-md:max-h-[min(80vh,calc(100dvh-var(--top-panel)-1rem-env(safe-area-inset-bottom)))]
          flex flex-col overflow-hidden
        `}>

          {/* 1. INTERRUPTORES: fijos arriba, no dependen del scroll */}
          <div className="shrink-0 px-5 py-3 border-b border-line">
            <div className="space-y-3">
              <Interruptor checked={spectatorOnly} onChange={setSpectatorOnly} color="bg-accent">
                <span className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">Solo Día del Espectador</span>
                <span aria-hidden="true" className="bg-accent-soft text-foreground text-[9px] px-1.5 rounded border border-accent font-bold">%</span>
              </Interruptor>
              <Interruptor checked={onlySpecials} onChange={setOnlySpecials} color="bg-primary">
                <span className="text-sm font-bold text-foreground group-hover:text-primary transition-colors">Solo Eventos Especiales</span>
                <span aria-hidden="true" className="bg-primary-soft text-primary text-[9px] px-1.5 rounded border border-primary">★</span>
              </Interruptor>
            </div>
          </div>

          {/* 2. CUERPO DESPLAZABLE: cines (plegados), hora y orden */}
          <div className="min-h-0 overflow-y-auto overscroll-contain custom-scrollbar px-5 py-3 space-y-4">

            {/* CINES */}
            <div>
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className={ETIQUETA}>Cine</p>
                  <p className="text-sm font-bold text-foreground truncate">
                    {selectedCinema === "Todos" ? "Todos los cines" : cleanCinemaName(selectedCinema)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setVerCines(!verCines)}
                  aria-expanded={verCines}
                  aria-controls={idCines}
                  className={`${CHIP} ${CHIP_OFF} shrink-0`}
                >
                  {verCines ? "Ocultar" : "Elegir cine"}
                </button>
              </div>
              {verCines && (
                <div id={idCines} role="group" aria-label="Cines" className="flex flex-wrap gap-2 mt-3">
                  {availableCinemas.map((cine) => (
                    <button
                      key={cine}
                      type="button"
                      onClick={() => setSelectedCinema(cine)}
                      aria-pressed={selectedCinema === cine}
                      className={`${CHIP} ${selectedCinema === cine ? CHIP_ON : CHIP_OFF}`}
                    >
                      {cleanCinemaName(cine)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* RANGO DE HORAS */}
            <div>
              <div className="flex justify-between items-center">
                <p className={ETIQUETA}>Hora de la sesión</p>
                <span className="text-xs text-foreground font-bold bg-surface px-2 py-0.5 rounded border border-line">
                  {timeRange[0]}:00 - {timeRange[1]}:00
                </span>
              </div>

              <div className="relative h-8 flex items-center justify-center select-none">
                <div className="absolute w-full h-1 bg-line rounded-full"></div>
                <div
                  className="absolute h-1 bg-primary rounded-full"
                  style={{
                    left: `${((timeRange[0] - 6) / 18) * 100}%`,
                    right: `${100 - ((timeRange[1] - 6) / 18) * 100}%`
                  }}
                ></div>
                <input
                  type="range" min="6" max="24" step="1"
                  aria-label="Hora de inicio"
                  value={timeRange[0]}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    if (val < timeRange[1]) setTimeRange([val, timeRange[1]]);
                  }}
                  className="range-slider-input absolute w-full h-1 z-20"
                />
                 <input
                  type="range" min="6" max="24" step="1"
                  aria-label="Hora de fin"
                  value={timeRange[1]}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    if (val > timeRange[0]) setTimeRange([timeRange[0], val]);
                  }}
                  className="range-slider-input absolute w-full h-1 z-20"
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted">
                <span>06:00</span>
                <span>Mediodía</span>
                <span>00:00</span>
              </div>
            </div>

            {/* ORDEN */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <p className={ETIQUETA}>Ordenar películas</p>
                {activeFiltersCount > 0 && (
                  <button type="button" onClick={resetFilters} className="text-xs text-red-600 hover:text-red-700 underline">
                    Borrar filtros
                  </button>
                )}
              </div>
              <div className="flex gap-2">
                {[["sesiones", "Más sesiones"], ["nota", "Nota TMDB"], ["titulo", "A–Z"]].map(([valor, texto]) => (
                  <button
                    key={valor}
                    type="button"
                    onClick={() => setSortBy(valor)}
                    aria-pressed={sortBy === valor}
                    className={`${CHIP} ${sortBy === valor ? CHIP_ON : CHIP_OFF}`}
                  >
                    {texto}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
