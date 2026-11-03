"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Una sola petición a /cines por carga de página, compartida por todos los que la usen
let promesa = null;
const leer = () =>
  (promesa ??= fetch(`${API_URL}/cines`)
    .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
    .then((cines) => Object.fromEntries(cines.map((c) => [c.slug, c.tarifas])))
    .catch((err) => {
      console.error("Error loading tarifas:", err);
      promesa = null;  // se reintenta en el próximo montaje
      return {};
    }));

// Tarifas por slug de cine ({} mientras cargan o si falla: ningún cine sale como día del espectador)
export function useTarifas() {
  const [tarifas, setTarifas] = useState({});
  useEffect(() => {
    let vivo = true;
    leer().then((t) => vivo && setTarifas(t));
    return () => { vivo = false; };
  }, []);
  return tarifas;
}
