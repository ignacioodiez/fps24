import { isSameDay } from "@/utils/helpers";

export default function DateSelector({ 
  visibleDays, 
  selectedDate, 
  setSelectedDate, 
  weekOffset, 
  changeWeek, 
  hasMoreDays 
}) {
  return (
    // ✅ MANTENEMOS EL ARREGLO: 'py-4' para que el zoom no corte el botón
    <div className="flex flex-nowrap overflow-x-auto justify-start md:justify-center items-center gap-3 py-4 px-2 custom-scrollbar">
      
      {weekOffset > 0 && (
        <button 
          onClick={() => changeWeek(-1)} 
          className="flex-shrink-0 h-16 w-12 md:h-20 md:w-14 rounded-2xl bg-gray-800/50 border border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-yellow-400 hover:border-yellow-400/50 transition-all flex items-center justify-center backdrop-blur-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>
      )}

      {visibleDays.map((dateStr, index) => {
        const active = isSameDay(dateStr, selectedDate);
        return (
          <button
            key={index}
            onClick={() => setSelectedDate(new Date(dateStr))}
            // ✅ MANTENEMOS EL ARREGLO: 'flex-shrink-0' para que no se aplasten
            className={`
              flex flex-col items-center justify-center w-16 md:w-20 py-3 rounded-2xl transition-all duration-300 flex-shrink-0
              ${active
                // 🔙 VOLVEMOS AL ESTILO ORIGINAL (Gradiente gris/blanco)
                ? "bg-gradient-to-br from-gray-100 to-gray-500 text-black shadow-lg shadow-black-500/40 ring-2 ring-black-300 transform -translate-y-1 scale-105"
                : "bg-gray-800/50 text-gray-200 hover:bg-gray-800 hover:text-white backdrop-blur-sm border border-gray-700 hover:border-gray-500"
              }
            `}
          >
            <span className="text-xs font-semibold uppercase tracking-wide opacity-90">
              {new Date(dateStr).toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', '')}
            </span>
            <span className="text-2xl md:text-3xl font-bold mt-0.5">
              {new Date(dateStr).getDate()}
            </span>
            
            {active && (
              <div className="w-1.5 h-1.5 bg-black rounded-full mt-1"></div>
            )}
          </button>
        );
      })}

      {hasMoreDays && (
        <button 
          onClick={() => changeWeek(1)} 
          className="flex-shrink-0 h-16 w-12 md:h-20 md:w-14 rounded-2xl bg-gray-800/50 border border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-yellow-400 hover:border-yellow-400/50 transition-all flex items-center justify-center backdrop-blur-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      )}
    </div>
  );
}