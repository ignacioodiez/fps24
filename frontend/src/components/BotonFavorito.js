"use client";

import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import { useFavoritos } from "@/components/FavoritosProvider";

// Estrella de cine favorito. Sin sesión, pulsarla abre el inicio de sesión. pequeno: la de las sesiones del modal.
export default function BotonFavorito({ slug, nombre, pequeno = false, className = "" }) {
  const { cargando } = useAuth();
  const { favoritos, alternar } = useFavoritos();
  if (!AUTH_DISPONIBLE || !slug) return null;
  const activo = favoritos.has(slug);
  return (
    <button
      type="button" aria-pressed={activo} disabled={cargando}
      aria-label={activo ? `Quitar ${nombre} de mis cines` : `Añadir ${nombre} a mis cines`}
      title={activo ? "Quitar de mis cines" : "Añadir a mis cines"}
      onClick={(e) => {
        e.stopPropagation(); // dentro de tarjetas que abren la película al hacer clic
        alternar(slug, nombre);
      }}
      className={`shrink-0 inline-flex items-center justify-center leading-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-60 ${
        pequeno ? "w-7 h-7 -my-1 text-base rounded-md" : "w-10 h-10 text-2xl rounded-full border border-line bg-background hover:border-primary"} ${
        activo ? "text-primary" : "text-muted hover:text-primary"} ${className}`}
    >
      <span aria-hidden="true">{activo ? "★" : "☆"}</span>
    </button>
  );
}

// Marca discreta (no interactiva) junto al nombre de un cine favorito
export function MarcaFavorito({ slug }) {
  const { favoritos } = useFavoritos();
  if (!favoritos.has(slug)) return null;
  return (
    <span className="text-primary" title="En tus cines favoritos">
      <span aria-hidden="true">★</span><span className="sr-only">Cine favorito: </span>
    </span>
  );
}
