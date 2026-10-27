"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import { useSesionesGuardadas } from "@/components/SesionesGuardadasProvider";
import { diaCompleto, etiquetaRelativa, hoyMadrid } from "@/lib/fechasMadrid";
import { listarSesiones, marcarVista, quitarSesion } from "@/lib/sesiones";

const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);
const nombreDia = (fecha, hoy) => {
  const relativa = etiquetaRelativa(fecha, hoy);
  return relativa ? `${relativa}, ${diaCompleto(fecha)}` : capitalizar(diaCompleto(fecha));
};

// Próximas en grupos por día, en su orden: [{ fecha, sesiones }]
function porDia(sesiones) {
  const dias = [];
  for (const s of sesiones) {
    if (dias.at(-1)?.fecha !== s.fecha) dias.push({ fecha: s.fecha, sesiones: [] });
    dias.at(-1).sesiones.push(s);
  }
  return dias;
}

// Una sesión guardada. La copia vale aunque el pase ya no exista; sin pelicula_id no hay ficha ni "La vi".
function Tarjeta({ sesion, futura, hoy, usuario, onQuitar, onVista }) {
  const [ocupado, setOcupado] = useState(false);
  const hora = sesion.hora.slice(0, 5);
  const accion = async (fn) => {
    setOcupado(true);
    if (!(await fn(sesion))) setOcupado(false);
  };
  return (
    <li className="flex gap-3 md:gap-4 py-4 border-b border-line">
      <div className="w-12 md:w-16 aspect-[2/3] shrink-0 overflow-hidden border border-line bg-surface">
        {sesion.poster_url && <img src={sesion.poster_url} alt="" className="w-full h-full object-cover" loading="lazy" />}
      </div>
      <div className="min-w-0 flex-1">
        {sesion.pelicula_id ? (
          <a href={`/pelicula/${sesion.pelicula_id}`} className="font-display font-bold uppercase text-foreground hover:text-primary break-words">{sesion.titulo}</a>
        ) : (
          <span className="font-display font-bold uppercase text-foreground break-words">{sesion.titulo}</span>
        )}
        <p className="mt-1 text-sm text-muted break-words">
          <Link href={`/cines/${sesion.cine_slug}`} className="text-foreground hover:text-primary hover:underline">{sesion.cine_nombre}</Link>
          {" · "}
          {!futura && <>{nombreDia(sesion.fecha, hoy)} · </>}
          <time dateTime={`${sesion.fecha}T${sesion.hora}`} className="font-semibold text-foreground">{hora}</time>
          {sesion.idioma && sesion.idioma !== "Español" && <> · {sesion.idioma}</>}
        </p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {futura && sesion.link_compra && (
            <a href={sesion.link_compra} target="_blank" rel="noopener noreferrer" className={`${BOTON_PRIMARIO} rounded-lg`}>
              Comprar<span className="sr-only"> entradas para {sesion.titulo} (se abre en una pestaña nueva)</span>
            </a>
          )}
          {!futura && sesion.diario_entrada_id && (
            <span className="text-sm text-foreground">
              Vista ✓ · <Link href={`/u/${usuario}/diario`} className="font-bold text-primary hover:underline">En tu diario</Link>
            </span>
          )}
          {!futura && !sesion.diario_entrada_id && sesion.pelicula_id && (
            <button type="button" onClick={() => accion(onVista)} disabled={ocupado} className={`${BOTON_SECUNDARIO} rounded-lg`}>
              La vi<span className="sr-only">: apuntar {sesion.titulo} en mi diario</span>
            </button>
          )}
          <button type="button" onClick={() => accion(onQuitar)} disabled={ocupado} className="px-2 py-1.5 text-xs font-bold text-muted hover:text-red-600 disabled:opacity-60">
            Quitar<span className="sr-only"> {sesion.titulo}, {hora}</span>
          </button>
        </div>
      </div>
    </li>
  );
}

// Pestaña Sesiones de mi perfil: la agenda privada (GET /me/sesiones), próximas por día y ya pasadas
export default function MisSesiones({ usuario }) {
  const { olvidar } = useSesionesGuardadas();
  const [agenda, setAgenda] = useState(null); // { proximas, pasadas } o { error }
  const [aviso, setAviso] = useState("");
  const hoy = hoyMadrid();

  useEffect(() => {
    listarSesiones().then(setAgenda).catch((err) => setAgenda({ error: err.message }));
  }, []);

  const cambiar = (id, editar) =>
    setAgenda((a) => ({ proximas: editar(a.proximas, id), pasadas: editar(a.pasadas, id) }));

  const quitar = async (sesion) => {
    try {
      await quitarSesion(sesion.id);
      cambiar(sesion.id, (lista, id) => lista.filter((s) => s.id !== id));
      olvidar(sesion.id);
      setAviso(`«${sesion.titulo}» quitada de tus sesiones`);
      return true;
    } catch (err) {
      setAviso(err.message);
      return false;
    }
  };

  const vista = async (sesion) => {
    try {
      const nueva = await marcarVista(sesion.id);
      cambiar(sesion.id, (lista, id) => lista.map((s) => (s.id === id ? nueva : s)));
      setAviso(`«${sesion.titulo}» apuntada en tu diario`);
      return true;
    } catch (err) {
      setAviso(err.message);
      return false;
    }
  };

  if (!agenda) return <div aria-busy="true" aria-label="Cargando tus sesiones" className="mt-6 h-24 bg-surface animate-pulse" />;
  if (agenda.error) return <p role="alert" className="py-8 text-red-600">{agenda.error}</p>;

  const tarjeta = (s, futura) => (
    <Tarjeta key={s.id} sesion={s} futura={futura} hoy={hoy} usuario={usuario} onQuitar={quitar} onVista={vista} />
  );
  return (
    <div>
      <p role="status" aria-live="polite" className="text-sm font-semibold text-primary min-h-5">{aviso}</p>
      {!agenda.proximas.length && !agenda.pasadas.length ? (
        <p className="py-10 text-center text-muted">
          Aún no tienes sesiones guardadas. Pulsa la hora de una sesión en la{" "}
          <Link href="/" className="font-bold text-primary hover:underline">cartelera</Link> y elige «Guardar sesión»: aparecerá
          aquí, con su enlace de compra, y cuando la hayas visto podrás apuntarla en tu diario.
        </p>
      ) : (
        <>
          <section aria-labelledby="sesiones-proximas" className="mt-4">
            <h4 id="sesiones-proximas" className="text-sm font-bold uppercase tracking-wider text-foreground">Próximas</h4>
            {agenda.proximas.length ? porDia(agenda.proximas).map((d) => (
              <section key={d.fecha} aria-labelledby={`dia-${d.fecha}`} className="mt-4">
                <h5 id={`dia-${d.fecha}`} className="text-xs font-bold uppercase tracking-wider text-muted border-b border-line pb-2">{nombreDia(d.fecha, hoy)}</h5>
                <ul>{d.sesiones.map((s) => tarjeta(s, true))}</ul>
              </section>
            )) : <p className="mt-2 text-sm text-muted">No tienes sesiones próximas guardadas.</p>}
          </section>
          {agenda.pasadas.length > 0 && (
            <section aria-labelledby="sesiones-pasadas" className="mt-10">
              <h4 id="sesiones-pasadas" className="text-sm font-bold uppercase tracking-wider text-foreground">Ya pasadas</h4>
              <ul className="mt-2">{agenda.pasadas.map((s) => tarjeta(s, false))}</ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
