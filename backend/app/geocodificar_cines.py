"""Geocodificador de un solo uso: busca en Nominatim (OpenStreetMap) las coordenadas de los cines de
CINES_DATOS sin lat/lng y las guarda en backend/coordenadas_cines.json para revisarlas a mano.
No escribe en la BD ni en el código. Política de Nominatim: 1 petición por segundo y User-Agent propio.
Uso: python -m app.geocodificar_cines"""
import json
import time
from pathlib import Path

import requests

from app.services.cines import CINES_DATOS, normalizar

URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "fps24 (contacto: ignacio.diez.vergara@gmail.com)"
SALIDA = Path(__file__).resolve().parent.parent / "coordenadas_cines.json"
PAUSA = 1.1  # segundos entre peticiones

_TIPOS_VIA = ("calle", "plaza", "paseo", "glorieta", "avenida")
_ARTICULOS = ("de las", "de los", "de la", "del", "de")


def partes(direccion: str) -> dict:
    """"[Lugar, ]Calle, Nº (o s/n), CP Ciudad" -> {calle, numero, cp, ciudad}."""
    trozos = direccion.split(", ")
    i = next(i for i, t in enumerate(trozos) if t.isdigit() or t == "s/n")
    cp, ciudad = trozos[-1].split(" ", 1)
    return dict(calle=trozos[i - 1], numero=trozos[i], cp=cp, ciudad=ciudad)


def clave_calle(calle: str) -> str:
    """Sin tipo de vía ni artículos: "Calle de la Princesa" y "Princesa" dan "princesa"."""
    clave = normalizar(calle)
    for prefijo in _TIPOS_VIA + _ARTICULOS:
        if clave.startswith(prefijo + " "):
            clave = clave[len(prefijo) + 1:]
    return clave


def dudas(direccion: str, resultado: dict) -> list:
    """Motivos para revisar un resultado de Nominatim (vacío si casa calle, número, ciudad y CP)."""
    if not resultado:
        return ["NO ENCONTRADO"]
    esperado, direccion_osm = partes(direccion), resultado.get("address", {})
    motivos = []
    calle_osm = direccion_osm.get("road") or direccion_osm.get("pedestrian") or direccion_osm.get("square") or ""
    if clave_calle(calle_osm) != clave_calle(esperado["calle"]):
        motivos.append(f"otra calle ({calle_osm or '?'})")
    if direccion_osm.get("house_number") != esperado["numero"]:
        motivos.append(f"otro número ({direccion_osm.get('house_number') or 'sin número'})")
    if normalizar(direccion_osm.get("city", "")) != normalizar(esperado["ciudad"]):
        motivos.append(f"otra ciudad ({direccion_osm.get('city') or '?'})")
    if direccion_osm.get("postcode") != esperado["cp"]:
        motivos.append(f"otro CP ({direccion_osm.get('postcode') or '?'})")
    return motivos


def _buscar(direccion: str):
    """Una sola petición, búsqueda estructurada. None si no hay resultado o falla (sin reintentos)."""
    p = partes(direccion)
    try:
        res = requests.get(URL, timeout=15, headers={"User-Agent": USER_AGENT}, params=dict(
            street=f"{p['numero']} {p['calle']}", city=p["ciudad"], postalcode=p["cp"], country="España",
            format="jsonv2", addressdetails=1, limit=1))
        res.raise_for_status()
        resultados = res.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  error en Nominatim para {direccion!r}: {e}")
        return None
    return resultados[0] if resultados else None


def main():
    pendientes = {slug: d for slug, d in CINES_DATOS.items() if d["lat"] is None or d["lng"] is None}
    filas = []
    for i, (slug, datos) in enumerate(pendientes.items()):
        if i:
            time.sleep(PAUSA)
        r = _buscar(datos["direccion"])
        filas.append(dict(slug=slug, direccion=datos["direccion"], display_name=r and r.get("display_name"),
                          lat=r and float(r["lat"]), lng=r and float(r["lon"]),
                          tipo=r and f"{r.get('category')}/{r.get('type')} ({r.get('addresstype')})",
                          dudas=dudas(datos["direccion"], r)))
    SALIDA.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    for f in filas:
        marca = "REVISAR: " + "; ".join(f["dudas"]) if f["dudas"] else "ok"
        print(f"{f['slug']} | {f['direccion']} | {f['display_name']} | {f['lat']} | {f['lng']} | {f['tipo']} | {marca}")
    print(f"{len(filas)} cines, {sum(bool(f['dudas']) for f in filas)} a revisar. Guardado en {SALIDA}")


if __name__ == "__main__":
    main()
