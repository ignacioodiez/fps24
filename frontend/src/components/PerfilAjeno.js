"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import Avatar, { AtribucionPoster } from "@/components/Avatar";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import { ListaDiario } from "@/components/Perfil";
import { CabeceraPerfil, PestanaPerfil, PestanasPerfil, TarjetasCines } from "@/components/PerfilVistas";
import { bloquear, leerPerfilComoYo, pedirAmistad, quitarAmigo } from "@/lib/amigos";

// /u/<usuario> de otra persona. El servidor la pinta sin saber quién mira (solo lo público, nunca lo "solo amigos");
// con sesión, el navegador la vuelve a pedir con el token y cambia a lo que este visitante puede ver.

// Pestañas con contenido para un visitante (Perfil siempre)
const visibles = (perfil) => [
  "perfil",
  ...(perfil.diario?.total > 0 ? ["diario"] : []),
  ...(perfil.cines?.length > 0 ? ["cines"] : []),
];

export function NoDisponible() {
  return (
    <div className="max-w-3xl mx-auto px-4 md:px-6 py-12 text-center">
      <p className="text-xl text-foreground">Este perfil no existe o es privado.</p>
    </div>
  );
}

function Diario({ usuario, diario }) {
  if (!diario) return <p className="mt-10 text-center text-muted">Este diario no se muestra.</p>;
  if (!diario.total) return <p className="mt-10 text-center text-muted">Todavía no hay películas en este diario.</p>;
  const paginas = Math.ceil(diario.total / diario.por_pagina);
  const enlace = (n) => `/u/${usuario}/diario${n > 1 ? `?pagina=${n}` : ""}`;
  return (
    <>
      {diario.entradas.length ? <ListaDiario entradas={diario.entradas} /> : <p className="mt-6 text-muted">No hay más entradas.</p>}
      <AtribucionPoster className="mt-4" />
      {paginas > 1 && (
        <nav aria-label="Páginas del diario" className="mt-6 flex flex-wrap items-center justify-center gap-3 text-sm">
          {diario.pagina > 1 && <Link href={enlace(diario.pagina - 1)} className={BOTON_SECUNDARIO}>Más recientes</Link>}
          <span className="text-muted">Página {Math.min(diario.pagina, paginas)} de {paginas}</span>
          {diario.pagina < paginas && <Link href={enlace(diario.pagina + 1)} className={BOTON_SECUNDARIO}>Anteriores</Link>}
        </nav>
      )}
    </>
  );
}

// Añadir amigo / Solicitud enviada / Aceptar solicitud / Amigos ✓ (con quitar y bloquear). Sin sesión, abre el login.
function BotonAmistad({ perfil, onCambio }) {
  const { usuario: sesion, cargando, abrirLogin, miPerfil } = useAuth();
  const [abierto, setAbierto] = useState(false);
  const [confirmar, setConfirmar] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");
  const id = useId();
  const nombre = perfil.usuario;
  const gestionar = miPerfil?.usuario && (
    <Link href={`/u/${miPerfil.usuario}/amigos`} className="text-sm font-bold text-primary hover:underline">Gestionar en Amigos</Link>
  );

  const accion = async (fn, hecho) => {
    setOcupado(true);
    setAviso("");
    try {
      await fn();
      setAbierto(false);
      setConfirmar(false);
      await onCambio();
      setAviso(hecho);
    } catch (err) {
      setAviso(err.message);
    } finally {
      setOcupado(false);
    }
  };

  // Mientras se sabe si hay sesión, y con sesión hasta tener la relación, nada (igual en servidor y navegador)
  if (cargando || (sesion && !perfil.relacion) || perfil.relacion === "yo" || (!sesion && !AUTH_DISPONIBLE)) return null;

  let contenido;
  if (!sesion) {
    contenido = (
      <button type="button" onClick={() => abrirLogin("Inicia sesión para añadir amigos")} aria-haspopup="dialog" className={BOTON_PRIMARIO}>
        Añadir amigo
      </button>
    );
  } else if (perfil.relacion === "ninguna") {
    contenido = (
      <button type="button" disabled={ocupado} onClick={() => accion(() => pedirAmistad(nombre), "Solicitud enviada")} className={BOTON_PRIMARIO}>
        Añadir amigo
      </button>
    );
  } else if (perfil.relacion === "recibida") {
    contenido = (
      <button type="button" disabled={ocupado} onClick={() => accion(() => pedirAmistad(nombre), `Ahora @${nombre} y tú sois amigos`)} className={BOTON_PRIMARIO}>
        Aceptar solicitud
      </button>
    );
  } else if (perfil.relacion === "enviada") {
    contenido = <><span className="text-sm font-bold text-muted">Solicitud enviada</span>{gestionar}</>;
  } else if (perfil.relacion === "bloqueado") {
    contenido = <><span className="text-sm text-muted">Has bloqueado a @{nombre}.</span>{gestionar}</>;
  } else if (perfil.relacion === "amigos") {
    contenido = (
      <div onKeyDown={(e) => e.key === "Escape" && (setAbierto(false), setConfirmar(false))}>
        <button type="button" aria-expanded={abierto} aria-controls={`${id}-opciones`} onClick={() => { setAbierto((v) => !v); setConfirmar(false); }}
                className={`${BOTON_SECUNDARIO} border-primary text-primary`}>
          Amigos ✓<span className="sr-only">: opciones</span>
        </button>
        {abierto && (
          <div id={`${id}-opciones`} className="mt-2 flex flex-wrap items-center gap-3 text-sm font-bold">
            {confirmar ? (
              <>
                <span className="font-normal text-foreground">¿Bloquear a @{nombre}? Dejaréis de ser amigos y no podrá ver tu perfil.</span>
                <button type="button" disabled={ocupado} onClick={() => accion(() => bloquear(nombre), `Has bloqueado a @${nombre}`)} className="text-red-600 hover:underline disabled:opacity-60">
                  Sí, bloquear
                </button>
                <button type="button" onClick={() => setConfirmar(false)} className="text-muted hover:text-foreground">No</button>
              </>
            ) : (
              <>
                <button type="button" disabled={ocupado} onClick={() => accion(() => quitarAmigo(nombre), `Ya no sois amigos`)} className="text-muted hover:text-red-600 disabled:opacity-60">
                  Quitar amigo
                </button>
                <button type="button" onClick={() => setConfirmar(true)} className="text-muted hover:text-red-600">Bloquear</button>
              </>
            )}
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="mt-3">
      <div className="flex flex-wrap items-center gap-3">{contenido}</div>
      <p role="status" aria-live="polite" className="mt-1 text-sm font-semibold text-primary min-h-5">{aviso}</p>
    </div>
  );
}

// inicial: lo que el servidor leyó sin sesión. Con sesión, lo de GET /u con el token (null: para mí no existe).
export default function PerfilAjeno({ inicial, pestana, pagina = 1 }) {
  const { usuario: sesion } = useAuth();
  const uid = sesion?.id;
  const clave = `${uid}|${inicial.usuario}|${pagina}`; // lo leído con otra sesión u otra página deja de valer
  const [comoYo, setComoYo] = useState({ clave: null, datos: undefined });

  const recargar = useCallback(
    () => (uid ? leerPerfilComoYo(inicial.usuario, pagina).then((datos) => setComoYo({ clave, datos })).catch(() => {}) : Promise.resolve()),
    [uid, inicial.usuario, pagina, clave],
  );
  useEffect(() => {
    recargar();
  }, [recargar]);

  const perfil = uid && comoYo.clave === clave ? comoYo.datos : inicial;
  if (perfil === null) return <NoDisponible />;

  if (perfil.restringido) {
    return (
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-12 flex flex-col items-center text-center">
        <Avatar usuario={perfil.usuario} avatar={perfil.avatar} className="w-20 h-20 md:w-24 md:h-24 text-3xl" />
        {perfil.avatar?.tipo === "pelicula" && <AtribucionPoster className="mt-1" />}
        <h2 className="mt-3 text-2xl md:text-4xl font-black font-display text-primary break-all">@{perfil.usuario}</h2>
        <p className="mt-2 text-muted">Solo sus amigos pueden ver su perfil.</p>
        <BotonAmistad perfil={perfil} onCambio={recargar} />
      </div>
    );
  }

  const cifras = {
    entradas: perfil.cifras?.entradas,
    este_anio: perfil.cifras?.este_anio,
    cines: perfil.cines ? perfil.cines.length : undefined,
  };
  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 py-8">
      <CabeceraPerfil perfil={perfil} cifras={cifras}>
        <BotonAmistad perfil={perfil} onCambio={recargar} />
      </CabeceraPerfil>
      <PestanasPerfil usuario={perfil.usuario} actual={pestana} visibles={visibles(perfil)} />
      {pestana === "perfil" && (
        <PestanaPerfil usuario={perfil.usuario} entradas={perfil.diario?.entradas} total={perfil.diario?.total} cines={perfil.cines} />
      )}
      {pestana === "diario" && <Diario usuario={perfil.usuario} diario={perfil.diario} />}
      {pestana === "cines" && (perfil.cines?.length
        ? <TarjetasCines cines={perfil.cines} />
        : <p className="mt-10 text-center text-muted">Sus cines favoritos no se muestran.</p>)}
    </div>
  );
}
