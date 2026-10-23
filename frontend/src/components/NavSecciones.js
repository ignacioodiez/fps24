"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

// Secciones de la barra: añadir una es añadir una línea. "tambien" = otras rutas en las que la pestaña cuenta como activa.
const SECCIONES = [
  { href: "/", etiqueta: "Inicio", tambien: ["/pelicula"] },
  { href: "/cines", etiqueta: "Cines" },
];

// "/" solo coincide exacta; el resto, la ruta y sus subrutas
const dentro = (ruta, base) => (base === "/" ? ruta === "/" : ruta === base || ruta.startsWith(base + "/"));

const PILDORA = "block whitespace-nowrap px-5 py-2 rounded-full border text-sm font-bold uppercase tracking-wide transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";

export default function NavSecciones() {
  const ruta = usePathname();
  const fila = useRef(null);

  // En móvil la fila se desliza: lleva la pestaña activa a la vista sin mover la página
  useEffect(() => {
    const activa = fila.current?.querySelector("[aria-current]");
    if (activa) fila.current.scrollLeft = activa.offsetLeft - 16; // offsetLeft relativo a la fila (relative)
  }, [ruta]);

  return (
    <nav aria-label="Secciones" className="max-w-9xl mx-auto w-full mt-4">
      <div ref={fila} className="relative overflow-x-auto px-4 md:px-8 py-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <ul className="flex gap-2 w-max mx-auto xl:mx-0">
          {SECCIONES.map(({ href, etiqueta, tambien = [] }) => {
            const activa = [href, ...tambien].some((base) => dentro(ruta, base));
            return (
              <li key={href}>
                <Link
                  href={href}
                  aria-current={activa ? "page" : undefined}
                  className={`${PILDORA} ${activa
                    ? "border-primary bg-primary text-white"
                    : "border-line bg-background text-foreground hover:border-primary hover:text-primary"}`}
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
