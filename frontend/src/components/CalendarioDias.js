"use client";

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { cuatroSemanas, diaCompleto, formato, rotuloMes } from "@/lib/fechasMadrid";

const SEMANA = [["L", "lunes"], ["M", "martes"], ["X", "miércoles"], ["J", "jueves"], ["V", "viernes"], ["S", "sábado"], ["D", "domingo"]];
const MOVER = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };

// Popover (hoja inferior en móvil) con las 4 semanas desde el lunes de hoy. conSesiones: claves "AAAA-MM-DD" ordenadas.
export default function CalendarioDias({ hoy, conSesiones, seleccionado, onElegir, onCerrar, botonRef }) {
  const dias = cuatroSemanas(hoy);
  const hay = new Set(conSesiones);
  const ultimo = conSesiones.at(-1);
  const [foco, setFoco] = useState(dias.includes(seleccionado) ? seleccionado : hoy);
  const celdas = useRef({});
  const panel = useRef(null);

  useEffect(() => celdas.current[foco]?.focus(), [foco]);

  useEffect(() => {
    const tecla = (e) => e.key === "Escape" && onCerrar();
    const fuera = (e) => !panel.current.contains(e.target) && !botonRef.current.contains(e.target) && onCerrar();
    document.addEventListener("keydown", tecla);
    document.addEventListener("mousedown", fuera);
    return () => {
      document.removeEventListener("keydown", tecla);
      document.removeEventListener("mousedown", fuera);
    };
  }, [onCerrar, botonRef]);

  const teclas = (e) => {
    const i = dias.indexOf(foco);
    const destino = e.key === "Home" ? i - (i % 7) : e.key === "End" ? i - (i % 7) + 6 : MOVER[e.key] != null ? i + MOVER[e.key] : null;
    if (destino == null) return;
    e.preventDefault();
    if (dias[destino]) setFoco(dias[destino]);
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-50 md:hidden" aria-hidden="true" />
      <div
        ref={panel}
        role="dialog"
        aria-labelledby="calendario-titulo"
        className="fixed inset-x-0 bottom-0 z-50 rounded-t-2xl md:absolute md:inset-x-auto md:bottom-auto md:right-2 md:top-full md:mt-1 md:w-80 md:rounded-2xl bg-background border border-line shadow-xl p-4 pb-6 md:pb-4"
      >
        <div className="flex items-center justify-between mb-3">
          <h2 id="calendario-titulo" className="font-bold text-foreground">{rotuloMes(dias[0], dias[27])}</h2>
          <button onClick={onCerrar} aria-label="Cerrar calendario" className="p-1 rounded-full text-muted hover:text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div role="grid" aria-labelledby="calendario-titulo" onKeyDown={teclas} className="grid gap-1">
          <div role="row" className="grid grid-cols-7 gap-1">
            {SEMANA.map(([letra, nombre]) => (
              <div key={nombre} role="columnheader" aria-label={nombre} className="text-center text-xs font-semibold text-muted py-1">
                {letra}
              </div>
            ))}
          </div>
          {[0, 7, 14, 21].map((ini) => (
            <div key={ini} role="row" className="grid grid-cols-7 gap-1">
              {dias.slice(ini, ini + 7).map((d) => {
                const activo = hay.has(d);
                const elegido = d === seleccionado;
                const esHoy = d === hoy;
                const numero = Number(d.slice(8));
                return (
                  <div key={d} role="gridcell" aria-selected={elegido}>
                    <button
                      ref={(el) => (celdas.current[d] = el)}
                      tabIndex={d === foco ? 0 : -1}
                      aria-disabled={!activo}
                      aria-current={esHoy ? "date" : undefined}
                      aria-label={`${diaCompleto(d)}${esHoy ? ", hoy" : ""}${activo ? "" : ", sin sesiones"}`}
                      onFocus={() => setFoco(d)}
                      onClick={() => activo && onElegir(d)}
                      className={`w-full h-12 md:h-11 flex flex-col items-center justify-center rounded-xl text-sm leading-none focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1
                        ${elegido ? "bg-primary text-white font-bold" : activo ? "bg-primary-soft text-primary font-semibold hover:bg-primary hover:text-white" : "text-muted cursor-default"}
                        ${esHoy && !elegido ? "ring-2 ring-inset ring-primary" : ""}`}
                    >
                      {numero === 1 && <span className="text-[10px] font-semibold uppercase">{formato(d, { month: "short" })}</span>}
                      <span>{numero}</span>
                      {esHoy && <span className="text-[10px] font-semibold mt-0.5">Hoy</span>}
                    </button>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {(!ultimo || ultimo < dias[27]) && (
          <p className="mt-3 text-xs text-muted">
            {ultimo ? `Aún sin sesiones después del ${formato(ultimo, { day: "numeric", month: "long" })}.` : "Aún sin sesiones."}
          </p>
        )}
      </div>
    </>
  );
}
