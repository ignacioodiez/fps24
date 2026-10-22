"use client";

import { use } from "react";
import ModalPelicula from "@/components/ModalPelicula";

// Ruta interceptada: al navegar desde la portada a /pelicula/{id} se abre la vista rápida encima.
// Con la URL directa (o al recargar) se ve la página completa de app/pelicula/[id].
export default function PeliculaInterceptada({ params }) {
  const { id } = use(params);
  return <ModalPelicula id={id} />;
}
