"use client";

import { useState, useEffect } from "react";
import Header from "@/components/Header";
import { backdropDeHoy } from "@/lib/peliculas";

// Header con el backdrop de hoy para páginas que no cargan los pases (p. ej. /cines)
export default function TodayHeader() {
  const [backdrop, setBackdrop] = useState(null);

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/pases`)
      .then((res) => res.json())
      .then((data) => setBackdrop(backdropDeHoy(data)))
      .catch((err) => console.error("Error loading sessions:", err)); // sin backdrop: fondo blanco
  }, []);

  return <Header backdrop={backdrop} />;
}
