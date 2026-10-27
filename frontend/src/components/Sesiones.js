"use client";

import { useId, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { cleanCinemaName, extractTime, isDiaEspectador, textoSala } from "@/utils/helpers";
import BotonFavorito, { MarcaFavorito } from "@/components/BotonFavorito";
import { useFavoritos } from "@/components/FavoritosProvider";
import { favoritosPrimero } from "@/lib/favoritos";

// Piezas de sesiones con el estilo de la cartelera de la portada. Las usan la portada (MovieGrid),
// la vista rápida (ModalPelicula) y la página completa de película, para que se vean igual.

// Límites de la ficha antes de "Ver más": cines (vista "Por cine"), sesiones (vista "Por hora") y
// resúmenes de "Otros días" visibles. La portada no tiene límites.
const LIMITES = {
  modal: { cines: 3, sesiones: 8, dias: 3 },
  pagina: { cines: 5, sesiones: 15, dias: 5 },
};
const HORAS_POR_CINE = 8; // horas visibles por cine en la ficha; el resto, tras el chip "+N"

// Clave de día en hora local ("YYYY-MM-DD"), como la cartelera
export const claveDia = (fecha) => new Date(fecha).toLocaleDateString("sv-SE");
// ?dia=YYYY-MM-DD de una tarjeta con sesión sugerida: vale solo si ese día tiene sesiones desde hoy; si no, null
export const diaConSesiones = (dia, pases) =>
  dia && dia >= claveDia(new Date()) && pases.some((p) => claveDia(p.fecha_hora) === dia) ? dia : null;
const capitalizar = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);
const nombreDia = (clave) =>
  capitalizar(new Date(`${clave}T00:00`).toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" }));
const diaCorto = (clave) => {
  const d = new Date(`${clave}T00:00`);
  return `${capitalizar(d.toLocaleDateString("es-ES", { weekday: "short" }).replace(".", ""))} ${d.getDate()}`;
};
const plural = (n, una, varias) => `${n} ${n === 1 ? una : varias}`;

// Contenedor que hace scroll del elemento (el panel del modal o la página)
const contenedorScroll = (el) => {
  for (let p = el.parentElement; p; p = p.parentElement) {
    const { overflowY } = getComputedStyle(p);
    if ((overflowY === "auto" || overflowY === "scroll") && p.scrollHeight > p.clientHeight) return p;
  }
  return document.scrollingElement;
};

// Botón "Ver X más / Ver menos" con el estilo de botón secundario de la portada ("Salas y precios").
// Al plegar, el contenido de encima encoge: se compensa el scroll de su contenedor para que el botón no se mueva.
function BotonVerMas({ abierto, onAlternar, texto, controla, chip = false, etiqueta }) {
  const boton = useRef(null);
  const pulsar = () => {
    const antes = boton.current.getBoundingClientRect().top;
    onAlternar();
    if (!abierto) return;
    requestAnimationFrame(() => {
      if (!boton.current) return;
      contenedorScroll(boton.current).scrollTop += boton.current.getBoundingClientRect().top - antes;
    });
  };
  const estilo = chip
    ? "px-3 py-1 rounded-lg text-xs font-semibold border border-line bg-surface text-muted hover:border-primary hover:text-primary"
    : "px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wide border border-line bg-background text-foreground hover:border-primary hover:text-primary";
  return (
    <button ref={boton} type="button" onClick={pulsar} aria-expanded={abierto} aria-controls={controla} aria-label={etiqueta}
            className={`${estilo} transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary`}>
      {abierto ? "Ver menos" : texto}
    </button>
  );
}

// Minuto actual (ms) para apagar las horas pasadas; null en el servidor y al hidratar (sin desajuste)
const MINUTO = 60000;
const suscribirReloj = (aviso) => {
  const t = setInterval(aviso, MINUTO);
  return () => clearInterval(t);
};
const useAhora = () => useSyncExternalStore(suscribirReloj, () => Math.floor(Date.now() / MINUTO) * MINUTO, () => null);

// Precio de una sesión salvo "Consultar"
const precioDe = (pase) => (pase.precio && pase.precio !== "Consultar" ? pase.precio : null);

// Nombre de un cine que lleva a su página; sin slug, texto normal. reemplazar: desde el modal, sustituye su
// entrada del historial para que "atrás" vuelva a la portada y no reabra el modal.
export function EnlaceCine({ slug, reemplazar = false, className = "", title, children }) {
  if (!slug) return <span title={title} className={className}>{children}</span>;
  return (
    <Link href={`/cines/${slug}`} replace={reemplazar} title={title} className={`rounded focus-visible:outline-2 focus-visible:outline-offset-2 ${className}`}>
      {children}
    </Link>
  );
}

// Chip de idioma: VOSE neutro y legible en cualquier chip (también el violeta de los especiales y su hover);
// otros idiomas, discretos; nada si es en español
export function ChipIdioma({ idioma }) {
  if (!idioma || idioma === "Español") return null;
  if (idioma === "VOSE") {
    return <span className="text-[10px] leading-none px-1 py-0.5 rounded border border-muted bg-background text-foreground font-bold uppercase tracking-wide">VOSE</span>;
  }
  return <span className="text-[9px] bg-surface px-1 rounded font-medium text-muted border border-line">{idioma}</span>;
}

// Rejilla de cines dentro de la tarjeta de una película: 2 columnas si la tarjeta mide 440px o más (container query;
// el padre lleva @container), por filas. Entre cines, una línea fina; la primera fila sin ella.
export const REJILLA_CINES = "grid gap-x-6 gap-y-3 @[440px]:grid-cols-2 [&>*]:border-t [&>*]:border-line [&>*]:pt-3 [&>*:first-child]:border-t-0 [&>*:first-child]:pt-0 @[440px]:[&>*:nth-child(2)]:border-t-0 @[440px]:[&>*:nth-child(2)]:pt-0";

// Cabecera de un cine: el nombre como texto, enlace a su página (★ delante si es favorito).
// conFavorito: la estrella para marcarlo o quitarlo (modal y ficha). A la derecha, "Espectador" si ese día lo es
// en ese cine y el precio del día.
export function CabeceraCine({ nombre, fecha, slug, conFavorito = false, precio = null, reemplazar = false }) {
  const espectador = isDiaEspectador(nombre, fecha);
  const texto = cleanCinemaName(nombre);
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <h3 className="flex min-w-0 text-xs font-bold uppercase tracking-wide text-foreground">
        <EnlaceCine slug={slug} reemplazar={reemplazar}
                    className={`truncate underline-offset-2 ${slug ? "hover:text-primary hover:underline focus-visible:underline focus-visible:outline-primary transition-colors" : ""}`}>
          {!conFavorito && <MarcaFavorito slug={slug} />} {texto}
        </EnlaceCine>
      </h3>
      {conFavorito && <BotonFavorito pequeno slug={slug} nombre={texto} />}
      {(espectador || precio) && (
        <span className="ml-auto shrink-0 flex items-center gap-1.5 text-xs font-bold text-foreground">
          {espectador && <span className="px-1.5 py-0.5 rounded bg-accent">Espectador</span>}
          {precio}
        </span>
      )}
    </div>
  );
}

// Chip de hora. Con link_compra es el botón de compra (pestaña nueva); sin él, apagado y no clicable.
// conPrecio: el precio salvo "Consultar"; conSala: la sala ("Sala 9") si no repite el cine. La portada no usa ninguno.
// pasada: ya ha empezado (apagada).
export function ChipHora({ pase, cine, conPrecio = false, conSala = false, pasada = false }) {
  const hora = pase.hora ?? extractTime(pase.fecha_hora); // hora: "HH:MM" ya formateada (/cines/{slug}, sin depender del locale)
  const precio = conPrecio ? precioDe(pase) : null;
  const sala = conSala ? textoSala(pase.sala, cine) : null;
  const contenido = (
    <>
      <span className="text-sm">{hora}</span>
      <ChipIdioma idioma={pase.idioma} />
      {sala && <span className="text-[10px] font-medium opacity-70">{sala}</span>}
      {precio && <span className="text-[10px] font-medium opacity-80">{precio}</span>}
    </>
  );
  const base = `px-3 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 border ${pasada ? "opacity-50" : ""}`;

  if (!pase.link_compra) {
    return <span title={sala || undefined} className={`${base} bg-surface text-muted border-line opacity-60 cursor-default`}>{contenido}</span>;
  }
  return (
    <a
      href={pase.link_compra}
      target="_blank"
      rel="noopener noreferrer"
      title={sala || undefined}
      aria-label={`Comprar entrada para las ${hora} en ${cleanCinemaName(cine)}${sala ? `, ${sala}` : ""}${pase.idioma === "VOSE" ? ", VOSE" : ""}${pasada ? ", ya ha empezado" : ""}`}
      className={`${base} focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
        pase.es_evento_especial
          ? "bg-primary-soft text-primary border-primary hover:bg-primary hover:text-white"
          : "bg-background text-foreground border-line hover:border-primary hover:text-primary"}`}
    >
      {contenido}
    </a>
  );
}

// Un cine con sus horas: bloque con cabecera + chips (portada, vista rápida y ficha). pases en orden de hora.
// maxHoras: en la ficha, horas visibles antes del chip "+N" (la portada no limita).
// El precio va en la cabecera si es el mismo todo el día; si cambia (según sala) y conPrecio, en cada hora.
export function SesionesCine({ cine, pases, conPrecio = false, conSala = false, maxHoras = Infinity, conFavorito = false, reemplazar = false }) {
  const [abierto, setAbierto] = useState(false);
  const id = useId();
  const ahora = useAhora();
  const ocultas = pases.length - maxHoras;
  const visibles = abierto || ocultas <= 0 ? pases : pases.slice(0, maxHoras);
  const precios = new Set(pases.map(precioDe).filter(Boolean));
  return (
    <div className="flex flex-col gap-1.5 min-w-0">
      <CabeceraCine nombre={cine} fecha={pases[0]?.fecha_hora} slug={pases[0]?.cine_slug} conFavorito={conFavorito}
                    precio={precios.size === 1 ? [...precios][0] : null} reemplazar={reemplazar} />
      <div id={id} className="flex flex-wrap gap-2">
        {visibles.map((pase, i) => (
          <ChipHora key={pase.id ?? i} pase={pase} cine={cine} conPrecio={conPrecio && precios.size > 1} conSala={conSala} pasada={ahora != null && new Date(pase.fecha_hora) < ahora} />
        ))}
        {ocultas > 0 && (
          <BotonVerMas chip abierto={abierto} onAlternar={() => setAbierto((a) => !a)} texto={`+${ocultas}`} controla={id}
                       etiqueta={abierto ? `Ver menos horas en ${cleanCinemaName(cine)}` : `Ver ${plural(ocultas, "hora", "horas")} más en ${cleanCinemaName(cine)}`} />
        )}
      </div>
    </div>
  );
}

// --- Agrupación de las sesiones de un día en la ficha de película: "Por cine" (por defecto) o "Por hora" ---

const CLAVE_AGRUPACION = "fps24.sesiones.agrupacion";
const oyentes = new Set();
const suscribir = (aviso) => {
  oyentes.add(aviso);
  window.addEventListener("storage", aviso);
  return () => {
    oyentes.delete(aviso);
    window.removeEventListener("storage", aviso);
  };
};
const leerAgrupacion = () => {
  try {
    return localStorage.getItem(CLAVE_AGRUPACION) === "hora" ? "hora" : "cine";
  } catch {
    return "cine"; // localStorage bloqueado (modo privado, permisos)
  }
};

// [modo, cambiar]: recordado en localStorage. En el servidor y en el primer render, "cine" (sin desajuste al hidratar).
export function useAgrupacion() {
  const modo = useSyncExternalStore(suscribir, leerAgrupacion, () => "cine");
  const cambiar = (nuevo) => {
    try {
      localStorage.setItem(CLAVE_AGRUPACION, nuevo);
    } catch {
      // sin localStorage se queda solo en esta visita
    }
    oyentes.forEach((aviso) => aviso());
  };
  return [modo, cambiar];
}

const OPCIONES = [
  { id: "cine", texto: "Por cine" },
  { id: "hora", texto: "Por hora" },
];

// Selector discreto "Por cine | Por hora"
export function SelectorAgrupacion({ modo, onCambiar }) {
  return (
    <div role="radiogroup" aria-label="Agrupar sesiones" className="inline-flex p-0.5 rounded-full bg-surface border border-line text-xs font-semibold">
      {OPCIONES.map((o) => (
        <button key={o.id} type="button" role="radio" aria-checked={modo === o.id} onClick={() => onCambiar(o.id)}
                className={`px-3 py-1 rounded-full transition-colors ${
                  modo === o.id ? "bg-background text-foreground border border-line" : "text-muted hover:text-foreground border border-transparent"}`}>
          {o.texto}
        </button>
      ))}
    </div>
  );
}

// Sesiones de un día. "cine": un bloque por cine, cines por su primera sesión y horas en orden.
// "hora": lista cronológica plana, con el cine en cada fila (sin reordenar por favoritos: manda la hora). contexto: "modal" o "pagina" (límites de LIMITES).
// Lo desplegado se queda abierto mientras la ficha esté montada (también al cambiar de vista y volver).
export function SesionesDia({ pases, modo = "cine", contexto = "modal" }) {
  const { favoritos } = useFavoritos();
  const limite = LIMITES[contexto];
  const [todosCines, setTodosCines] = useState(false);
  const [todasSesiones, setTodasSesiones] = useState(false);
  const id = useId();
  const ordenados = [...pases].sort((a, b) => a.fecha_hora.localeCompare(b.fecha_hora));
  const reemplazar = contexto === "modal";

  if (modo === "hora") {
    const ocultas = ordenados.length - limite.sesiones;
    const visibles = todasSesiones || ocultas <= 0 ? ordenados : ordenados.slice(0, limite.sesiones);
    return (
      <div className="space-y-3">
        <ul id={id} className="space-y-2">
          {visibles.map((pase, i) => (
            <li key={pase.id ?? i} className="flex flex-wrap items-center gap-2">
              <ChipHora pase={pase} cine={pase.cine} conPrecio conSala />
              <EnlaceCine slug={pase.cine_slug} reemplazar={reemplazar}
                          className="text-xs font-bold uppercase tracking-wide text-foreground hover:text-primary hover:underline focus-visible:outline-primary">
                <MarcaFavorito slug={pase.cine_slug} /> {cleanCinemaName(pase.cine)}
              </EnlaceCine>
            </li>
          ))}
        </ul>
        {ocultas > 0 && (
          <BotonVerMas abierto={todasSesiones} onAlternar={() => setTodasSesiones((a) => !a)} controla={id}
                       texto={`Ver ${plural(ocultas, "sesión", "sesiones")} más`} />
        )}
      </div>
    );
  }
  // Map conserva el orden de inserción: cada cine entra con su primera sesión
  const porCine = new Map();
  for (const pase of ordenados) {
    if (!porCine.has(pase.cine)) porCine.set(pase.cine, []);
    porCine.get(pase.cine).push(pase);
  }
  // Mis cines favoritos primero (antes del límite de "Ver más"), cada grupo en su orden
  const cines = favoritosPrimero([...porCine], ([, delCine]) => delCine[0].cine_slug, favoritos);
  const ocultos = cines.length - limite.cines;
  const visibles = todosCines || ocultos <= 0 ? cines : cines.slice(0, limite.cines);
  return (
    <div className="@container space-y-3">
      <div id={id} className={REJILLA_CINES}>
        {visibles.map(([cine, delCine]) => (
          <SesionesCine key={cine} cine={cine} pases={delCine} conPrecio conSala maxHoras={HORAS_POR_CINE} conFavorito reemplazar={reemplazar} />
        ))}
      </div>
      {ocultos > 0 && (
        <BotonVerMas abierto={todosCines} onAlternar={() => setTodosCines((a) => !a)} controla={id}
                     texto={`Ver ${plural(ocultos, "cine", "cines")} más`} />
      )}
    </div>
  );
}

// Resumen plegable de un día de "Otros días" ("Sáb 24 · 12 sesiones"); al abrirlo, sus sesiones con la misma
// agrupación y límites
function DiaPlegable({ clave, pases, modo, contexto }) {
  const [abierto, setAbierto] = useState(false);
  const id = useId();
  return (
    <li>
      <button type="button" onClick={() => setAbierto((a) => !a)} aria-expanded={abierto} aria-controls={id}
              className="w-full flex items-center justify-between gap-3 px-3 py-2 rounded-lg border border-line bg-background text-sm hover:border-primary transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
        <span><span className="font-bold text-foreground">{diaCorto(clave)}</span> <span className="text-muted">· {plural(pases.length, "sesión", "sesiones")}</span></span>
        <svg viewBox="0 0 24 24" className={`w-4 h-4 text-muted transition-transform ${abierto ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {abierto && (
        <div id={id} className="pt-3 pb-1">
          <SesionesDia pases={pases} modo={modo} contexto={contexto} />
        </div>
      )}
    </li>
  );
}

// Sesiones de la ficha desde hoy a las 00:00: el día destacado abierto (el elegido en la portada o, si no hay,
// el primero con sesiones) y debajo "Otros días" plegados, con "Ver más días".
export function SesionesPorDias({ pases, modo, contexto = "modal", diaElegido = null }) {
  const limite = LIMITES[contexto];
  const [todosDias, setTodosDias] = useState(false);
  const id = useId();
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  const porDia = [...pases]
    .filter((p) => new Date(p.fecha_hora) >= hoy)
    .sort((a, b) => a.fecha_hora.localeCompare(b.fecha_hora))
    .reduce((acc, p) => {
      (acc[claveDia(p.fecha_hora)] ||= []).push(p);
      return acc;
    }, {});
  const dias = Object.keys(porDia);
  if (dias.length === 0) return <p className="text-sm text-muted">No hay sesiones programadas próximamente.</p>;

  const destacado = diaElegido ?? dias[0];
  const otros = dias.filter((d) => d !== destacado);
  const ocultos = otros.length - limite.dias;
  const visibles = todosDias || ocultos <= 0 ? otros : otros.slice(0, limite.dias);

  return (
    <div className="space-y-6">
      {porDia[destacado] ? (
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider mb-2 text-primary">{nombreDia(destacado)}</h3>
          <SesionesDia pases={porDia[destacado]} modo={modo} contexto={contexto} />
        </div>
      ) : (
        <p className="text-sm text-muted">No hay sesiones el {nombreDia(destacado).toLowerCase()}.</p>
      )}
      {otros.length > 0 && (
        <div className="pt-4 border-t border-line space-y-3">
          <p className="text-xs font-bold uppercase tracking-wider text-muted">Otros días</p>
          <ul id={id} className="space-y-2">
            {visibles.map((d) => <DiaPlegable key={d} clave={d} pases={porDia[d]} modo={modo} contexto={contexto} />)}
          </ul>
          {ocultos > 0 && (
            <BotonVerMas abierto={todosDias} onAlternar={() => setTodosDias((a) => !a)} controla={id}
                         texto={`Ver ${plural(ocultos, "día", "días")} más`} />
          )}
        </div>
      )}
    </div>
  );
}
