"use client";

import Link from "next/link";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import DialogoDiario, { BOTON_PRIMARIO, BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import NotaEstrellas from "@/components/NotaEstrellas";
import BuscadorPeliculas from "@/components/BuscadorPeliculas";
import { borrar, hoyMadrid, listar } from "@/lib/diario";

const POR_PAGINA = 20;
const COMENTARIO_CORTO = 240; // más largo (o con más de 3 líneas) se recorta con "ver más"

// Fechas "YYYY-MM-DD" de la API: en UTC para que el huso del navegador no las mueva (como en CarteleraCine)
const formato = (fecha, opciones) => new Date(`${fecha}T00:00Z`).toLocaleDateString("es-ES", { timeZone: "UTC", ...opciones });
const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);
const nombreMes = (fecha) => capitalizar(formato(fecha, { month: "long", year: "numeric" }).replace(" de ", " "));
// Mismo orden que el backend: fecha vista y, a igual fecha, la última apuntada primero
const ordenar = (lista) => [...lista].sort((a, b) => b.fecha_vista.localeCompare(a.fecha_vista) || b.creado_en.localeCompare(a.creado_en) || b.id - a.id);

function Comentario({ texto }) {
  const [abierto, setAbierto] = useState(false);
  const largo = texto.length > COMENTARIO_CORTO || texto.split("\n").length > 3;
  return (
    <div className="mt-2 text-sm text-foreground">
      {/* Texto plano con sus saltos de línea: nunca HTML */}
      <p className={`whitespace-pre-wrap break-words ${largo && !abierto ? "line-clamp-3" : ""}`}>{texto}</p>
      {largo && (
        <button type="button" onClick={() => setAbierto((v) => !v)} aria-expanded={abierto} className="mt-1 text-xs font-bold text-primary hover:underline">
          {abierto ? "ver menos" : "ver más"}
        </button>
      )}
    </div>
  );
}

function Entrada({ entrada, marcada, onEditar, onBorrar }) {
  const [confirmar, setConfirmar] = useState(false);
  const [borrando, setBorrando] = useState(false);
  const { pelicula, cine } = entrada;

  const eliminar = async () => {
    setBorrando(true);
    if (!(await onBorrar(entrada))) setBorrando(false);
  };

  return (
    <li id={`entrada-${entrada.id}`} className={`flex gap-3 md:gap-4 py-4 border-b border-line transition-colors duration-700 ${marcada ? "bg-primary-soft" : ""}`}>
      <div className="w-12 md:w-16 aspect-[2/3] shrink-0 overflow-hidden border border-line bg-surface">
        {pelicula.poster_url && <img src={pelicula.poster_url} alt="" className="w-full h-full object-cover" loading="lazy" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          {/* <a> y no <Link>: con Link se abriría la vista rápida encima y el diario no se enteraría de los cambios */}
          <a href={`/pelicula/${pelicula.id}`} className="font-display font-bold uppercase text-foreground hover:text-primary break-words">
            {pelicula.titulo}
          </a>
          {pelicula.anio && <span className="text-sm text-muted">{pelicula.anio}</span>}
          {entrada.repeticion && (
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary bg-primary-soft px-1.5 py-0.5">Repetición</span>
          )}
        </div>
        <p className="mt-1 text-sm text-muted">
          <time dateTime={entrada.fecha_vista}>{formato(entrada.fecha_vista, { day: "numeric", month: "long", year: "numeric" })}</time>
          {cine && <> · <Link href={`/cines/${cine.slug}`} className="text-foreground hover:text-primary hover:underline">{cine.nombre}</Link></>}
        </p>
        {entrada.nota && <div className="mt-1"><NotaEstrellas valor={entrada.nota} soloLectura /></div>}
        {entrada.comentario && <Comentario texto={entrada.comentario} />}

        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm font-bold">
          {confirmar ? (
            <>
              <span className="font-normal text-foreground">¿Eliminar esta entrada?</span>
              <button type="button" onClick={eliminar} disabled={borrando} className="text-red-600 hover:underline disabled:opacity-60">
                {borrando ? "Eliminando…" : "Sí, eliminar"}
              </button>
              <button type="button" onClick={() => setConfirmar(false)} className="text-muted hover:text-foreground">No</button>
            </>
          ) : (
            <>
              <button type="button" aria-haspopup="dialog" onClick={() => onEditar(entrada)} className="text-primary hover:underline">
                Editar<span className="sr-only"> {pelicula.titulo}</span>
              </button>
              <button type="button" onClick={() => setConfirmar(true)} className="text-muted hover:text-red-600">
                Eliminar<span className="sr-only"> {pelicula.titulo}</span>
              </button>
            </>
          )}
        </div>
      </div>
    </li>
  );
}

// total: lo guarda Perfil, que lo enseña en la cabecera
function PestanaDiario({ total, setTotal }) {
  const [entradas, setEntradas] = useState([]);
  const [estado, setEstado] = useState("cargando"); // cargando | listo | error
  const [error, setError] = useState("");
  const [editando, setEditando] = useState(null);
  const [aviso, setAviso] = useState("");
  const [nueva, setNueva] = useState(null); // película elegida en el buscador
  const [marcada, setMarcada] = useState(null); // id de la entrada recién añadida
  const [buscador, setBuscador] = useState(0); // cambiar la key vacía el buscador

  // desplazamiento 0 = primera página; si no, se añade a lo cargado (sin repetir: un borrado mueve el desplazamiento)
  const pedirPagina = useCallback((desplazamiento) => {
    listar(POR_PAGINA, desplazamiento)
      .then((datos) => {
        setEntradas((previas) => {
          const base = desplazamiento ? previas : [];
          return ordenar([...base, ...datos.entradas.filter((e) => !base.some((b) => b.id === e.id))]);
        });
        setTotal(datos.total);
        setEstado("listo");
      })
      .catch((err) => {
        setError(err.message);
        setEstado("error");
      });
  }, [setTotal]);

  useEffect(() => pedirPagina(0), [pedirPagina]);

  // La entrada recién añadida: a la vista, con el foco en su título y marcada un momento
  useEffect(() => {
    if (!marcada) return;
    const li = document.getElementById(`entrada-${marcada}`);
    li?.scrollIntoView({ block: "center" });
    li?.querySelector("a")?.focus({ preventScroll: true });
    const t = setTimeout(() => setMarcada(null), 2000);
    return () => clearTimeout(t);
  }, [marcada]);

  const cargarMas = () => {
    setEstado("cargando");
    pedirPagina(entradas.length);
  };

  const quitar = (id) => {
    setEntradas((previas) => previas.filter((e) => e.id !== id));
    setTotal((t) => t - 1);
  };

  const borrarEntrada = async (entrada) => {
    try {
      await borrar(entrada.id);
      quitar(entrada.id);
      setAviso(`«${entrada.pelicula.titulo}» eliminada del diario`);
      return true;
    } catch (err) {
      setAviso(err.message);
      return false;
    }
  };


  // Agrupadas por mes, en el orden de la lista
  const meses = [];
  for (const e of entradas) {
    const clave = e.fecha_vista.slice(0, 7);
    if (meses.at(-1)?.clave !== clave) meses.push({ clave, entradas: [] });
    meses.at(-1).entradas.push(e);
  }

  return (
    <div>
      <BuscadorPeliculas key={buscador} onElegir={setNueva} />
      <p role="status" aria-live="polite" className="mt-2 text-sm font-semibold text-primary min-h-5">{aviso}</p>

      {estado === "cargando" && entradas.length === 0 ? (
        <Esqueleto />
      ) : estado === "error" && entradas.length === 0 ? (
        <p role="alert" className="py-8 text-red-600">{error}</p>
      ) : entradas.length === 0 ? (
        <p className="py-12 text-center text-lg text-foreground">
          Tu diario está vacío. Busca arriba una película que hayas visto para añadirla.
        </p>
      ) : (
        <>
          <p className="text-sm text-muted">{total} {total === 1 ? "película apuntada" : "películas apuntadas"}</p>
          {meses.map((m) => (
            <section key={m.clave} aria-labelledby={`mes-${m.clave}`} className="mt-6">
              <h3 id={`mes-${m.clave}`} className="text-xs font-bold uppercase tracking-wider text-muted border-b border-line pb-2">
                {nombreMes(`${m.clave}-01`)}
              </h3>
              <ul>
                {m.entradas.map((e) => (
                  <Entrada key={e.id} entrada={e} marcada={e.id === marcada} onEditar={setEditando} onBorrar={borrarEntrada} />
                ))}
              </ul>
            </section>
          ))}
          {entradas.length < total && (
            <div className="mt-6 text-center">
              <button type="button" onClick={cargarMas} disabled={estado === "cargando"} className={BOTON_SECUNDARIO}>
                {estado === "cargando" ? "Cargando…" : "Cargar más"}
              </button>
              {estado === "error" && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
            </div>
          )}
        </>
      )}

      {nueva && (
        <DialogoDiario
          pelicula={nueva} fechaInicial={hoyMadrid()}
          onCerrar={() => setNueva(null)}
          onGuardado={(guardada) => {
            setEntradas((previas) => ordenar([...previas, guardada]));
            setTotal((t) => t + 1);
            setAviso(`«${guardada.pelicula.titulo}» añadida a tu diario`);
            setMarcada(guardada.id);
            setBuscador((k) => k + 1);
          }}
        />
      )}

      {editando && (
        <DialogoDiario
          pelicula={editando.pelicula} entrada={editando}
          onCerrar={() => setEditando(null)}
          onGuardado={(guardada) => {
            setEntradas((previas) => ordenar(previas.map((e) => (e.id === guardada.id ? guardada : e))));
            setAviso(`«${guardada.pelicula.titulo}» actualizada`);
          }}
          onBorrado={(id) => {
            quitar(id);
            setAviso(`«${editando.pelicula.titulo}» eliminada del diario`);
          }}
        />
      )}
    </div>
  );
}

// Pestañas del perfil: añadir una ("Quiero verla", "Ajustes") es añadir una línea
const PESTANAS = [
  { id: "diario", etiqueta: "Diario", Contenido: PestanaDiario },
];

function Esqueleto() {
  return (
    <div aria-busy="true" aria-label="Cargando" className="space-y-4 py-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex gap-4">
          <div className="w-12 md:w-16 aspect-[2/3] bg-surface animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-5 w-1/2 bg-surface animate-pulse" />
            <div className="h-4 w-1/3 bg-surface animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Estilo plano de la barra de secciones (NavSecciones): texto en mayúsculas y línea violeta en la activa
const PESTANA = "flex items-center min-h-11 whitespace-nowrap px-3 md:px-4 text-xs md:text-[13px] font-semibold uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary";

export default function Perfil() {
  const { usuario, cargando, abrirLogin } = useAuth();
  const [activa, setActiva] = useState(PESTANAS[0].id);
  const [total, setTotal] = useState(null); // del GET /diario; null hasta que llega
  const pestanas = useRef({});
  const id = useId();

  if (cargando) {
    return <div className="max-w-3xl mx-auto px-4 md:px-6"><Esqueleto /></div>;
  }

  if (!usuario) {
    return (
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-12 text-center space-y-4">
        <h2 className="text-3xl md:text-5xl font-black font-display uppercase text-primary">Mi perfil</h2>
        <p className="text-muted text-lg">
          {AUTH_DISPONIBLE ? "Inicia sesión para ver tu diario de películas." : "El inicio de sesión no está disponible ahora mismo."}
        </p>
        {AUTH_DISPONIBLE && (
          <button type="button" onClick={() => abrirLogin("Inicia sesión para ver tu diario")} aria-haspopup="dialog" className={BOTON_PRIMARIO}>
            Iniciar sesión
          </button>
        )}
      </div>
    );
  }

  // Flechas, Inicio y Fin se mueven entre pestañas (patrón tabs de WAI-ARIA)
  const tecla = (e) => {
    const pos = PESTANAS.findIndex((p) => p.id === activa);
    const destino = { ArrowRight: pos + 1, ArrowLeft: pos - 1, Home: 0, End: PESTANAS.length - 1 }[e.key];
    if (destino === undefined) return;
    e.preventDefault();
    const nueva = PESTANAS[(destino + PESTANAS.length) % PESTANAS.length].id;
    setActiva(nueva);
    pestanas.current[nueva]?.focus();
  };

  const { Contenido } = PESTANAS.find((p) => p.id === activa);

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-6">
      <div className="mb-6">
        <h2 className="text-3xl md:text-5xl font-black font-display uppercase text-primary">Mi perfil</h2>
        <p className="mt-1 text-muted">
          <span className="break-all">{usuario.email}</span>
          {total !== null && <> · {total} {total === 1 ? "película" : "películas"} en tu diario</>}
        </p>
      </div>

      <div role="tablist" aria-label="Secciones del perfil" onKeyDown={tecla} className="flex overflow-x-auto bg-surface border-y border-line">
        {PESTANAS.map((p) => (
          <button
            key={p.id} ref={(el) => (pestanas.current[p.id] = el)} type="button" role="tab" id={`${id}-${p.id}`}
            aria-selected={p.id === activa} aria-controls={`${id}-panel`} tabIndex={p.id === activa ? 0 : -1}
            onClick={() => setActiva(p.id)}
            className={`${PESTANA} ${p.id === activa ? "text-primary shadow-[inset_0_-3px_0_var(--primary)]" : "text-muted hover:text-foreground"}`}
          >
            {p.etiqueta}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${activa}`} className="pt-4">
        <Contenido total={total} setTotal={setTotal} />
      </div>
    </div>
  );
}
