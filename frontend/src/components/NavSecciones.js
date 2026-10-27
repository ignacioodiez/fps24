"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import Avatar from "@/components/Avatar";
import BotonAnadirDiario from "@/components/BotonAnadirDiario";

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
const ACTIVA = "text-primary shadow-[inset_0_-3px_0_var(--primary)]";
const INACTIVA = "text-muted hover:text-foreground";

// Cuenta, a la derecha. En móvil (<640px) baja a su propia línea para que el scroll de las secciones nunca la tape.
// Mientras AuthProvider carga (servidor e hidratación) se reserva el hueco vacío: ni salto ni desajuste.
function ZonaCuenta({ ruta }) {
  // cerrarSesion lleva a la portada y cierra la sesión allí; el aviso "Has cerrado sesión" lo da AuthProvider
  const { usuario, cargando, cerrarSesion, abrirLogin, miPerfil, esAdmin } = useAuth();
  if (!AUTH_DISPONIBLE) return null;

  // Con usuario conocido, directo a /u/<usuario> (sin pasar por la redirección de /perfil)
  const miRuta = miPerfil?.usuario ? `/u/${miPerfil.usuario}` : "/perfil";
  const perfilActivo = dentro(ruta, "/perfil") || dentro(ruta.toLowerCase(), miRuta);
  return (
    <div className="flex items-stretch justify-end w-full sm:w-auto ml-auto border-t border-line sm:border-t-0 min-h-11">
      {cargando ? null : usuario ? (
        <>
          <BotonAnadirDiario />
          <span aria-hidden="true" className="w-px h-4 self-center bg-line" />
          <Link href={miRuta} aria-current={perfilActivo ? "page" : undefined} className={`${ENLACE} gap-2 ${perfilActivo ? ACTIVA : INACTIVA}`}>
            {/* Decorativo: el texto "Mi perfil" ya lo nombra */}
            {miPerfil?.usuario && <Avatar usuario={miPerfil.usuario} avatar={miPerfil.avatar} etiqueta={null} className="w-6 h-6 text-[10px] normal-case tracking-normal" />}
            Mi perfil
          </Link>
          <span aria-hidden="true" className="w-px h-4 self-center bg-line" />
          {esAdmin && (
            <>
              <Link href="/admin" aria-current={dentro(ruta, "/admin") ? "page" : undefined} className={`${ENLACE} ${dentro(ruta, "/admin") ? ACTIVA : INACTIVA}`}>
                Admin
              </Link>
              <span aria-hidden="true" className="w-px h-4 self-center bg-line" />
            </>
          )}
          <button type="button" onClick={cerrarSesion} className={`${ENLACE} ${INACTIVA}`}>Cerrar sesión</button>
        </>
      ) : (
        <button type="button" onClick={() => abrirLogin()} aria-haspopup="dialog" className={`${ENLACE} text-primary hover:opacity-75`}>
          Iniciar sesión
        </button>
      )}
    </div>
  );
}

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
      <div className="max-w-9xl mx-auto flex flex-wrap px-1 md:px-4">
        <div ref={fila} className="relative min-w-0 w-full sm:w-auto sm:flex-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <ul className="flex w-max">
            {SECCIONES.map(({ href, etiqueta, tambien = [] }) => {
              const activa = [href, ...tambien].some((base) => dentro(ruta, base));
              return (
                <li key={href}>
                  <Link href={href} aria-current={activa ? "page" : undefined} className={`${ENLACE} ${activa ? ACTIVA : INACTIVA}`}>
                    {etiqueta}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
        <ZonaCuenta ruta={ruta} />
      </div>
    </nav>
  );
}
