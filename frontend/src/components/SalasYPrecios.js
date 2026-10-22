"use client";

import { useState } from "react";
import { ChipDato } from "@/components/FichaPelicula";

const FINDE = ["Sábado", "Domingo"];
const INICIAL = { Lunes: "L", Martes: "M", Miércoles: "X", Jueves: "J", Viernes: "V", Sábado: "S", Domingo: "D" };

const euros = (n) => n.toLocaleString("es-ES", { style: "currency", currency: "EUR" });
const plural = (n, una, varias) => `${n} ${n === 1 ? una : varias}`;

// Precio de una entrada HOY según cine.tarifas: { precio, tipo } con tipo "espectador", "finde", "laboral" o
// "entrada"; precio null si hay tarifas pero no un precio único (p. ej. según sala); null sin tarifas.
export const precioHoy = (tarifas, dia) => {
  if (!tarifas) return null;
  const espectador = tarifas.dia_espectador;
  if (espectador?.dias?.includes(dia)) return { precio: espectador.precio, tipo: "espectador" };
  if (FINDE.includes(dia) && tarifas.entrada_finde != null) return { precio: tarifas.entrada_finde, tipo: "finde" };
  if (!FINDE.includes(dia) && tarifas.entrada_laboral != null) return { precio: tarifas.entrada_laboral, tipo: "laboral" };
  const precio = tarifas.entrada ?? tarifas.entrada_laboral ?? tarifas.entrada_finde ?? null;
  return { precio, tipo: "entrada" };
};

const ETIQUETA_HOY = { finde: "fin de semana", laboral: "día laborable", entrada: "entrada" };

// Estilo de los chips de la portada: activo en violeta (o verde para el día del espectador)
function ChipFiltro({ activo, onClick, verde = false, children }) {
  const encendido = verde ? "bg-accent text-foreground border-accent" : "bg-primary text-white border-primary";
  return (
    <button type="button" aria-pressed={activo} onClick={onClick}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
              activo ? encendido : "bg-background text-foreground border-line hover:border-primary hover:text-primary"}`}>
      {children}
    </button>
  );
}

// Botón secundario de la portada ("Salas y precios")
function Boton({ href, children, nueva = false }) {
  return (
    <a href={href} {...(nueva ? { target: "_blank", rel: "noopener noreferrer" } : {})}
       className="px-3 py-1.5 rounded-full border border-line bg-background text-foreground text-xs font-bold uppercase tracking-wide hover:border-primary hover:text-primary transition-colors">
      {children}
    </a>
  );
}

function BloquePrecio({ tarifas, hoy }) {
  if (!tarifas) return <p className="text-sm text-muted">Consulta los precios en su web</p>;
  const resumen = [
    tarifas.entrada != null && `Entrada ${euros(tarifas.entrada)}`,
    tarifas.entrada_laboral != null && `Laborable ${euros(tarifas.entrada_laboral)}`,
    tarifas.entrada_finde != null && `Finde ${euros(tarifas.entrada_finde)}`,
    tarifas.dia_espectador && `Espectador (${tarifas.dia_espectador.dias.map((d) => INICIAL[d] || d).join(", ")}) ${euros(tarifas.dia_espectador.precio)}`,
  ].filter(Boolean);

  return (
    <div className="space-y-1.5">
      {hoy.tipo === "espectador" ? (
        <p className="px-3 py-2 rounded-lg bg-accent border border-accent text-sm font-bold text-foreground">
          Hoy día del espectador · {euros(hoy.precio)}
        </p>
      ) : hoy.precio != null ? (
        <p className="px-3 py-2 rounded-lg bg-surface border border-line text-sm">
          <span className="font-bold text-foreground">Hoy {euros(hoy.precio)}</span>
          <span className="text-muted"> · {ETIQUETA_HOY[hoy.tipo]}</span>
        </p>
      ) : (
        <p className="px-3 py-2 rounded-lg bg-surface border border-line text-sm font-bold text-foreground">Precio según sala</p>
      )}
      {resumen.length > 0 && <p className="text-xs text-foreground">{resumen.join(" · ")}</p>}
      {tarifas.notas && <p className="text-xs text-muted">{tarifas.notas}</p>}
    </div>
  );
}

function TarjetaCine({ cine, hoy }) {
  const telefono = cine.telefono?.replace(/\s+/g, "");
  return (
    <li className="rounded-3xl border border-line bg-background p-4 flex flex-col gap-3 min-w-0">
      <div className="min-w-0">
        <h3 className="text-lg font-display font-bold uppercase leading-tight text-foreground">{cine.nombre}</h3>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          {cine.zona && <ChipDato>{cine.zona}</ChipDato>}
          {cine.tipo === "autor" && (
            <span className="text-xs px-2 py-0.5 rounded-md border bg-primary-soft text-primary border-primary">Autor</span>
          )}
          {cine.tipo === "comercial" && <ChipDato>Comercial</ChipDato>}
        </div>
        {cine.direccion && <p className="mt-2 text-xs text-muted">{cine.direccion}</p>}
      </div>

      <p className="text-sm text-foreground">
        {cine.sesiones_hoy > 0 ? (
          <><span className="font-bold">Hoy:</span> {plural(cine.sesiones_hoy, "sesión", "sesiones")} · {plural(cine.peliculas_hoy, "película", "películas")}</>
        ) : (
          <span className="text-muted">Hoy ya no quedan sesiones</span>
        )}
      </p>

      <BloquePrecio tarifas={cine.tarifas} hoy={hoy} />

      <div className="mt-auto pt-1 flex flex-wrap gap-2">
        {cine.web && <Boton href={cine.web} nueva>Web</Boton>}
        {cine.lat != null && cine.lng != null && (
          <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}`} nueva>Cómo llegar</Boton>
        )}
        {telefono && <Boton href={`tel:+34${telefono}`}>{cine.telefono}</Boton>}
      </div>
    </li>
  );
}

// Página "Salas y precios": filtros (zona, tipo, día del espectador hoy) y orden (por zona o más baratos hoy)
export default function SalasYPrecios({ cines, diaHoy }) {
  const [zona, setZona] = useState("todas");
  const [tipo, setTipo] = useState("todos");
  const [soloEspectador, setSoloEspectador] = useState(false);
  const [orden, setOrden] = useState("zona");

  const conHoy = cines.map((cine) => ({ cine, hoy: precioHoy(cine.tarifas, diaHoy) }));
  const zonas = [...new Set(cines.map((c) => c.zona).filter(Boolean))];  // ya vienen por zona
  const sesionesHoy = cines.reduce((total, c) => total + c.sesiones_hoy, 0);

  const visibles = conHoy.filter(({ cine, hoy }) =>
    (zona === "todas" || cine.zona === zona)
    && (tipo === "todos" || cine.tipo === tipo)
    && (!soloEspectador || hoy?.tipo === "espectador"));
  if (orden === "precio") {
    // Sin precio de hoy, al final
    visibles.sort((a, b) => (a.hoy?.precio ?? Infinity) - (b.hoy?.precio ?? Infinity) || a.cine.nombre.localeCompare(b.cine.nombre));
  }
  // Por zona: el orden de la API (zona y nombre), en grupos
  const grupos = orden === "zona"
    ? zonas.map((z) => [z, visibles.filter(({ cine }) => cine.zona === z)]).concat([["Sin zona", visibles.filter(({ cine }) => !cine.zona)]])
        .filter(([, lista]) => lista.length > 0)
    : [[null, visibles]];

  return (
    <div>
      <p className="text-center text-sm font-semibold text-muted mb-6">
        {plural(cines.length, "cine", "cines")} · {sesionesHoy > 0 ? `hoy ${plural(sesionesHoy, "sesión", "sesiones")}` : "hoy ya no quedan sesiones"}
      </p>

      {/* Filtros y orden */}
      <div className="space-y-3 mb-8">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Zona">
          <ChipFiltro activo={zona === "todas"} onClick={() => setZona("todas")}>Todas</ChipFiltro>
          {zonas.map((z) => <ChipFiltro key={z} activo={zona === z} onClick={() => setZona(z)}>{z}</ChipFiltro>)}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Tipo de cine">
            <ChipFiltro activo={tipo === "todos"} onClick={() => setTipo("todos")}>Todos</ChipFiltro>
            <ChipFiltro activo={tipo === "autor"} onClick={() => setTipo("autor")}>Autor</ChipFiltro>
            <ChipFiltro activo={tipo === "comercial"} onClick={() => setTipo("comercial")}>Comercial</ChipFiltro>
          </div>
          <ChipFiltro verde activo={soloEspectador} onClick={() => setSoloEspectador((v) => !v)}>Día del espectador hoy</ChipFiltro>
        </div>
        <div role="radiogroup" aria-label="Ordenar" className="inline-flex p-0.5 rounded-full bg-surface border border-line text-xs font-semibold">
          {[["zona", "Por zona"], ["precio", "Más baratos hoy"]].map(([id, texto]) => (
            <button key={id} type="button" role="radio" aria-checked={orden === id} onClick={() => setOrden(id)}
                    className={`px-3 py-1 rounded-full transition-colors border ${
                      orden === id ? "bg-background text-foreground border-line" : "text-muted hover:text-foreground border-transparent"}`}>
              {texto}
            </button>
          ))}
        </div>
      </div>

      {visibles.length === 0 ? (
        <p className="text-center text-muted py-12 rounded-3xl border border-dashed border-line bg-surface">Ningún cine cumple esos filtros.</p>
      ) : (
        <div className="space-y-10">
          {grupos.map(([nombre, lista]) => (
            <section key={nombre || "todos"} aria-label={nombre || "Cines"}>
              {nombre && <h2 className="text-lg md:text-xl font-display font-bold text-foreground mb-3">{nombre}</h2>}
              <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {lista.map(({ cine, hoy }) => <TarjetaCine key={cine.id} cine={cine} hoy={hoy} />)}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
