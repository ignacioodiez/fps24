"use client";

// Mapa de "Salas y precios" (Leaflet). Solo en cliente: se carga con next/dynamic y ssr: false.
import { useEffect } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";

const CENTRO_MADRID = [40.4168, -3.7038];
const tieneCoordenadas = ({ cine }) => cine.lat != null && cine.lng != null;
const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// Pin propio (HTML/CSS en globals.css): violeta autor, gris oscuro comercial, apagado sin sesiones hoy
const icono = (cine, activo) => L.divIcon({
  className: "",
  html: `<span class="pin-cine ${cine.tipo === "autor" ? "pin-autor" : "pin-comercial"}${cine.sesiones_hoy > 0 ? "" : " pin-apagado"}${activo ? " pin-activo" : ""}">${cine.sesiones_hoy}</span>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -14],
});

// Encuadra los cines visibles (todos: centro de Madrid) y recoloca el mapa cuando cambia de tamaño (p. ej. al
// pasar de oculto a visible en móvil, donde Leaflet no se entera solo)
function Encuadre({ puntos, todos }) {
  const map = useMap();
  const clave = puntos.map((p) => p.join()).join("|");

  useEffect(() => {
    const encuadrar = () => {
      const animate = !sinMovimiento();
      if (todos || puntos.length === 0) map.setView(CENTRO_MADRID, 13, { animate });
      else if (puntos.length === 1) map.setView(puntos[0], 15, { animate });
      else map.fitBounds(puntos, { padding: [40, 40], maxZoom: 15, animate });
    };
    encuadrar();
    let ancho = map.getContainer().clientWidth;
    const observador = new ResizeObserver(() => {
      map.invalidateSize();
      const nuevo = map.getContainer().clientWidth;
      if (ancho === 0 && nuevo > 0) encuadrar();
      ancho = nuevo;
    });
    observador.observe(map.getContainer());
    return () => observador.disconnect();
  }, [map, clave, todos]);  // eslint-disable-line react-hooks/exhaustive-deps -- clave resume puntos

  return null;
}

// items: [{ cine, hoy }] ya filtrados; activo: id del cine resaltado; popup(item): contenido del popup
export default function MapaCines({ items, todos, activo, onPin, posicion, popup }) {
  const conPunto = items.filter(tieneCoordenadas);
  const animado = !sinMovimiento();
  return (
    <MapContainer center={CENTRO_MADRID} zoom={13} scrollWheelZoom className="h-full w-full"
                  zoomAnimation={animado} fadeAnimation={animado} markerZoomAnimation={animado}
                  aria-label="Mapa de los cines" role="region">
      {/* CARTO Positron ya exige clave de API (devuelve "API KEY REQUIRED"): tiles estándar de OSM */}
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19}
                 attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
      <Encuadre puntos={conPunto.map(({ cine }) => [cine.lat, cine.lng])} todos={todos} />
      {conPunto.map((item) => (
        <Marker key={item.cine.id} position={[item.cine.lat, item.cine.lng]} icon={icono(item.cine, item.cine.id === activo)}
                zIndexOffset={item.cine.id === activo ? 1000 : 0} title={item.cine.nombre} alt={item.cine.nombre}
                eventHandlers={{ click: () => onPin(item.cine.id) }}>
          <Popup>{popup(item)}</Popup>
        </Marker>
      ))}
      {posicion && (
        <CircleMarker center={[posicion.lat, posicion.lng]} radius={8}
                      pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#2563eb", fillOpacity: 1 }}>
          <Popup>Estás aquí</Popup>
        </CircleMarker>
      )}
    </MapContainer>
  );
}
