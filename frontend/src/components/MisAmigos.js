"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useState } from "react";
import Avatar from "@/components/Avatar";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO, CAMPO, ETIQUETA } from "@/components/DialogoDiario";
import {
  aceptarSolicitud, bloquear, cancelarSolicitud, desbloquear, listarAmigos, listarBloqueos, pedirAmistad, quitarAmigo, rechazarSolicitud,
} from "@/lib/amigos";

const SUBTITULO = "text-sm font-bold uppercase tracking-wider text-foreground";
const ACCION = "px-2 py-1.5 text-xs font-bold disabled:opacity-60";

// Una persona: avatar y nombre (enlazado a su perfil) y, a la derecha, sus acciones
function Fila({ persona, children }) {
  return (
    <li className="flex flex-wrap items-center gap-x-3 gap-y-1 py-3 border-b border-line">
      <Link href={`/u/${persona.usuario}`} className="flex min-w-0 flex-1 items-center gap-3 font-bold text-foreground hover:text-primary">
        <Avatar usuario={persona.usuario} avatar={persona.avatar} className="w-10 h-10 text-base" etiqueta={null} />
        <span className="min-w-0 break-all">@{persona.usuario}</span>
      </Link>
      <div className="flex flex-wrap items-center gap-1">{children}</div>
    </li>
  );
}

function Seccion({ id, titulo, vacio, children }) {
  return (
    <section aria-labelledby={id} className="mt-8 min-w-0">
      <h4 id={id} className={SUBTITULO}>{titulo}</h4>
      {children.length ? <ul className="mt-2">{children}</ul> : <p className="mt-2 text-sm text-muted">{vacio}</p>}
    </section>
  );
}

// Pestaña Amigos de mi perfil: añadir por nombre de usuario (sin distinguir mayúsculas), solicitudes, amigos y bloqueados.
// onRecibidas(n): para el contador de la pestaña.
export default function MisAmigos({ onRecibidas }) {
  const [datos, setDatos] = useState(null); // { amigos, recibidas, enviadas, bloqueos } o { error }
  const [nombre, setNombre] = useState("");
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [bloqueando, setBloqueando] = useState(null); // usuario pendiente de confirmar
  const id = useId();

  const cargar = useCallback(
    () => Promise.all([listarAmigos(), listarBloqueos()])
      .then(([amigos, bloqueos]) => {
        setDatos({ ...amigos, bloqueos });
        onRecibidas?.(amigos.recibidas.length);
      })
      .catch((err) => setDatos((d) => d ?? { error: err.message })),
    [onRecibidas],
  );
  useEffect(() => {
    cargar();
  }, [cargar]);

  const hacer = async (fn, hecho) => {
    setOcupado(true);
    setAviso("");
    try {
      const r = await fn();
      setBloqueando(null);
      await cargar();
      setAviso(hecho ?? r?.mensaje ?? "");
      return true;
    } catch (err) {
      setAviso(err.message);
      return false;
    } finally {
      setOcupado(false);
    }
  };

  const enviar = async (e) => {
    e.preventDefault();
    if (await hacer(() => pedirAmistad(nombre))) setNombre("");
  };

  if (!datos) return <div aria-busy="true" aria-label="Cargando tus amigos" className="mt-6 h-24 bg-surface animate-pulse" />;
  if (datos.error) return <p role="alert" className="py-8 text-red-600">{datos.error}</p>;

  return (
    <div>
      <form onSubmit={enviar} className="mt-4 border border-line bg-surface p-4">
        <label htmlFor={`${id}-usuario`} className={ETIQUETA}>Nombre de usuario</label>
        <div className="flex flex-wrap gap-2">
          <input
            id={`${id}-usuario`} type="text" required maxLength={21} value={nombre} onChange={(e) => setNombre(e.target.value)}
            placeholder="Nombre de usuario" autoComplete="off" autoCapitalize="none" spellCheck={false}
            aria-describedby={`${id}-ayuda`} className={`${CAMPO} min-w-0 flex-1 basis-48`}
          />
          <button type="submit" disabled={ocupado || !nombre.trim()} className={BOTON_PRIMARIO}>Enviar solicitud</button>
        </div>
        <p id={`${id}-ayuda`} className="mt-1 text-xs text-muted">
          Da igual mayúsculas o minúsculas. Si te ha enviado una solicitud, se acepta al momento.
        </p>
      </form>
      <p role="status" aria-live="polite" className="mt-2 text-sm font-semibold text-primary min-h-5">{aviso}</p>

      {/* Recibidas y enviadas, lado a lado desde md; en móvil, una encima de otra */}
      <div className="grid gap-x-8 md:grid-cols-2">
        <Seccion id={`${id}-recibidas`} titulo={`Solicitudes recibidas (${datos.recibidas.length})`} vacio="No tienes solicitudes pendientes.">
          {datos.recibidas.map((s) => (
            <Fila key={s.id} persona={s}>
              <button type="button" disabled={ocupado} onClick={() => hacer(() => aceptarSolicitud(s.id), `Ahora @${s.usuario} y tú sois amigos`)} className={BOTON_PRIMARIO}>
                Aceptar<span className="sr-only"> a @{s.usuario}</span>
              </button>
              <button type="button" disabled={ocupado} onClick={() => hacer(() => rechazarSolicitud(s.id), `Solicitud de @${s.usuario} rechazada`)} className={`${ACCION} text-muted hover:text-red-600`}>
                Rechazar<span className="sr-only"> a @{s.usuario}</span>
              </button>
            </Fila>
          ))}
        </Seccion>

        <Seccion id={`${id}-enviadas`} titulo={`Solicitudes enviadas (${datos.enviadas.length})`} vacio="No tienes solicitudes enviadas sin respuesta.">
          {datos.enviadas.map((s) => (
            <Fila key={s.id} persona={s}>
              <span className="text-xs text-muted">Pendiente</span>
              <button type="button" disabled={ocupado} onClick={() => hacer(() => cancelarSolicitud(s.id), `Solicitud a @${s.usuario} cancelada`)} className={`${ACCION} text-muted hover:text-red-600`}>
                Cancelar<span className="sr-only"> la solicitud a @{s.usuario}</span>
              </button>
            </Fila>
          ))}
        </Seccion>
      </div>

      <Seccion id={`${id}-amigos`} titulo={`Amigos (${datos.amigos.length})`} vacio="Aún no tienes amigos en fps24. Añade a alguien por su nombre de usuario.">
        {datos.amigos.map((a) => (
          <Fila key={a.usuario} persona={a}>
            {bloqueando === a.usuario ? (
              <>
                <span className="text-xs text-foreground">¿Bloquear a @{a.usuario}?</span>
                <button type="button" disabled={ocupado} onClick={() => hacer(() => bloquear(a.usuario), `Has bloqueado a @${a.usuario}`)} className={`${ACCION} text-red-600 hover:underline`}>
                  Sí, bloquear
                </button>
                <button type="button" onClick={() => setBloqueando(null)} className={`${ACCION} text-muted hover:text-foreground`}>No</button>
              </>
            ) : (
              <>
                <button type="button" disabled={ocupado} onClick={() => hacer(() => quitarAmigo(a.usuario), `@${a.usuario} ya no está en tus amigos`)} className={`${ACCION} text-muted hover:text-red-600`}>
                  Quitar<span className="sr-only"> a @{a.usuario} de tus amigos</span>
                </button>
                <button type="button" onClick={() => setBloqueando(a.usuario)} className={`${ACCION} text-muted hover:text-red-600`}>
                  Bloquear<span className="sr-only"> a @{a.usuario}</span>
                </button>
              </>
            )}
          </Fila>
        ))}
      </Seccion>

      <Seccion id={`${id}-bloqueos`} titulo={`Bloqueados (${datos.bloqueos.length})`} vacio="No has bloqueado a nadie.">
        {datos.bloqueos.map((b) => (
          <Fila key={b.usuario} persona={b}>
            <button type="button" disabled={ocupado} onClick={() => hacer(() => desbloquear(b.usuario), `Has desbloqueado a @${b.usuario}`)} className={`${BOTON_SECUNDARIO}`}>
              Desbloquear<span className="sr-only"> a @{b.usuario}</span>
            </button>
          </Fila>
        ))}
      </Seccion>
      <p className="mt-6 text-xs text-muted">
        Quien bloqueas no puede ver tu perfil ni enviarte solicitudes, y no recibe ningún aviso.{" "}
        <Link href="/privacidad" className="font-bold text-primary hover:underline">Más sobre amigos y privacidad</Link>
      </p>
    </div>
  );
}
