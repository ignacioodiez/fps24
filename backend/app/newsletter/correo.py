"""Envío por la API HTTP de Resend con requests (ya instalado; sin SDK). Todo pasa por `cliente()`: los tests lo
sustituyen por uno simulado y nunca sale un correo real."""
import os
import time

import requests

RESEND_URL = "https://api.resend.com"
LOTE = 100     # máximo de correos por llamada a /emails/batch
PAUSA = 0.6    # segundos entre llamadas: por debajo del límite por defecto de Resend (2 peticiones/s)
REINTENTOS = 3  # ante un 429


def remitente() -> str:
    return os.getenv("NEWSLETTER_FROM") or "FPS24 Esta semana en Madrid <newsletter@fps24.es>"


def contacto() -> str:
    return os.getenv("EMAIL_CONTACTO") or "ignacio.diez.vergara@gmail.com"  # el mismo que /privacidad


def api_publica() -> str:
    """URL pública de esta API: los enlaces de confirmar y de baja (y List-Unsubscribe) apuntan aquí."""
    return (os.getenv("API_URL_PUBLICA") or "http://localhost:8000").rstrip("/")


def url_baja(token: str) -> str:
    return f"{api_publica()}/newsletter/baja?token={token}"


def mensaje(para: str, asunto: str, html: str, texto: str, token_baja: str = None) -> dict:
    """Cuerpo de un correo para Resend. Con token_baja, las cabeceras de baja en un clic (RFC 8058)."""
    correo = {"from": remitente(), "to": [para], "reply_to": contacto(), "subject": asunto, "html": html, "text": texto}
    if token_baja:
        correo["headers"] = {"List-Unsubscribe": f"<{url_baja(token_baja)}>",
                             "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"}
    return correo


class Resend:
    def __init__(self, clave: str):
        self.clave = clave

    def _post(self, ruta: str, cuerpo):
        for _ in range(REINTENTOS):
            r = requests.post(RESEND_URL + ruta, json=cuerpo, timeout=30,
                              headers={"Authorization": f"Bearer {self.clave}"})
            if r.status_code != 429:
                break
            time.sleep(float(r.headers.get("retry-after") or 1))
        r.raise_for_status()
        return r.json()

    def enviar(self, correo: dict):
        return self._post("/emails", correo)

    def enviar_lote(self, correos: list):
        """Hasta LOTE correos en una llamada. Si uno es inválido, Resend rechaza el lote entero."""
        return self._post("/emails/batch", correos)


def cliente():
    clave = os.getenv("RESEND_API_KEY")
    if not clave:
        raise RuntimeError("Falta RESEND_API_KEY")
    return Resend(clave)


def enviar_por_lotes(correos: list, envio=None) -> tuple:
    """-> (ok, errores). Un lote fallido cuenta todos sus correos como errores y se sigue con el siguiente."""
    envio = envio or cliente()
    ok = errores = 0
    for i in range(0, len(correos), LOTE):
        lote = correos[i:i + LOTE]
        if i:
            time.sleep(PAUSA)
        try:
            envio.enviar_lote(lote)
            ok += len(lote)
        except Exception as e:  # noqa: BLE001 — se registra y se sigue con el resto
            print(f"Lote {i // LOTE + 1} fallido ({len(lote)} correos): {e}")
            errores += len(lote)
    return ok, errores
