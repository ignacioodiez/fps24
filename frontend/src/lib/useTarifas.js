"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Una sola petición a /cines por carga de página, compartida por todos los que la usen
let promesa = null;
const leer = () =>
  (promesa ??= fetch(`${API_URL}/cines`)
    .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
    .then((cines) => Object.fromEntries(cines.map((c) => [c.slug, c])))
    .catch((err) => {
      console.error("Error loading tarifas:", err);
      promesa = null;  // se reintenta en el próximo montaje
      return {};
    }));

// Ficha de cada cine por slug ({} mientras carga o si falla)
export function useCines() {
  const [cines, setCines] = useState({});
  useEffect(() => {
    let vivo = true;
    leer().then((c) => vivo && setCines(c));
    return () => { vivo = false; };
  }, []);
  return cines;
}

// Tarifas por slug de cine ({} mientras cargan o si falla: ningún cine sale como día del espectador)
export function useTarifas() {
  const cines = useCines();
  return useMemo(() => Object.fromEntries(Object.entries(cines).map(([slug, c]) => [slug, c.tarifas])), [cines]);
}

// Centros culturales (tipo "cultural"): su link_compra es la ficha de la actividad, no una compra. Para rotular el botón
// "Más información" en vez de "Comprar entradas". Mientras carga /cines, false (se rotula como siempre).
export function useSinVenta(slug) {
  return useCines()[slug]?.tipo === "cultural";
}
