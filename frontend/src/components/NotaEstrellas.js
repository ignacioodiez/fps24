"use client";

import { useRef } from "react";

// Nota del diario: valor 1-10 = ½ a 5 estrellas; null = sin nota
export const textoNota = (valor) => {
  const n = valor / 2;
  return `${n.toLocaleString("es-ES")} ${n === 1 ? "estrella" : "estrellas"}`;
};

// Estrella rellena al 0, 50 o 100 %
function Estrella({ relleno, grande }) {
  return (
    <span className={`relative inline-block leading-none ${grande ? "text-3xl" : "text-base"}`} aria-hidden="true">
      <span className="text-line">★</span>
      <span className="absolute inset-0 overflow-hidden text-primary" style={{ width: `${relleno}%` }}>★</span>
    </span>
  );
}

const relleno = (valor, i) => Math.max(0, Math.min(100, ((valor ?? 0) - i * 2) * 50));

// Editable: radiogroup con foco itinerante. Cada estrella son dos radios (media y entera); flechas suben o bajan
// medio punto, Inicio = sin nota, Fin = 5 estrellas. soloLectura: solo las estrellas, con su texto para lectores.
export default function NotaEstrellas({ valor = null, onCambiar, soloLectura = false, idEtiqueta }) {
  const radios = useRef([]);

  if (soloLectura) {
    if (!valor) return null;
    return (
      <span role="img" aria-label={textoNota(valor)} className="inline-flex">
        {[0, 1, 2, 3, 4].map((i) => <Estrella key={i} relleno={relleno(valor, i)} />)}
      </span>
    );
  }

  const elegir = (v) => {
    onCambiar(v);
    radios.current[v]?.focus();
  };
  const tecla = (e) => {
    const actual = valor ?? 0;
    const destino = {
      ArrowRight: actual + 1, ArrowUp: actual + 1, ArrowLeft: actual - 1, ArrowDown: actual - 1, Home: 0, End: 10,
    }[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    elegir(Math.max(0, Math.min(10, destino)) || null);
  };
  const radio = (v, etiqueta, clase) => (
    <button
      key={v} ref={(el) => (radios.current[v ?? 0] = el)} type="button" role="radio"
      aria-checked={valor === v} aria-label={etiqueta} tabIndex={valor === v ? 0 : -1} onClick={() => elegir(v)}
      className={`${clase} focus-visible:outline-2 focus-visible:outline-primary`}
    />
  );

  return (
    <div role="radiogroup" aria-labelledby={idEtiqueta} onKeyDown={tecla} className="flex flex-wrap items-center gap-3">
      <div className="flex">
        {[0, 1, 2, 3, 4].map((i) => (
          <span key={i} className="relative">
            <Estrella relleno={relleno(valor, i)} grande />
            {radio(i * 2 + 1, textoNota(i * 2 + 1), "absolute inset-y-0 left-0 w-1/2")}
            {radio(i * 2 + 2, textoNota(i * 2 + 2), "absolute inset-y-0 right-0 w-1/2")}
          </span>
        ))}
      </div>
      <button
        ref={(el) => (radios.current[0] = el)} type="button" role="radio" aria-checked={valor === null}
        tabIndex={valor === null ? 0 : -1} onClick={() => elegir(null)}
        className={`px-3 py-1 border text-xs font-semibold uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
          valor === null ? "border-primary text-primary bg-primary-soft" : "border-line text-muted hover:text-foreground"}`}
      >
        Sin nota
      </button>
      <span className="text-sm text-muted" aria-hidden="true">{valor ? textoNota(valor) : ""}</span>
    </div>
  );
}
