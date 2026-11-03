"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { Map as IconoMapa } from "lucide-react";
import { ChipDato } from "@/components/FichaPelicula";
import { useAuth } from "@/components/AuthProvider";
import BotonFavorito from "@/components/BotonFavorito";
import { useFavoritos } from "@/components/FavoritosProvider";
import PasesCerca from "@/components/PasesCerca";
import { ahoraMadrid, buscarCerca, centroZona, cinesConPronto, distanciaKm, textoDistancia } from "@/lib/cercaDeTi";
import { comoUTC } from "@/lib/fechasMadrid";
import { ETIQUETA_TIPO as ETIQUETA_HOY, euros, precioHoy, reglasEspectador } from "@/lib/tarifas";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Leaflet usa window: solo en cliente
const MapaCines = dynamic(() => import("@/components/MapaCines"), {
  ssr: false,
  loading: () => <div className="h-full w-full bg-surface" />,
});

const INICIAL = { Lunes: "L", Martes: "M", Miércoles: "X", Jueves: "J", Viernes: "V", Sábado: "S", Domingo: "D" };

const plural = (n, una, varias) => `${n} ${n === 1 ? una : varias}`;

const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Estilo de los chips de la portada: activo en violeta (o verde para el día del espectador)
export function ChipFiltro({ activo, onClick, verde = false, children }) {
  const encendido = verde ? "bg-accent text-foreground border-accent" : "bg-primary text-white border-primary";
  return (
    <button type="button" aria-pressed={activo} onClick={onClick}
            className={`px-3 py-1.5 rounded-full text-xs font-bold border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
              activo ? encendido : "bg-background text-foreground border-line hover:border-primary hover:text-primary"}`}>
      {children}
    </button>
  );
}

// Botón secundario de "Cines de Madrid" (/cines); interno: enlace de Next (página de un cine)
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
    <p className="px-3 py-2 rounded-lg bg-surface border border-line text-sm font-bold text-foreground">{tarifas.precio_texto ?? "Precio según sala"}</p>
  );
}

export function BloquePrecio({ tarifas, hoy }) {
  if (!tarifas) return <LineaHoy tarifas={tarifas} hoy={hoy} />;
  const resumen = [
    tarifas.entrada != null && `Entrada ${euros(tarifas.entrada)}`,
    tarifas.entrada_laboral != null && `Laborable ${euros(tarifas.entrada_laboral)}`,
    tarifas.entrada_finde != null && `Finde ${euros(tarifas.entrada_finde)}`,
    ...reglasEspectador(tarifas).map((r) => `Espectador (${r.dias.map((d) => INICIAL[d] || d).join(", ")}) ${euros(r.precio)}`),
  ].filter(Boolean);

  return (
    <div className="space-y-1.5">
      <LineaHoy tarifas={tarifas} hoy={hoy} />
      {resumen.length > 0 && <p className="text-xs text-foreground">{resumen.join(" · ")}</p>}
      {tarifas.notas && <p className="text-xs text-muted">{tarifas.notas}</p>}
    </div>
  );
}

// activo: resaltada (pin pulsado o ratón/foco encima); onActivar(id | null) avisa al mapa; onCentrar: centra el
// mapa en su pin (al pulsar la tarjeta fuera de sus enlaces, o "Ver en el mapa"); pronto: sesión en la próxima hora
function TarjetaCine({ cine, hoy, activo, distancia, pronto, onActivar, onCentrar }) {
  const telefono = cine.telefono?.replace(/\s+/g, "");
  const conPunto = cine.lat != null && cine.lng != null;
  return (
    <li id={`cine-${cine.id}`} onMouseEnter={() => onActivar(cine.id)} onMouseLeave={() => onActivar(null)}
        onFocus={() => onActivar(cine.id)} onBlur={() => onActivar(null)}
        onClick={(e) => conPunto && !e.target.closest("a, button") && onCentrar(cine.id)}
        className={`scroll-mt-4 rounded-3xl border bg-background p-4 flex flex-col gap-3 min-w-0 transition-colors ${
          activo ? "border-primary ring-2 ring-primary" : "border-line"}`}>
      <div className="min-w-0">
        {distancia != null && <p className="mb-1 text-xs font-bold text-primary">a {textoDistancia(distancia)}</p>}
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
      {pronto && (
        <p className="flex items-center gap-1.5 text-xs font-bold text-primary">
          <span aria-hidden="true" className="w-2 h-2 rounded-full bg-primary" /> Empieza alguna sesión en la próxima hora
        </p>
      )}

      <BloquePrecio tarifas={cine.tarifas} hoy={hoy} />

      <div className="mt-auto pt-1 flex flex-wrap gap-2">
        <Boton href={`/cines/${cine.slug}`} interno>Ver cartelera →</Boton>
        {cine.web && <Boton href={cine.web} nueva>Web</Boton>}
        {conPunto && (
          <>
            <button type="button" onClick={() => onCentrar(cine.id)} className={`${BOTON} inline-flex items-center gap-1.5`}>
              <IconoMapa className="w-3.5 h-3.5" aria-hidden="true" /> Ver en el mapa
            </button>
            <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}`} nueva>Cómo llegar</Boton>
          </>
        )}
        {telefono && <Boton href={`tel:+34${telefono}`}>{cine.telefono}</Boton>}
      </div>
    </li>
  );
}

// Pases que quedan hasta mañana a esta hora: /pases trae varias semanas y aquí solo hacen falta los próximos
const HORIZONTE_MS = 30 * 3600 * 1000;

// Página "Cines de Madrid" (/cines): pases cerca de ti, mapa y lista de cines con filtros (zona, tipo, día del espectador
// hoy) y orden (por zona, más baratos hoy o más cerca)
export default function SalasYPrecios({ cines, fechaHoy }) {
  const [zona, setZona] = useState("todas");
  const [tipo, setTipo] = useState("todos");
  const [soloEspectador, setSoloEspectador] = useState(false);
  const [orden, setOrden] = useState("zona");
  const [activo, setActivo] = useState(null);
  const [centrar, setCentrar] = useState(null);  // { id, n }: ver MapaCines
  const { usuario } = useAuth();
  const { favoritos } = useFavoritos();
  const [soloMios, setSoloMios] = useState(false);
  // "Mis cines": con sesión y algún favorito; si se quita el último estando en él, sigue visible con el aviso
  const conMios = Boolean(usuario) && (favoritos.size > 0 || soloMios);
  const mios = conMios && soloMios;
  // Posición { lat, lng, origen: "gps" | "zona" | "mapa" } solo en este navegador: no se envía a ningún servidor
  const [posicion, setPosicion] = useState(null);
  const [geo, setGeo] = useState(null);  // null | "pidiendo" | "concedido" | "denegado" | "no-disponible" | "tiempo"
  const [zonaCerca, setZonaCerca] = useState("");
  const [colocando, setColocando] = useState(false);
  const [filtro, setFiltro] = useState({ radioKm: 1, ventana: "1h" });
  const mapa = useRef(null);

  // Sesiones próximas (para los pines, el popup y los pases cerca) y "ahora" en Madrid, al minuto. Solo tras
  // montar: el HTML del servidor no depende de la hora (sin desajustes al hidratar).
  const [pases, setPases] = useState(null);  // null: cargando; "error"; o la lista
  const [ahora, setAhora] = useState(null);
  useEffect(() => {
    let vivo = true;
    fetch(`${API_URL}/pases`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data) => {
        if (!vivo) return;
        const ya = ahoraMadrid();
        setAhora(ya);
        setPases(data.filter((p) => {
          const t = comoUTC(p.fecha_hora).getTime();
          return t >= ya && t <= ya + HORIZONTE_MS;
        }));
      })
      .catch((err) => {
        console.error("Error loading sessions:", err);
        if (vivo) setPases("error");
      });
    const reloj = setInterval(() => setAhora(ahoraMadrid()), 60000);
    return () => {
      vivo = false;
      clearInterval(reloj);
    };
  }, []);
  const conPases = Array.isArray(pases) && ahora != null;
  const pronto = conPases ? cinesConPronto(pases, ahora) : undefined;
  const cinesPorSlug = new Map(cines.map((c) => [c.slug, c]));
  const resultado = posicion && conPases ? buscarCerca(pases, cinesPorSlug, posicion, ahora, filtro) : null;
  const proximas = (slug) => (conPases ? pases.filter((p) => p.cine_slug === slug && comoUTC(p.fecha_hora).getTime() >= ahora).slice(0, 3) : []);

  const elegir = (punto) => {
    setPosicion(punto);
    setOrden("distancia");
    setColocando(false);
  };
  const quitar = () => {
    setPosicion(null);
    setGeo(null);
    setZonaCerca("");
    if (orden === "distancia") setOrden("zona");
  };
  const usarUbicacion = () => {
    if (!navigator.geolocation) return setGeo("no-disponible");
    setGeo("pidiendo");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setZonaCerca("");
        elegir({ lat: coords.latitude, lng: coords.longitude, origen: "gps" });
        setGeo("concedido");
      },
      (err) => setGeo({ [err.PERMISSION_DENIED]: "denegado", [err.TIMEOUT]: "tiempo" }[err.code] ?? "no-disponible"),
      { timeout: 10000, maximumAge: 300000 },
    );
  };
  const elegirZona = (z) => {
    const centro = z && centroZona(cines, z);
    if (!centro) return quitar();
    setZonaCerca(z);
    setGeo(null);
    elegir({ ...centro, origen: "zona" });
  };
  const alternarColocar = () => {
    setColocando(!colocando);
    if (!colocando) mapa.current?.scrollIntoView({ behavior: sinMovimiento() ? "auto" : "smooth", block: "nearest" });
  };
  const colocar = (punto) => {
    setZonaCerca("");
    setGeo(null);
    elegir({ ...punto, origen: "mapa" });
  };

  // Pin pulsado: resalta su tarjeta y la trae a la vista (el popup ya muestra el resumen)
  const pulsarPin = (id) => {
    setActivo(id);
    document.getElementById(`cine-${id}`)?.scrollIntoView({ behavior: sinMovimiento() ? "auto" : "smooth", block: "nearest" });
  };
  // Tarjeta pulsada: centra el mapa en su pin (y lo trae a la vista si no se ve)
  const centrarEn = (id) => {
    setActivo(id);
    setCentrar((c) => ({ id, n: (c?.n ?? 0) + 1 }));
    mapa.current?.scrollIntoView({ behavior: sinMovimiento() ? "auto" : "smooth", block: "nearest" });
  };

  const conHoy = cines.map((cine) => ({
    cine,
    hoy: precioHoy(cine.tarifas, fechaHoy),
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

      <PasesCerca posicion={posicion} geo={geo} onUbicacion={usarUbicacion} onQuitar={quitar}
                  zonas={zonas} zona={zonaCerca} onZona={elegirZona} colocando={colocando} onColocar={alternarColocar}
                  filtro={filtro} onFiltro={setFiltro} resultado={resultado}
                  estadoPases={pases === "error" ? "error" : conPases ? "listo" : "cargando"} />

      {/* Mapa a lo ancho y la lista debajo, con la misma información (el mapa no es la única vía) */}
      <div ref={mapa} className={`scroll-mt-4 h-[60vh] lg:h-[min(70vh,640px)] rounded-3xl overflow-hidden border isolate ${
        colocando ? "border-primary ring-2 ring-primary [&_.leaflet-container]:cursor-crosshair" : "border-line"}`}>
        <MapaCines items={visibles} todos={visibles.length === cines.length} activo={activo} onPin={pulsarPin} posicion={posicion}
                   pronto={pronto} favoritos={favoritos} centrar={centrar} onColocar={colocando ? colocar : null}
                   popup={({ cine }) => (
                     <div className="space-y-2 min-w-48 [&_p]:m-0">
                       <div>
                         <p className="font-display font-bold uppercase text-sm leading-tight text-foreground">
                           {favoritos.has(cine.slug) && <span aria-label="Favorito">★ </span>}{cine.nombre}
                         </p>
                         {cine.zona && <p className="text-xs text-muted">{cine.zona}</p>}
                       </div>
                       {conPases ? (
                         proximas(cine.slug).length > 0 ? (
                           <ul className="space-y-0.5 text-xs text-foreground" aria-label="Próximas sesiones">
                             {proximas(cine.slug).map((p) => (
                               <li key={p.id}><span className="font-bold">{p.fecha_hora.slice(11, 16)}</span> {p.pelicula?.titulo}{p.idioma === "VOSE" ? " (VOSE)" : ""}</li>
                             ))}
                           </ul>
                         ) : <p className="text-xs text-muted">No quedan sesiones hasta mañana</p>
                       ) : (
                         <p className="text-sm text-foreground"><span className="font-bold">Hoy:</span> {plural(cine.sesiones_hoy, "sesión", "sesiones")}</p>
                       )}
                       <div className="flex flex-wrap gap-2">
                         <Boton href={`/cines/${cine.slug}`} interno>Ver cartelera →</Boton>
                         <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}`} nueva>Cómo llegar</Boton>
                       </div>
                     </div>
                   )} />
      </div>
      <ul aria-label="Leyenda del mapa" className="mt-2 mb-8 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <li className="flex items-center gap-1.5"><span aria-hidden="true" className="w-3 h-3 rounded-full bg-primary" /> Empieza alguna sesión en la próxima hora</li>
        <li className="flex items-center gap-1.5"><span aria-hidden="true" className="w-3 h-3 rounded-sm bg-muted" /> Nada en la próxima hora</li>
        <li className="flex items-center gap-1.5"><span aria-hidden="true" className="px-0.5 rounded-full bg-accent text-foreground leading-none">★</span> Favorito</li>
        <li>El número: sesiones que quedan hoy</li>
      </ul>

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
        <div role="radiogroup" aria-label="Ordenar" className="inline-flex p-0.5 rounded-full bg-surface border border-line text-xs font-semibold">
          {[["zona", "Por zona"], ["precio", "Más baratos hoy"], ...(posicion ? [["distancia", "Más cerca"]] : [])].map(([id, texto]) => (
            <button key={id} type="button" role="radio" aria-checked={orden === id} onClick={() => setOrden(id)}
                    className={`px-3 py-1 rounded-full transition-colors border ${
                      orden === id ? "bg-background text-foreground border-line" : "text-muted hover:text-foreground border-transparent"}`}>
              {texto}
            </button>
          ))}
        </div>
      </div>

      {visibles.length === 0 ? (
        <p className="text-center text-muted py-12 px-4 rounded-3xl border border-dashed border-line bg-surface">
          {mios && favoritos.size === 0 ? "Aún no tienes cines favoritos. Pulsa la ★ en un cine para añadirlo." : "Ningún cine cumple esos filtros."}
        </p>
      ) : (
        <div className="space-y-10">
          {grupos.map(([nombre, lista]) => (
            <section key={nombre || "todos"} aria-label={nombre || "Cines"}>
              {nombre && <h2 className="text-lg md:text-xl font-display font-bold text-foreground mb-3">{nombre}</h2>}
              <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {lista.map(({ cine, hoy, distancia }) => (
                  <TarjetaCine key={cine.id} cine={cine} hoy={hoy} distancia={distancia} pronto={Boolean(pronto?.has(cine.slug))}
                               activo={activo === cine.id} onActivar={setActivo} onCentrar={centrarEn} />
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
