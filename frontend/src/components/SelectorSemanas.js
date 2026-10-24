"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { comoUTC, formato } from "@/lib/fechasMadrid";

const SEMANA_MS = 7 * 864e5;

// /estrenos: salto directo a cualquier semana (0..maxima). En 390 px la fila se desliza en horizontal y, como en
// NavSecciones, se lleva la semana elegida a la vista sin mover la página.
export default function SelectorSemanas({ semana, desde, maxima }) {
  const fila = useRef(null);
  useEffect(() => {
    const actual = fila.current?.querySelector("[aria-current]");
    if (actual) fila.current.scrollLeft = actual.offsetLeft - 16; // offsetLeft relativo a la fila (relative)
  }, [semana]);

  const lunes0 = comoUTC(desde).getTime() - semana * SEMANA_MS;
  return (
    <nav ref={fila} aria-label="Elegir semana" className="relative -mx-4 px-4 mb-6 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
      <ul className="flex gap-2 w-max">
        {Array.from({ length: maxima + 1 }, (_, n) => {
          const lunes = new Date(lunes0 + n * SEMANA_MS).toISOString().slice(0, 10);
          const actual = n === semana;
          return (
            <li key={n}>
              <Link href={`?semana=${n}`} aria-current={actual ? "page" : undefined}
                    aria-label={`Semana del ${formato(lunes, { day: "numeric", month: "long" })}`}
                    className={`flex items-center min-h-11 rounded-full border px-4 text-xs font-semibold whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${actual ? "border-primary bg-primary text-white" : "border-line text-foreground hover:border-primary hover:text-primary"}`}>
                {n === 0 ? "Esta semana" : `${comoUTC(lunes).getUTCDate()} ${formato(lunes, { month: "short" })}`}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
