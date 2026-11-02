"use client";

import Link from "next/link";
import { LocateFixed, MapPin, X } from "lucide-react";
import { Boton, ChipFiltro } from "@/components/SalasYPrecios";
import { Version } from "@/components/ModalSesion";
import { useSesionesGuardadas } from "@/components/SesionesGuardadasProvider";
import { minutosAndando, textoDistancia } from "@/lib/cercaDeTi";
import { cleanCinemaName } from "@/utils/helpers";

export const RADIOS = [[0.5, "500 m"], [1, "1 km"], [2, "2 km"]];
export const VENTANAS = [["1h", "1 h"], ["2h", "2 h"], ["noche", "Esta noche"]];
const TEXTO_VENTANA = { "1h": "la próxima hora", "2h": "las próximas 2 horas", noche: "lo que queda de noche" };
const textoRadio = (km) => RADIOS.find(([r]) => r === km)?.[1] ?? textoDistancia(km);

// Estado de la geolocalización -> mensaje (pidiendo, concedido, denegado, no disponible, tiempo agotado)
const MENSAJE_GEO = {
  pidiendo: "Pidiendo tu ubicación…",
  concedido: "Usamos tu ubicación solo en este navegador: no se envía a ningún servidor.",
  denegado: "Sin permiso de ubicación. Puedes activarlo en tu navegador, o elegir una zona o un punto en el mapa.",
  "no-disponible": "No podemos obtener tu ubicación en este dispositivo. Elige una zona o un punto en el mapa.",
  tiempo: "Ha tardado demasiado en llegar tu ubicación. Vuelve a intentarlo o elige una zona.",
};

const empiezaEn = (min) => min < 1 ? "Empieza ahora"
  : min < 60 ? `Empieza en ${min} min` : `Empieza en ${Math.floor(min / 60)} h${min % 60 ? ` ${min % 60} min` : ""}`;

function TarjetaPase({ pase, cine, distancia, minutos }) {
  const { abrir } = useSesionesGuardadas();
  const { pelicula = {} } = pase;
  const hora = pase.fecha_hora.slice(11, 16);
  const nombreCine = cleanCinemaName(pase.cine);
  return (
    <li className="flex gap-3 rounded-2xl border border-line bg-background p-3 min-w-0">
      <div className="w-16 aspect-[2/3] shrink-0 rounded-lg overflow-hidden border border-line bg-surface">
        {pelicula.poster_url && <img src={pelicula.poster_url} alt="" className="w-full h-full object-cover" />}
      </div>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-xs font-bold text-primary">{empiezaEn(minutos)} · <time dateTime={pase.fecha_hora}>{hora}</time></p>
        <h3 className="font-display font-bold uppercase leading-tight text-foreground break-words">
          {pelicula.id ? <Link href={`/pelicula/${pelicula.id}`} className="hover:text-primary rounded focus-visible:outline-2 focus-visible:outline-primary">{pelicula.titulo}</Link> : pelicula.titulo}
        </h3>
        <p className="text-sm font-semibold break-words">
          <Link href={`/cines/${pase.cine_slug}`} className="hover:text-primary hover:underline rounded focus-visible:outline-2 focus-visible:outline-primary">{nombreCine}</Link>
        </p>
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted">
          <span>{textoDistancia(distancia)} · ~{minutosAndando(distancia)} min andando</span>
          <Version idioma={pase.idioma} />
        </p>
        <div className="pt-1 flex flex-wrap gap-2">
          <button type="button" aria-haspopup="dialog" onClick={(e) => abrir(pase, e.currentTarget)}
                  aria-label={`Ver sesión: ${pelicula.titulo}, ${hora} en ${nombreCine}`}
                  className="px-3 py-1.5 rounded-full border border-primary bg-primary text-white text-xs font-bold uppercase tracking-wide hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
            Ver sesión
          </button>
          <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}&travelmode=walking`} nueva>Cómo llegar</Boton>
        </div>
      </div>
    </li>
  );
}

// "Encuentra pases cerca de ti": elegir el punto (ubicación, zona o mapa), radio y ventana, y las sesiones.
// Todo en el cliente: la posición vive en el estado de SalasYPrecios y no sale del navegador.
export default function PasesCerca({
  posicion, geo, onUbicacion, onQuitar, zonas, zona, onZona, colocando, onColocar,
  filtro, onFiltro, resultado, estadoPases,
}) {
  const sinPermiso = geo && geo !== "pidiendo" && geo !== "concedido";
  return (
    <section aria-labelledby="titulo-cerca" className="mb-8 rounded-3xl border border-line bg-surface p-4 md:p-6 space-y-4">
      <h2 id="titulo-cerca" className="text-xl md:text-2xl font-display font-bold uppercase text-foreground">
        Encuentra pases <span className="text-primary">cerca de ti</span>
      </h2>

      <div className="flex flex-wrap items-center gap-2">
        {posicion ? (
          <button type="button" onClick={onQuitar}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border bg-primary text-white border-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
            <X className="w-3.5 h-3.5" aria-hidden="true" /> Quitar {posicion.origen === "gps" ? "mi ubicación" : "el punto"}
          </button>
        ) : (
          <button type="button" onClick={onUbicacion} disabled={geo === "pidiendo"}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border bg-background text-foreground border-line hover:border-primary hover:text-primary transition-colors disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
            <LocateFixed className="w-3.5 h-3.5" aria-hidden="true" /> {geo === "pidiendo" ? "Pidiendo…" : "Usar mi ubicación"}
          </button>
        )}
        <label className="inline-flex items-center gap-1.5 text-xs font-bold text-foreground">
          <span>{sinPermiso || !posicion ? "o elige una zona" : "Zona"}</span>
          <select value={zona} onChange={(e) => onZona(e.target.value)}
                  className="max-w-40 px-2 py-1.5 rounded-full border border-line bg-background text-foreground text-xs font-bold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
            <option value="">—</option>
            {zonas.map((z) => <option key={z} value={z}>{z}</option>)}
          </select>
        </label>
        <button type="button" aria-pressed={colocando} onClick={onColocar}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
                  colocando ? "bg-primary text-white border-primary" : "bg-background text-foreground border-line hover:border-primary hover:text-primary"}`}>
          <MapPin className="w-3.5 h-3.5" aria-hidden="true" /> {colocando ? "Pulsa en el mapa…" : "Elegir un punto en el mapa"}
        </button>
      </div>
      <p role="status" className="text-xs text-muted empty:hidden">{geo ? MENSAJE_GEO[geo] : ""}</p>

      {posicion && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex flex-wrap gap-2" role="group" aria-label="Distancia máxima">
              {RADIOS.map(([km, texto]) => (
                <ChipFiltro key={km} activo={filtro.radioKm === km} onClick={() => onFiltro({ ...filtro, radioKm: km })}>{texto}</ChipFiltro>
              ))}
            </div>
            <div className="flex flex-wrap gap-2" role="group" aria-label="Cuándo empieza">
              {VENTANAS.map(([id, texto]) => (
                <ChipFiltro key={id} activo={filtro.ventana === id} onClick={() => onFiltro({ ...filtro, ventana: id })}>{texto}</ChipFiltro>
              ))}
            </div>
          </div>

          <div aria-live="polite">
            {estadoPases === "cargando" ? (
              <p className="text-sm text-muted">Cargando sesiones…</p>
            ) : estadoPases === "error" ? (
              <p className="text-sm text-muted">No se han podido cargar las sesiones. Vuelve a intentarlo en unos minutos.</p>
            ) : (
              <>
                {resultado.ampliado && resultado.items.length > 0 && (
                  <p className="mb-3 px-3 py-2 rounded-lg bg-primary-soft border border-primary text-sm text-foreground">
                    No hay nada a menos de {textoRadio(filtro.radioKm)} en {TEXTO_VENTANA[filtro.ventana]}: te enseñamos lo que hay
                    a menos de {textoRadio(resultado.ampliado.radioKm)} en {TEXTO_VENTANA[resultado.ampliado.ventana]}.
                  </p>
                )}
                {resultado.items.length > 0 ? (
                  <ul className="grid grid-cols-1 md:grid-cols-2 gap-3" aria-label="Sesiones cerca">
                    {resultado.items.map((item) => <TarjetaPase key={item.pase.id} {...item} />)}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">
                    No hay sesiones a menos de {textoRadio((resultado.ampliado ?? filtro).radioKm)} en{" "}
                    {TEXTO_VENTANA[(resultado.ampliado ?? filtro).ventana]}.{" "}
                    {filtro.ventana !== "noche" && <>Prueba con «Esta noche», </>}elige otra zona o mira{" "}
                    <Link href="/" className="text-primary font-bold hover:underline">toda la cartelera</Link>.
                  </p>
                )}
              </>
            )}
          </div>
        </>
      )}
    </section>
  );
}
