import { useState, useRef, useEffect } from "react";
import { cleanCinemaName } from "@/utils/helpers";
import * as gtag from "@/lib/gtag"; // 👈 AÑADE ESTO AL INICIO

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
  const menuRef = useRef(null);

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
          background: #a5a5a5;
          border: 2px solid white;
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
          margin-top: -8px;
        }
        .range-slider-input::-moz-range-thumb {
          pointer-events: auto;
          width: 20px;
          height: 20px;
          background: #14b8a6;
          border: 2px solid white;
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }
      `}</style>

      {/* --- BOTÓN PRINCIPAL --- */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          flex items-center gap-2 px-5 py-3 rounded-full font-bold transition-all shadow-lg border
          ${isOpen || activeFiltersCount > 0
            ? "bg-gradient-to-br from-gray-100 to-gray-500 text-black shadow-lg shadow-black-500/40 ring-2 ring-black-300 transform -translate-y-1 scale-105" 
            : "bg-gray-800 text-gray-300 border-gray-600 hover:border-gray-400 hover:text-white"
          }
        `}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="4" x2="20" y1="21" y2="21"/><line x1="4" x2="20" y1="3" y2="3"/><line x1="10" x2="4" y1="14" y2="14"/><line x1="20" x2="14" y1="14" y2="14"/><line x1="14" x2="20" y1="7" y2="7"/><line x1="4" x2="10" y1="7" y2="7"/>
        </svg>
        <span>Filtros</span>
        
        {activeFiltersCount > 0 && (
          <span className="bg-white text-teal-700 text-[10px] w-5 h-5 flex items-center justify-center rounded-full font-black">
            {activeFiltersCount}
          </span>
        )}
      </button>

      {/* --- MENÚ DESPLEGABLE (MODAL) --- */}
      {isOpen && (
        <div className={`
          absolute top-14 right-0 w-80 md:w-96 
          bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl 
          animate-in fade-in slide-in-from-top-2 z-50
          max-h-[80vh] flex flex-col overflow-hidden /* 👈 Clave: flex-col y overflow-hidden aquí */
        `}>
          
          {/* 1. CABECERA FIJA (No se mueve) */}
          <div className="flex justify-between items-center p-6 pb-4 border-b border-gray-800 bg-gray-900 shrink-0">
            <h3 className="text-lg font-bold text-white">Configurar Búsqueda</h3>
            {activeFiltersCount > 0 && (
              <button 
                onClick={resetFilters}
                className="text-xs text-red-400 hover:text-red-300 underline"
              >
                Borrar todo
              </button>
            )}
          </div>

          {/* 2. CUERPO SCROLLABLE (Solo se mueve esto) */}
          <div className="overflow-y-auto custom-scrollbar p-6 pt-4 space-y-8">

            {/* ORDEN */}
<div>
  <label className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 block">
    Ordenar películas
  </label>

  <div className="flex gap-2">
    <button
      onClick={() => setSortBy("sesiones")}
      className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all
        ${sortBy === "sesiones"
          ? "bg-yellow-500 border-yellow-500 text-black"
          : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-400 hover:text-white"
        }`}
    >
      Más sesiones
    </button>

    <button
      onClick={() => setSortBy("nota")}
      className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all
        ${sortBy === "nota"
          ? "bg-yellow-500 border-yellow-500 text-black"
          : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-400 hover:text-white"
        }`}
    >
      Nota TMDB
    </button>

    <button
      onClick={() => setSortBy("titulo")}
      className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all
        ${sortBy === "titulo"
          ? "bg-yellow-500 border-yellow-500 text-black"
          : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-400 hover:text-white"
        }`}
    >
      A–Z
    </button>
  </div>
</div>
            
            
            {/* SELECCIÓN DE CINE */}
            <div>
              <label className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 block">
                Elige tu Cine
              </label>
              <div className="flex flex-wrap gap-2">
                {availableCinemas.map((cine) => (
                  <button
                    key={cine}
                    onClick={() => setSelectedCinema(cine)}
                    className={`
                      px-3 py-1.5 rounded-lg text-xs font-bold border transition-all
                      ${selectedCinema === cine
                        ? "bg-yellow-500 border-yellow-500 text-black shadow-lg shadow-yellow-500/20"
                        : "bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-400 hover:text-white"
                      }
                    `}
                  >
                    {cleanCinemaName(cine)}
                  </button>
                ))}
              </div>
            </div>

            {/* RANGO DE HORAS */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Hora de la sesión</label>
                <span className="text-xs font-mono text-gray-200 font-bold bg-gray-900/30 px-2 py-0.5 rounded border border-yellow-500/30">
                  {timeRange[0]}:00 - {timeRange[1]}:00
                </span>
              </div>
              
              <div className="relative h-12 flex items-center justify-center select-none">
                <div className="absolute w-full h-1 bg-gray-700 rounded-full"></div>
                <div 
                  className="absolute h-1 bg-yellow-500 rounded-full"
                  style={{
                    left: `${((timeRange[0] - 6) / 18) * 100}%`,
                    right: `${100 - ((timeRange[1] - 6) / 18) * 100}%`
                  }}
                ></div>
                <input 
                  type="range" min="6" max="24" step="1"
                  value={timeRange[0]}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    if (val < timeRange[1]) setTimeRange([val, timeRange[1]]);
                  }}
                  className="range-slider-input absolute w-full h-1 z-20"
                />
                 <input 
                  type="range" min="6" max="24" step="1"
                  value={timeRange[1]}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    if (val > timeRange[0]) setTimeRange([timeRange[0], val]);
                  }}
                  className="range-slider-input absolute w-full h-1 z-20"
                />
              </div>
              <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                <span>06:00</span>
                <span>Mediodía</span>
                <span>00:00</span>
              </div>
            </div>

            {/* TOGGLES */}
            <div className="space-y-3 pt-4 border-t border-gray-800">
              <label className="flex items-center justify-between cursor-pointer group">
                <span className="flex items-center gap-2">
                  <span className="text-sm font-bold text-gray-300 group-hover:text-white transition-colors">Solo Día del Espectador</span>
                  <span className="bg-teal-900 text-teal-300 text-[9px] px-1.5 rounded border border-teal-700 font-bold">%</span>
                </span>
                <div className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${spectatorOnly ? "bg-teal-600" : "bg-gray-700"}`}>
                  <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${spectatorOnly ? "translate-x-5" : "translate-x-0"}`}></div>
                </div>
                <input type="checkbox" className="hidden" checked={spectatorOnly} onChange={(e) => setSpectatorOnly(e.target.checked)} />
              </label>

              <label className="flex items-center justify-between cursor-pointer group">
                  <span className="flex items-center gap-2">
                  <span className="text-sm font-bold text-gray-300 group-hover:text-white transition-colors">Solo Eventos Especiales</span>
                  <span className="bg-purple-900 text-purple-300 text-[9px] px-1.5 rounded border border-purple-700">★</span>
                </span>
                <div className={`w-11 h-6 flex items-center rounded-full p-1 transition-colors ${onlySpecials ? "bg-purple-600" : "bg-gray-700"}`}>
                  <div className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${onlySpecials ? "translate-x-5" : "translate-x-0"}`}></div>
                </div>
                <input type="checkbox" className="hidden" checked={onlySpecials} onChange={(e) => setOnlySpecials(e.target.checked)} />
              </label>
            </div>

          </div>
        </div>
      )}
    </div>
  );

  
}