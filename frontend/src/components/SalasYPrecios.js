"use client";

import { useState, useSyncExternalStore } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { LocateFixed, X } from "lucide-react";
import { ChipDato } from "@/components/FichaPelicula";
import { useAuth } from "@/components/AuthProvider";
import BotonFavorito from "@/components/BotonFavorito";
import { useFavoritos } from "@/components/FavoritosProvider";

// Leaflet usa window: solo en cliente
const MapaCines = dynamic(() => import("@/components/MapaCines"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-surface" />,
});

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

// Distancia en línea recta (haversine) en km entre dos { lat, lng }
const distanciaKm = (a, b) => {
  const rad = Math.PI / 180;
  const h = Math.sin(((b.lat - a.lat) * rad) / 2) ** 2
    + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(((b.lng - a.lng) * rad) / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
};
const km = (n) => `${n.toLocaleString("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;
const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// --- Vista en móvil/tablet: "lista" (por defecto) o "mapa", recordada en localStorage (patrón de Sesiones.js) ---
const CLAVE_VISTA = "fps24.cines.vista";
let vistaEnMemoria = "lista";  // si localStorage está bloqueado, dura lo que la visita
const oyentesVista = new Set();
const suscribirVista = (aviso) => {
  oyentesVista.add(aviso);
  window.addEventListener("storage", aviso);
  return () => {
    oyentesVista.delete(aviso);
    window.removeEventListener("storage", aviso);
  };
};
const leerVista = () => {
  try {
    return (localStorage.getItem(CLAVE_VISTA) ?? vistaEnMemoria) === "mapa" ? "mapa" : "lista";
  } catch {
    return vistaEnMemoria;
  }
};
function useVista() {
  const vista = useSyncExternalStore(suscribirVista, leerVista, () => "lista");
  const cambiar = (nueva) => {
    vistaEnMemoria = nueva;
    try {
      localStorage.setItem(CLAVE_VISTA, nueva);
    } catch {
      // se queda en vistaEnMemoria
    }
    oyentesVista.forEach((aviso) => aviso());
  };
  return [vista, cambiar];
}

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

// Botón secundario de la portada ("Salas y precios"); interno: enlace de Next (página de un cine)
const BOTON = "px-3 py-1.5 rounded-full border border-line bg-background text-foreground text-xs font-bold uppercase tracking-wide hover:border-primary hover:text-primary transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";
export function Boton({ href, children, nueva = false, interno = false }) {
  if (interno) return <Link href={href} className={BOTON}>{children}</Link>;
  return (
    <a href={href} {...(nueva ? { target: "_blank", rel: "noopener noreferrer" } : {})} className={BOTON}>
      {children}
    </a>
  );
}

// Precio de hoy destacado: en la tarjeta y en el popup del mapa
export function LineaHoy({ tarifas, hoy }) {
  if (!tarifas) return <p className="text-sm text-muted">Consulta los precios en su web</p>;
  return hoy.tipo === "espectador" ? (
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
  );
}

export function BloquePrecio({ tarifas, hoy }) {
  if (!tarifas) return <LineaHoy tarifas={tarifas} hoy={hoy} />;
  const resumen = [
    tarifas.entrada != null && `Entrada ${euros(tarifas.entrada)}`,
    tarifas.entrada_laboral != null && `Laborable ${euros(tarifas.entrada_laboral)}`,
    tarifas.entrada_finde != null && `Finde ${euros(tarifas.entrada_finde)}`,
    tarifas.dia_espectador && `Espectador (${tarifas.dia_espectador.dias.map((d) => INICIAL[d] || d).join(", ")}) ${euros(tarifas.dia_espectador.precio)}`,
  ].filter(Boolean);

  return (
    <div className="space-y-1.5">
      <LineaHoy tarifas={tarifas} hoy={hoy} />
      {resumen.length > 0 && <p className="text-xs text-foreground">{resumen.join(" · ")}</p>}
      {tarifas.notas && <p className="text-xs text-muted">{tarifas.notas}</p>}
    </div>
  );
}

// activo: resaltada (pin pulsado o ratón/foco encima); onActivar(id | null) avisa al mapa
function TarjetaCine({ cine, hoy, activo, distancia, onActivar }) {
  const telefono = cine.telefono?.replace(/\s+/g, "");
  return (
    <li id={`cine-${cine.id}`} onMouseEnter={() => onActivar(cine.id)} onMouseLeave={() => onActivar(null)}
        onFocus={() => onActivar(cine.id)} onBlur={() => onActivar(null)}
        className={`scroll-mt-4 rounded-3xl border bg-background p-4 flex flex-col gap-3 min-w-0 transition-colors ${
          activo ? "border-primary ring-2 ring-primary" : "border-line"}`}>
      <div className="min-w-0">
        {distancia != null && <p className="mb-1 text-xs font-bold text-primary">a {km(distancia)}</p>}
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-lg font-display font-bold uppercase leading-tight text-foreground">
            <Link href={`/cines/${cine.slug}`} className="hover:text-primary transition-colors rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">{cine.nombre}</Link>
          </h3>
          <BotonFavorito slug={cine.slug} nombre={cine.nombre} className="-mt-1" />
        </div>
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
        <Boton href={`/cines/${cine.slug}`} interno>Ver cartelera →</Boton>
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
  const [activo, setActivo] = useState(null);
  const [vista, setVista] = useVista();
  const { usuario } = useAuth();
  const { favoritos } = useFavoritos();
  const [soloMios, setSoloMios] = useState(false);
  // "Mis cines": con sesión y algún favorito; si se quita el último estando en él, sigue visible con el aviso
  const conMios = Boolean(usuario) && (favoritos.size > 0 || soloMios);
  const mios = conMios && soloMios;
  // Ubicación solo en este navegador: no se envía a ningún servidor
  const [posicion, setPosicion] = useState(null);
  const [geo, setGeo] = useState(null);  // null | "buscando" | mensaje de error

  const buscarme = () => {
    if (!navigator.geolocation) return setGeo("Tu navegador no permite usar la ubicación.");
    setGeo("buscando");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setPosicion({ lat: coords.latitude, lng: coords.longitude });
        setOrden("distancia");
        setGeo(null);
      },
      (err) => setGeo(err.code === err.PERMISSION_DENIED
        ? "Sin permiso de ubicación. Actívalo en tu navegador para ordenar por cercanía."
        : "No se ha podido obtener tu ubicación. Inténtalo de nuevo."),
      { timeout: 10000, maximumAge: 300000 },
    );
  };
  const quitarme = () => {
    setPosicion(null);
    setGeo(null);
    if (orden === "distancia") setOrden("zona");
  };

  // Pin pulsado: resalta su tarjeta y la trae a la vista (si la lista se ve; en móvil con el mapa, basta el popup)
  const pulsarPin = (id) => {
    setActivo(id);
    const tarjeta = document.getElementById(`cine-${id}`);
    if (tarjeta?.offsetParent) tarjeta.scrollIntoView({ behavior: sinMovimiento() ? "auto" : "smooth", block: "center" });
  };

  const conHoy = cines.map((cine) => ({
    cine,
    hoy: precioHoy(cine.tarifas, diaHoy),
    distancia: posicion && cine.lat != null && cine.lng != null ? distanciaKm(posicion, cine) : null,
  }));
  const zonas = [...new Set(cines.map((c) => c.zona).filter(Boolean))];  // ya vienen por zona
  const sesionesHoy = cines.reduce((total, c) => total + c.sesiones_hoy, 0);

  const visibles = conHoy.filter(({ cine, hoy }) =>
    (!mios || favoritos.has(cine.slug))
    && (zona === "todas" || cine.zona === zona)
    && (tipo === "todos" || cine.tipo === tipo)
    && (!soloEspectador || hoy?.tipo === "espectador"));
  if (orden === "precio") {
    // Sin precio de hoy, al final
    visibles.sort((a, b) => (a.hoy?.precio ?? Infinity) - (b.hoy?.precio ?? Infinity) || a.cine.nombre.localeCompare(b.cine.nombre));
  } else if (orden === "distancia") {
    // Sin coordenadas, al final
    visibles.sort((a, b) => (a.distancia ?? Infinity) - (b.distancia ?? Infinity) || a.cine.nombre.localeCompare(b.cine.nombre));
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
        {conMios && (
          <div role="radiogroup" aria-label="Qué cines ver" className="inline-flex p-0.5 rounded-full bg-surface border border-line text-sm font-semibold">
            {[[false, "Todos"], [true, "★ Mis cines"]].map(([valor, texto]) => (
              <button key={texto} type="button" role="radio" aria-checked={mios === valor} onClick={() => setSoloMios(valor)}
                      className={`px-4 py-1.5 rounded-full transition-colors border focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                        mios === valor ? "bg-background text-foreground border-line" : "text-muted hover:text-foreground border-transparent"}`}>
                {texto}
              </button>
            ))}
          </div>
        )}
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
        <div className="flex flex-wrap items-center gap-2">
          <div role="radiogroup" aria-label="Ordenar" className="inline-flex p-0.5 rounded-full bg-surface border border-line text-xs font-semibold">
            {[["zona", "Por zona"], ["precio", "Más baratos hoy"], ...(posicion ? [["distancia", "Más cerca"]] : [])].map(([id, texto]) => (
              <button key={id} type="button" role="radio" aria-checked={orden === id} onClick={() => setOrden(id)}
                      className={`px-3 py-1 rounded-full transition-colors border ${
                        orden === id ? "bg-background text-foreground border-line" : "text-muted hover:text-foreground border-transparent"}`}>
                {texto}
              </button>
            ))}
          </div>
          {posicion ? (
            <button type="button" onClick={quitarme}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border bg-primary text-white border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
              <X className="w-3.5 h-3.5" aria-hidden="true" /> Quitar mi ubicación
            </button>
          ) : (
            <button type="button" onClick={buscarme} disabled={geo === "buscando"}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border bg-background text-foreground border-line hover:border-primary hover:text-primary transition-colors disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
              <LocateFixed className="w-3.5 h-3.5" aria-hidden="true" /> {geo === "buscando" ? "Buscando…" : "Cerca de mí"}
            </button>
          )}
        </div>
        <p role="status" className="text-xs text-muted empty:hidden">{geo && geo !== "buscando" ? geo : ""}</p>
      </div>

      {/* Móvil/tablet: lista o mapa; escritorio: los dos */}
      <div role="radiogroup" aria-label="Vista" className="lg:hidden flex w-fit mx-auto mb-6 p-0.5 rounded-full bg-surface border border-line text-sm font-semibold">
        {[["lista", "Lista"], ["mapa", "Mapa"]].map(([id, texto]) => (
          <button key={id} type="button" role="radio" aria-checked={vista === id} onClick={() => setVista(id)}
                  className={`px-5 py-1.5 rounded-full transition-colors border ${
                    vista === id ? "bg-background text-foreground border-line" : "text-muted hover:text-foreground border-transparent"}`}>
            {texto}
          </button>
        ))}
      </div>

      <div className="lg:grid lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-6 lg:items-start">
        <div className={`${vista === "mapa" ? "block" : "hidden"} lg:block lg:sticky lg:top-4 h-[70vh] lg:h-[calc(100vh-2rem)] rounded-3xl overflow-hidden border border-line isolate`}>
          <MapaCines items={visibles} todos={visibles.length === cines.length} activo={activo} onPin={pulsarPin} posicion={posicion}
                     popup={({ cine, hoy }) => (
                       <div className="space-y-2 min-w-48 [&_p]:m-0">
                         <div>
                           <p className="font-display font-bold uppercase text-sm leading-tight text-foreground">{cine.nombre}</p>
                           <p className="text-xs text-muted">{[cine.zona, { autor: "Autor", comercial: "Comercial" }[cine.tipo]].filter(Boolean).join(" · ")}</p>
                         </div>
                         <p className="text-sm text-foreground"><span className="font-bold">Hoy:</span> {plural(cine.sesiones_hoy, "sesión", "sesiones")}</p>
                         <LineaHoy tarifas={cine.tarifas} hoy={hoy} />
                         <div className="flex flex-wrap gap-2">
                           <Boton href={`/cines/${cine.slug}`} interno>Ver cartelera →</Boton>
                           <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}`} nueva>Cómo llegar</Boton>
                           {cine.web && <Boton href={cine.web} nueva>Web</Boton>}
                         </div>
                       </div>
                     )} />
        </div>

        <div className={`${vista === "lista" ? "block" : "hidden"} lg:block`}>
          {visibles.length === 0 ? (
            <p className="text-center text-muted py-12 px-4 rounded-3xl border border-dashed border-line bg-surface">
              {mios && favoritos.size === 0 ? "Aún no tienes cines favoritos. Pulsa la ★ en un cine para añadirlo." : "Ningún cine cumple esos filtros."}
            </p>
          ) : (
            <div className="space-y-10">
              {grupos.map(([nombre, lista]) => (
                <section key={nombre || "todos"} aria-label={nombre || "Cines"}>
                  {nombre && <h2 className="text-lg md:text-xl font-display font-bold text-foreground mb-3">{nombre}</h2>}
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {lista.map(({ cine, hoy, distancia }) => (
                      <TarjetaCine key={cine.id} cine={cine} hoy={hoy} distancia={distancia} activo={activo === cine.id} onActivar={setActivo} />
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
