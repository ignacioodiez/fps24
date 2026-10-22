"use client";

import { useEffect, useState } from "react";
import TarjetaEstreno from "@/components/TarjetaEstreno";
import MosaicoEspeciales from "@/components/MosaicoEspeciales";

// "19–25 oct" o, si cambia de mes, "26 oct – 1 nov". Las fechas vienen como "YYYY-MM-DD" (Madrid).
const rangoSemana = ({ inicio, fin }) => {
  const [a, b] = [inicio, fin].map((f) => new Date(`${f}T00:00`));
  const mes = (d) => d.toLocaleDateString("es-ES", { month: "short" }).replace(".", "");
  return a.getMonth() === b.getMonth()
    ? `${a.getDate()}–${b.getDate()} ${mes(b)}`
    : `${a.getDate()} ${mes(a)} – ${b.getDate()} ${mes(b)}`;
};

// Celdas de la cuadrícula 2x2 de estrenos según cuántos hay (el backend devuelve hasta 4)
const CELDAS_ESTRENO = {
  1: ["col-span-2 md:row-span-2"],
  2: ["md:col-span-2", "md:col-span-2"],
  3: ["", "", "md:col-span-2"],
};

const PESTANAS = [
  { id: "estrenos", texto: "Estrenos" },
  { id: "especiales", texto: "Especiales" },
];

// Bloque de escritorio de alto fijo (los dos miden lo mismo). En móvil solo se ve el de la pestaña activa.
function Bloque({ id, titulo, visibleEnMovil, children }) {
  return (
    <section id={`panel-${id}`} role="tabpanel" aria-labelledby={`titulo-${id}`}
             className={`${visibleEnMovil ? "block" : "hidden"} md:block min-w-0`}>
      <h3 id={`titulo-${id}`} className="hidden md:block mb-2 text-xs font-bold uppercase tracking-wider text-muted">{titulo}</h3>
      <div className="md:h-[400px]">{children}</div>
    </section>
  );
}

function Esqueleto() {
  return (
    <div className="max-w-9xl mx-auto mt-8" aria-busy="true" aria-label="Cargando destacadas">
      <div className="h-5 w-56 rounded bg-surface animate-pulse mb-4" />
      <div className="grid md:grid-cols-2 gap-6">
        <div className="h-80 md:h-[400px] rounded-2xl bg-surface animate-pulse" />
        <div className="hidden md:block h-[400px] rounded-2xl bg-surface animate-pulse" />
      </div>
    </div>
  );
}

// Destacados de la semana (GET /destacadas): estrenos y pases especiales. Escritorio: dos bloques del mismo
// alto, lado a lado. Móvil: pestañas. Una lista vacía no se pinta (la otra ocupa todo); si falla la API, nada.
export default function SeccionDestacadas({ oculta = false }) {
  const [datos, setDatos] = useState(null);
  const [fallo, setFallo] = useState(false);
  const [pestana, setPestana] = useState("estrenos");

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/destacadas`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(setDatos)
      .catch((err) => {
        console.error("Error loading destacadas:", err);
        setFallo(true);
      });
  }, []);

  if (oculta || fallo) return null;
  if (!datos) return <Esqueleto />;

  const estrenos = (datos.estrenos || []).slice(0, 4);
  const especiales = datos.especiales || [];  // por nota, como vienen: el mosaico depende de ese orden
  if (estrenos.length === 0 && especiales.length === 0) return null;
  const ambas = estrenos.length > 0 && especiales.length > 0;
  // Con una sola lista no hay pestañas: se muestra la que hay
  const activa = ambas ? pestana : estrenos.length > 0 ? "estrenos" : "especiales";
  const celdas = CELDAS_ESTRENO[estrenos.length] || [];

  return (
    <section aria-labelledby="destacadas-titulo" className="max-w-9xl mx-auto mt-8">
      {/* Cabecera común (aquí irá la navegación de semana) */}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 mb-3">
        <h2 id="destacadas-titulo" className="text-lg md:text-xl font-display font-bold text-foreground">Destacados de la semana</h2>
        {datos.semana && (
          <span className="text-xs font-medium text-muted uppercase tracking-wider">{rangoSemana(datos.semana)}</span>
        )}
      </div>

      {ambas && (
        <div role="tablist" aria-label="Destacados" className="md:hidden flex p-1 mb-3 rounded-full bg-surface border border-line">
          {PESTANAS.map((p) => (
            <button key={p.id} type="button" role="tab" id={`pestana-${p.id}`} aria-controls={`panel-${p.id}`}
                    aria-selected={activa === p.id} onClick={() => setPestana(p.id)}
                    className={`flex-1 py-2 rounded-full text-sm font-bold transition-colors ${
                      activa === p.id ? "bg-background text-foreground shadow-sm" : "text-muted"}`}>
              {p.texto}
            </button>
          ))}
        </div>
      )}

      <div className={`grid gap-6 ${ambas ? "md:grid-cols-2" : ""}`}>
        {estrenos.length > 0 && (
          <Bloque id="estrenos" titulo="Estrenos" visibleEnMovil={activa === "estrenos"}>
            <ul className="grid grid-cols-2 md:grid-rows-2 md:h-full gap-3">
              {estrenos.map((estreno, i) => (
                <TarjetaEstreno key={estreno.pelicula.id} estreno={estreno} className={celdas[i] || ""} />
              ))}
            </ul>
          </Bloque>
        )}
        {especiales.length > 0 && (
          <Bloque id="especiales" titulo="Pases especiales" visibleEnMovil={activa === "especiales"}>
            <MosaicoEspeciales especiales={especiales} />
          </Bloque>
        )}
      </div>
    </section>
  );
}
