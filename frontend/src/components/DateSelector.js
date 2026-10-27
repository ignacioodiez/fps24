"use client";

import { useCallback, useRef, useState } from "react";
import { CalendarDays } from "lucide-react";
import { isSameDay } from "@/utils/helpers";
import { etiquetaRelativa, hoyMadrid, rotuloMes } from "@/lib/fechasMadrid";
import CalendarioDias from "@/components/CalendarioDias";

// fecha_hora es hora de Madrid sin zona: sus 10 primeros caracteres son el día en Madrid
const clave = (dateStr) => dateStr.slice(0, 10);

export default function DateSelector({ 
  visibleDays, 
  allDays,
  selectedDate, 
  setSelectedDate, 
  elegirDia,
  weekOffset, 
  changeWeek, 
  hasMoreDays 
}) {
  const [abierto, setAbierto] = useState(false);
  const boton = useRef(null);
  const cerrar = useCallback(() => {
    setAbierto(false);
    boton.current?.focus();
  }, []);
  // Solo se pinta con días, que llegan por fetch en cliente: no hay "hoy" de servidor que hidratar
  const hoy = hoyMadrid();
  const seleccionado = allDays.find((d) => isSameDay(d, selectedDate));

  return (
    <div className="relative">
    <div className="flex items-center justify-between gap-3 px-2">
      {/* shortcut: rótulo por la página de 7 días visible, no por la parte desplazada en móvil */}
      <p className="text-sm font-bold text-foreground" aria-live="polite">
        {visibleDays.length > 0 && rotuloMes(clave(visibleDays[0]), clave(visibleDays.at(-1)))}
      </p>
      <button
        ref={boton}
        onClick={() => (abierto ? cerrar() : setAbierto(true))}
        aria-label="Abrir calendario"
        aria-haspopup="dialog"
        aria-expanded={abierto}
        className={`flex-shrink-0 p-2 rounded-full border transition-colors ${abierto ? "border-primary text-primary" : "border-line text-muted hover:text-primary hover:border-primary"}`}
      >
        <CalendarDays className="w-5 h-5" />
      </button>
    </div>

    {abierto && (
      <CalendarioDias
        hoy={hoy}
        conSesiones={allDays.map(clave)}
        seleccionado={seleccionado && clave(seleccionado)}
        onElegir={(d) => {
          elegirDia(allDays.find((x) => clave(x) === d));
          cerrar();
        }}
        onCerrar={cerrar}
        botonRef={boton}
      />
    )}

    {/* ✅ MANTENEMOS EL ARREGLO: 'py-4' para que el zoom no corte el botón */}
    <div className="flex flex-nowrap overflow-x-auto justify-start md:justify-center items-center gap-3 py-4 px-2 custom-scrollbar">
      
      {weekOffset > 0 && (
        <button 
          onClick={() => changeWeek(-1)} 
          className="flex-shrink-0 h-16 w-12 md:h-20 md:w-14 rounded-2xl bg-background border border-line text-muted hover:text-primary hover:border-primary transition-colors flex items-center justify-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
          </svg>
        </button>
      )}

      {visibleDays.map((dateStr, index) => {
        const active = isSameDay(dateStr, selectedDate);
        const etiqueta = etiquetaRelativa(clave(dateStr), hoy);
        return (
          <button
            key={index}
            onClick={() => setSelectedDate(new Date(dateStr))}
            // ✅ MANTENEMOS EL ARREGLO: 'flex-shrink-0' para que no se aplasten
            className={`
              relative flex flex-col items-center justify-center w-16 md:w-20 py-3 rounded-2xl transition-colors flex-shrink-0 border
              ${active
                // 🔙 VOLVEMOS AL ESTILO ORIGINAL (Gradiente gris/blanco)
                ? "bg-primary text-white border-primary"
                : "bg-background text-foreground border-line hover:bg-surface"
              }
            `}
          >
            {etiqueta && (
              <span className={`absolute -top-2 left-1/2 -translate-x-1/2 px-1.5 py-px rounded-full text-[10px] font-bold leading-tight whitespace-nowrap border ${active ? "bg-white text-primary border-primary" : "bg-primary text-white border-primary"}`}>
                {etiqueta}
              </span>
            )}
            <span className="text-xs font-semibold uppercase tracking-wide opacity-90">
              {new Date(dateStr).toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', '')}
            </span>
            <span className="text-2xl md:text-3xl font-bold mt-0.5">
              {new Date(dateStr).getDate()}
            </span>
            
            {active && (
              <div className="w-1.5 h-1.5 bg-white rounded-full mt-1"></div>
            )}
          </button>
        );
      })}

      {hasMoreDays && (
        <button 
          onClick={() => changeWeek(1)} 
          className="flex-shrink-0 h-16 w-12 md:h-20 md:w-14 rounded-2xl bg-background border border-line text-muted hover:text-primary hover:border-primary transition-colors flex items-center justify-center"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
          </svg>
        </button>
      )}
    </div>
    </div>
  );
}
