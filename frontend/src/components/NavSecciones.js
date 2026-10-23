"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

// Secciones de la barra: añadir una es añadir una línea. "tambien" = otras rutas en las que la pestaña cuenta como activa.
const SECCIONES = [
  { href: "/", etiqueta: "Inicio", tambien: ["/pelicula"] },
  { href: "/cines", etiqueta: "Cines" },
  { href: "/estrenos", etiqueta: "Estrenos" },
  { href: "/especiales", etiqueta: "Especiales" },
];

// "/" solo coincide exacta; el resto, la ruta y sus subrutas
const dentro = (ruta, base) => (base === "/" ? ruta === "/" : ruta === base || ruta.startsWith(base + "/"));

// Enlace de texto plano; la activa lleva una línea violeta de 3px abajo (sombra interior: no la recorta el overflow)
const ENLACE = "flex items-center min-h-11 whitespace-nowrap px-3 md:px-4 text-xs md:text-[13px] font-semibold uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary";

export default function NavSecciones() {
  const ruta = usePathname();
  const fila = useRef(null);

  // En móvil la fila se desliza: lleva la pestaña activa a la vista sin mover la página
  useEffect(() => {
    const activa = fila.current?.querySelector("[aria-current]");
    if (activa) fila.current.scrollLeft = activa.offsetLeft - 16; // offsetLeft relativo a la fila (relative)
  }, [ruta]);

  return (
    <nav aria-label="Secciones" className="w-full bg-surface border-y border-line">
      {/* px resta el padding del primer enlace para que el texto se alinee con el contenido */}
      <div ref={fila} className="relative max-w-9xl mx-auto overflow-x-auto px-1 md:px-4 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <ul className="flex w-max">
          {SECCIONES.map(({ href, etiqueta, tambien = [] }) => {
            const activa = [href, ...tambien].some((base) => dentro(ruta, base));
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={activa ? "page" : undefined}
                  className={`${ENLACE} ${activa
                    ? "text-primary shadow-[inset_0_-3px_0_var(--primary)]"
                    : "text-muted hover:text-foreground"}`}
                >
                  {etiqueta}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </nav>
  );
}
