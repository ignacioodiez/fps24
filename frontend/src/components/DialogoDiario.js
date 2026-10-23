"use client";

import { useEffect, useId, useRef, useState } from "react";
import NotaEstrellas from "@/components/NotaEstrellas";
import { useAuth } from "@/components/AuthProvider";
import { COMENTARIO_MAX, ayerMadrid, borrar, cinesDelDia, crear, editar, hoyMadrid, todosLosCines } from "@/lib/diario";

const OTRO = "__otro";
const ETIQUETA = "block text-xs font-bold uppercase tracking-wider text-muted mb-1";
const CAMPO = "w-full border border-line bg-background px-3 py-2 text-foreground focus:border-primary focus:outline-none";
export const BOTON_PRIMARIO = "px-4 py-2 bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-60";
export const BOTON_SECUNDARIO = "px-4 py-2 border border-line text-sm font-bold text-foreground hover:border-primary hover:text-primary transition-colors disabled:opacity-60";

// Crear (sin entrada) o editar (con entrada) una película del diario. <dialog> nativo en modo modal: el foco
// queda dentro, Esc cierra y al cerrar vuelve al botón que lo abrió. Se monta abierto; cerrar = onCerrar().
export default function DialogoDiario({ pelicula, entrada = null, fechaInicial, repeticionInicial = false, onCerrar, onGuardado, onBorrado }) {
  const { abrirLogin, salir } = useAuth();
  const dialogo = useRef(null);
  const id = useId();
  const [fecha, setFecha] = useState(entrada?.fecha_vista ?? fechaInicial);
  const [cine, setCine] = useState(entrada?.cine?.slug ?? "");
  const [otro, setOtro] = useState(false);
  const [nota, setNota] = useState(entrada?.nota ?? null);
  const [comentario, setComentario] = useState(entrada?.comentario ?? "");
  const [repeticion, setRepeticion] = useState(entrada?.repeticion ?? repeticionInicial);
  const [cinesDia, setCinesDia] = useState({ fecha: null, lista: [] });
  const [todos, setTodos] = useState(null);
  const [estado, setEstado] = useState("inicio"); // inicio | guardando | confirmarBorrado
  const [error, setError] = useState(null);

  useEffect(() => {
    dialogo.current?.showModal();
  }, []);

  // Cines con pases de la película ese día (incluye pases pasados)
  useEffect(() => {
    if (!fecha) return;
    let vigente = true;
    cinesDelDia(pelicula.id, fecha)
      .then((lista) => vigente && setCinesDia({ fecha, lista }))
      .catch(() => vigente && setCinesDia({ fecha, lista: [] }));
    return () => { vigente = false; };
  }, [pelicula.id, fecha]);

  // Un cine que no está entre los del día (o "Otro cine…") se elige en la lista completa
  const delDia = cinesDia.fecha === fecha ? cinesDia.lista : [];
  const enOtro = otro || (cine !== "" && cinesDia.fecha === fecha && !delDia.some((c) => c.slug === cine));
  useEffect(() => {
    if (!enOtro || todos) return;
    todosLosCines().then(setTodos).catch(() => setTodos([]));
  }, [enOtro, todos]);

  const cerrar = () => dialogo.current?.close();

  const elegirCine = (v) => {
    setOtro(v === OTRO);
    if (v !== OTRO) setCine(v);
  };

  const guardar = async (e) => {
    e.preventDefault();
    setError(null);
    setEstado("guardando");
    const datos = { fecha_vista: fecha, cine_slug: cine || null, nota, comentario: comentario.trim() || null, repeticion };
    try {
      const guardada = entrada ? await editar(entrada.id, datos) : await crear({ pelicula_id: pelicula.id, ...datos });
      onGuardado(guardada, Boolean(entrada));
      cerrar();
    } catch (err) {
      setError(err);
      setEstado("inicio");
    }
  };

  const eliminar = async () => {
    setError(null);
    setEstado("guardando");
    try {
      await borrar(entrada.id);
      onBorrado(entrada.id);
      cerrar();
    } catch (err) {
      setError(err);
      setEstado("inicio");
    }
  };

  const ocupado = estado === "guardando";

  return (
    <dialog
      ref={dialogo}
      aria-labelledby={`${id}-titulo`}
      onClose={onCerrar}
      onClick={(e) => e.target === e.currentTarget && cerrar()}
      className="m-auto w-[calc(100%-2rem)] max-w-lg max-h-[calc(100dvh-2rem)] overflow-y-auto border border-line bg-background text-foreground p-0 backdrop:bg-black/40"
    >
      <form onSubmit={guardar} className="p-5 md:p-6 space-y-5 text-left">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h2 id={`${id}-titulo`} className="text-xl font-display font-bold uppercase">
              {entrada ? "Editar entrada" : "Añadir al diario"}
            </h2>
            <p className="text-sm text-muted truncate">{pelicula.titulo}</p>
          </div>
          <button type="button" onClick={cerrar} aria-label="Cerrar" className="text-muted hover:text-primary text-xl leading-none">×</button>
        </div>

        <div>
          <label htmlFor={`${id}-fecha`} className={ETIQUETA}>Fecha en que la viste</label>
          <div className="flex gap-2">
            <input
              id={`${id}-fecha`} type="date" required value={fecha} max={hoyMadrid()}
              onChange={(e) => setFecha(e.target.value)} className={`${CAMPO} min-w-0`}
            />
            {[["Hoy", hoyMadrid()], ["Ayer", ayerMadrid()]].map(([etiqueta, valor]) => (
              <button key={etiqueta} type="button" onClick={() => setFecha(valor)} aria-pressed={fecha === valor} className={`${BOTON_SECUNDARIO} aria-pressed:border-primary aria-pressed:text-primary`}>
                {etiqueta}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor={`${id}-cine`} className={ETIQUETA}>Cine</label>
          <select id={`${id}-cine`} value={enOtro ? OTRO : cine} onChange={(e) => elegirCine(e.target.value)} className={CAMPO}>
            {delDia.map((c) => (
              <option key={c.slug} value={c.slug}>{c.nombre} · {c.horas.join(", ")}</option>
            ))}
            <option value={OTRO}>Otro cine…</option>
            <option value="">No lo recuerdo</option>
          </select>
          {enOtro && (
            <select aria-label="Elige el cine" value={cine} onChange={(e) => setCine(e.target.value)} className={CAMPO}>
              <option value="">{todos ? "Elige un cine…" : "Cargando cines…"}</option>
              {todos?.map((c) => <option key={c.slug} value={c.slug}>{c.nombre}</option>)}
            </select>
          )}
        </div>

        <div>
          <p id={`${id}-nota`} className={ETIQUETA}>Tu nota</p>
          <NotaEstrellas valor={nota} onCambiar={setNota} idEtiqueta={`${id}-nota`} />
        </div>

        <div>
          <label htmlFor={`${id}-comentario`} className={ETIQUETA}>Comentario</label>
          <textarea
            id={`${id}-comentario`} rows={4} maxLength={COMENTARIO_MAX} value={comentario}
            onChange={(e) => setComentario(e.target.value)} aria-describedby={`${id}-contador`}
            className={`${CAMPO} resize-y`}
          />
          <p id={`${id}-contador`} className="mt-1 text-xs text-muted text-right">{comentario.length}/{COMENTARIO_MAX}</p>
        </div>

        <label className="flex items-center gap-2 text-sm text-foreground">
          <input type="checkbox" checked={repeticion} onChange={(e) => setRepeticion(e.target.checked)} className="w-4 h-4 accent-primary" />
          Es una repetición (ya la habías visto antes)
        </label>

        {error && (
          <div role="alert" className="text-sm text-red-600 space-y-2">
            <p>{error.message}</p>
            {/* Token caducado o revocado: se cierra la sesión local para que el panel de entrar se pueda abrir */}
            {error.status === 401 && (
              <button type="button" onClick={() => { cerrar(); salir().then(() => abrirLogin("Inicia sesión para guardar tu diario")); }} className={BOTON_SECUNDARIO}>
                Iniciar sesión
              </button>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 pt-1">
          <button type="submit" disabled={ocupado} className={BOTON_PRIMARIO}>{ocupado ? "Guardando…" : "Guardar"}</button>
          <button type="button" onClick={cerrar} className={BOTON_SECUNDARIO}>Cancelar</button>
          {entrada && (estado === "confirmarBorrado" ? (
            <span className="ml-auto flex flex-wrap items-center gap-2 text-sm">
              ¿Eliminar esta entrada?
              <button type="button" onClick={eliminar} className="px-3 py-2 bg-red-600 text-white font-bold hover:opacity-90">Sí, eliminar</button>
              <button type="button" onClick={() => setEstado("inicio")} className="px-3 py-2 font-bold text-muted hover:text-foreground">No</button>
            </span>
          ) : (
            <button type="button" disabled={ocupado} onClick={() => setEstado("confirmarBorrado")} className="ml-auto px-3 py-2 text-sm font-bold text-red-600 hover:underline disabled:opacity-60">
              Eliminar
            </button>
          ))}
        </div>
      </form>
    </dialog>
  );
}
