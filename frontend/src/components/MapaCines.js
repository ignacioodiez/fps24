"use client";

// Mapa de "Cines de Madrid" (/cines) (Leaflet). Solo en cliente: se carga con next/dynamic y ssr: false.
import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";

const CENTRO_MADRID = [40.4168, -3.7038];
const tieneCoordenadas = ({ cine }) => cine.lat != null && cine.lng != null;
const sinMovimiento = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const escapar = (texto) => texto.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// Texto del pin para lectores de pantalla y para el title (el color nunca es la única señal). pronto undefined:
// sin datos de sesiones (ficha del cine), no se dice nada
const textoPin = (cine, pronto, favorito) => `${cine.nombre}${favorito ? ", favorito" : ""}${
  pronto === undefined ? "" : pronto ? ": empieza alguna sesión en la próxima hora" : ": nada en la próxima hora"}`;

// Pin propio (HTML/CSS en globals.css): violeta y redondo con sesiones en la próxima hora, gris y cuadrado si no;
// ★ si es favorito
const icono = (cine, activo, pronto, favorito) => L.divIcon({
  className: "",
  html: `<span class="pin-cine${pronto ? " pin-pronto" : ""}${activo ? " pin-activo" : ""}"><span aria-hidden="true">${cine.sesiones_hoy}</span>${
    favorito ? '<span class="pin-fav" aria-hidden="true">★</span>' : ""}<span class="sr-only">${escapar(textoPin(cine, pronto, favorito))}</span></span>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -14],
});

// Encuadra los cines visibles (todos: centro de Madrid), o la posición elegida, y recoloca el mapa cuando cambia
// de tamaño (Leaflet no se entera solo)
function Encuadre({ puntos, todos, posicion }) {
  const map = useMap();
  const clave = puntos.map((p) => p.join()).join("|");
  const clavePos = posicion ? `${posicion.lat},${posicion.lng}` : "";

  useEffect(() => {
    const encuadrar = () => {
      const animate = !sinMovimiento();
      if (posicion) map.setView([posicion.lat, posicion.lng], 15, { animate });
      else if (todos || puntos.length === 0) map.setView(CENTRO_MADRID, 13, { animate });
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
  }, [map, clave, todos, clavePos]);  // eslint-disable-line react-hooks/exhaustive-deps -- clave y clavePos resumen puntos y posicion

  return null;
}

// Tarjeta pulsada: centra el mapa en su pin y abre su popup. centrar: { id, n } (n cambia en cada pulsación)
function Centrar({ centrar, marcadores }) {
  const map = useMap();
  useEffect(() => {
    const marcador = centrar && marcadores.current[centrar.id];
    if (!marcador) return;
    map.setView(marcador.getLatLng(), Math.max(map.getZoom(), 15), { animate: !sinMovimiento() });
    marcador.openPopup();
  }, [map, centrar, marcadores]);
  return null;
}

// Con onColocar, un clic en el mapa elige la posición
function Colocar({ onColocar }) {
  useMapEvents({ click: (e) => onColocar?.({ lat: e.latlng.lat, lng: e.latlng.lng }) });
  return null;
}

// items: [{ cine }] ya filtrados; activo: id del cine resaltado; popup(item): contenido del popup;
// pronto y favoritos: Set de slugs; centrar: ver Centrar; onColocar: ver Colocar
export default function MapaCines({ items, todos, activo, onPin, posicion, popup, pronto, favoritos, centrar, onColocar }) {
  const conPunto = items.filter(tieneCoordenadas);
  const animado = !sinMovimiento();
  const marcadores = useRef({});
  return (
    <MapContainer center={CENTRO_MADRID} zoom={13} scrollWheelZoom className="h-full w-full"
                  zoomAnimation={animado} fadeAnimation={animado} markerZoomAnimation={animado}
                  aria-label="Mapa de los cines" role="region">
      {/* CARTO Positron ya exige clave de API (devuelve "API KEY REQUIRED"): tiles estándar de OSM */}
      <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" maxZoom={19}
                 attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' />
      <Encuadre puntos={conPunto.map(({ cine }) => [cine.lat, cine.lng])} todos={todos} posicion={posicion} />
      <Centrar centrar={centrar} marcadores={marcadores} />
      <Colocar onColocar={onColocar} />
      {conPunto.map((item) => {
        const { cine } = item;
        const esPronto = pronto && pronto.has(cine.slug), esFavorito = Boolean(favoritos?.has(cine.slug));
        return (
          <Marker key={cine.id} position={[cine.lat, cine.lng]} icon={icono(cine, cine.id === activo, esPronto, esFavorito)}
                  ref={(m) => { marcadores.current[cine.id] = m; }}
                  zIndexOffset={cine.id === activo ? 1000 : esPronto ? 500 : 0} title={textoPin(cine, esPronto, esFavorito)}
                  eventHandlers={{ click: () => onPin(cine.id) }}>
            <Popup>{popup(item)}</Popup>
          </Marker>
        );
      })}
      {posicion && (
        <CircleMarker center={[posicion.lat, posicion.lng]} radius={8}
                      pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#2563eb", fillOpacity: 1 }}>
          <Popup>{posicion.origen === "gps" ? "Estás aquí" : "Punto elegido"}</Popup>
        </CircleMarker>
      )}
    </MapContainer>
  );
}
