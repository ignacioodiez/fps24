"use client";

import { useEffect, useId, useRef, useState } from "react";
import { buscarPeliculas } from "@/lib/diario";

const ESPERA = 250; // ms sin teclear antes de buscar

// Busca en el catálogo (GET /peliculas/buscar) para apuntar una película en el diario.
// Combobox de WAI-ARIA: el foco se queda en el campo y aria-activedescendant marca la opción.
export default function BuscadorPeliculas({ onElegir }) {
  const id = useId();
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState([]);
  const [estado, setEstado] = useState("inactivo"); // inactivo | cargando | listo | error
  const [abierto, setAbierto] = useState(false);
  const [activo, setActivo] = useState(-1);
  const temporizador = useRef(null);
  const peticion = useRef(null);

  const cancelar = () => {
    clearTimeout(temporizador.current);
    peticion.current?.abort();
  };
  useEffect(() => cancelar, []);

  // La opción activa a la vista dentro del desplegable
  useEffect(() => {
    if (activo >= 0) document.getElementById(`${id}-op-${activo}`)?.scrollIntoView({ block: "nearest" });
  }, [activo, id]);

  const cambiar = (valor) => {
    setTexto(valor);
    setActivo(-1);
    setAbierto(true);
    cancelar();
    const q = valor.trim();
    if (q.length < 2) {
      setResultados([]);
      setEstado("inactivo");
      return;
    }
    setEstado("cargando");
    temporizador.current = setTimeout(() => {
      const control = (peticion.current = new AbortController());
      buscarPeliculas(q, control.signal)
        .then((lista) => {
          if (control.signal.aborted) return;
          setResultados(lista);
          setEstado("listo");
        })
        .catch(() => control.signal.aborted || setEstado("error"));
    }, ESPERA);
  };

  const elegir = (pelicula) => {
    setAbierto(false);
    onElegir(pelicula);
  };

  const hayLista = abierto && estado === "listo" && resultados.length > 0;

  const tecla = (e) => {
    const n = resultados.length;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      setAbierto(true);
      if (n) setActivo((a) => (e.key === "ArrowDown" ? (a + 1) % n : (a <= 0 ? n : a) - 1));
    } else if (e.key === "Enter" && hayLista && activo >= 0) {
      e.preventDefault();
      elegir(resultados[activo]);
    } else if (e.key === "Escape") {
      // Primero cierra el desplegable; con él cerrado, borra el texto
      e.preventDefault();
      if (abierto && texto.trim().length >= 2) setAbierto(false);
      else cambiar("");
    }
  };

  const q = texto.trim();
  const mensaje = {
    cargando: "Buscando…",
    error: "No hemos podido buscar. Inténtalo de nuevo.",
    listo: resultados.length
      ? `${resultados.length} ${resultados.length === 1 ? "resultado" : "resultados"}`
      : `No encontramos «${q}» en nuestro catálogo. Solo aparecen películas que han pasado por la cartelera de Madrid desde que fps24 las registra.`,
  }[estado] ?? "";

  return (
    <div className="relative">
      <label htmlFor={`${id}-campo`} className="sr-only">Busca una película para añadir a tu diario</label>
      <input
        id={`${id}-campo`} type="search" role="combobox" autoComplete="off" spellCheck={false}
        placeholder="Busca una película para añadir a tu diario…"
        value={texto} onChange={(e) => cambiar(e.target.value)} onKeyDown={tecla}
        onFocus={() => setAbierto(true)} onBlur={() => setAbierto(false)}
        aria-expanded={hayLista} aria-controls={`${id}-lista`} aria-autocomplete="list"
        aria-activedescendant={hayLista && activo >= 0 ? `${id}-op-${activo}` : undefined}
        className="w-full min-h-11 border border-line bg-background px-4 py-2 text-foreground focus:border-primary focus:outline-none"
      />
      {/* Para lectores de pantalla: el número de resultados o el estado */}
      <p role="status" aria-live="polite" className="sr-only">{abierto ? mensaje : ""}</p>

      {abierto && estado !== "inactivo" && (
        // En móvil ocupa todo el ancho de la pantalla (el contenedor tiene px-4)
        <div className="absolute z-20 top-full -left-4 -right-4 sm:left-0 sm:right-0 mt-1 max-h-[60vh] overflow-y-auto border border-line bg-background shadow-lg">
          {hayLista ? (
            <ul role="listbox" id={`${id}-lista`} aria-label="Películas encontradas">
              {resultados.map((p, i) => (
                <li
                  key={p.id} id={`${id}-op-${i}`} role="option" aria-selected={i === activo}
                  onMouseDown={(e) => e.preventDefault()} onClick={() => elegir(p)} onMouseMove={() => setActivo(i)}
                  className={`flex items-center gap-3 px-4 py-2 min-h-11 cursor-pointer ${i === activo ? "bg-primary-soft" : ""}`}
                >
                  <div className="w-8 aspect-[2/3] shrink-0 overflow-hidden border border-line bg-surface">
                    {p.poster_url && <img src={p.poster_url} alt="" className="w-full h-full object-cover" loading="lazy" />}
                  </div>
                  <div className="min-w-0">
                    <p className="font-bold text-foreground break-words">{p.titulo}</p>
                    <p className="text-sm text-muted truncate">{[p.anio, p.director].filter(Boolean).join(" · ")}</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p aria-hidden="true" className={`px-4 py-3 text-sm ${estado === "error" ? "text-red-600" : "text-muted"}`}>{mensaje}</p>
          )}
        </div>
      )}
    </div>
  );
}
