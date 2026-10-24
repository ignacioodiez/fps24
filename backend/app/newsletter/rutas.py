"""Endpoints públicos de la newsletter: suscribir (doble opt-in), confirmar y baja. /newsletter/suscribir responde
siempre lo mismo, exista o no el email, y el correo sale en segundo plano para que el tiempo de respuesta tampoco lo
delate."""
import logging
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, select

from app.database.engine import get_session
from app.database.models import Suscriptor
from app.newsletter import correo, plantilla

router = APIRouter(prefix="/newsletter")
log = logging.getLogger("uvicorn.error").getChild("newsletter")

RESPUESTA = {"mensaje": "Si el email es correcto, te llegará un correo para confirmar la suscripción."}
LIMITE_IP = (5, 600)        # peticiones por IP en 10 minutos
LIMITE_EMAIL = (3, 3600)    # peticiones por email en una hora
REENVIO_CADA = timedelta(minutes=10)  # entre dos correos de confirmación al mismo email
CONFIRMACIONES_MAX = 5      # correos de confirmación en total a un email pendiente
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# shortcut: en memoria y por proceso (con varios workers el límite se multiplica); el tope CONFIRMACIONES_MAX de la BD
# es el que de verdad acota los correos a un email. Pasar a la BD o a Redis si hay abuso.
_peticiones = defaultdict(deque)


def limite_superado(clave, maximo: int, ventana: int) -> bool:
    """True si `clave` ya hizo `maximo` peticiones en los últimos `ventana` segundos; si no, apunta esta."""
    ahora, cola = time.monotonic(), _peticiones[clave]
    while cola and cola[0] <= ahora - ventana:
        cola.popleft()
    if len(cola) >= maximo:
        return True
    cola.append(ahora)
    return False


def ip_cliente(request: Request) -> str:
    # shortcut: la primera de X-Forwarded-For (la pone el proxy de Render) se puede falsear; el límite por email y el
    # tope de la BD siguen protegiendo a cada dirección.
    reenviada = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    return reenviada or (request.client.host if request.client else "")


def _ahora():
    return datetime.now(timezone.utc)


class Suscribir(SQLModel):
    email: str = Field(max_length=254)
    web: str = Field(default="", max_length=200)  # campo trampa: invisible en el formulario, solo lo rellenan bots


def enviar_confirmacion(email: str, token: str):
    asunto, html, texto = plantilla.confirmacion(f"{correo.api_publica()}/newsletter/confirmar?token={token}",
                                                 correo.contacto())
    try:
        correo.cliente().enviar(correo.mensaje(email, asunto, html, texto))
    except Exception:  # noqa: BLE001 — en segundo plano: no hay a quién responder, se registra
        log.exception("no se pudo enviar la confirmación de la newsletter")


@router.post("/suscribir")
def suscribir(cuerpo: Suscribir, request: Request, tareas: BackgroundTasks, session: Session = Depends(get_session)):
    if limite_superado(("ip", ip_cliente(request)), *LIMITE_IP):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones. Inténtalo dentro de un rato.")
    email = cuerpo.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(status_code=422, detail="Escribe un email válido.")
    if cuerpo.web or limite_superado(("email", email), *LIMITE_EMAIL):
        return RESPUESTA

    s = session.exec(select(Suscriptor).where(Suscriptor.email == email)).first()
    if s is None:
        s = Suscriptor(email=email, token_baja=secrets.token_urlsafe(32))
    elif s.estado == "activo":
        return RESPUESTA
    elif s.estado == "baja":  # vuelve a suscribirse: otra vez doble opt-in
        s.estado, s.confirmaciones_enviadas, s.confirmacion_enviada_en = "pendiente", 0, None
    if s.confirmaciones_enviadas >= CONFIRMACIONES_MAX or (
            s.confirmacion_enviada_en and _ahora() - s.confirmacion_enviada_en < REENVIO_CADA):
        return RESPUESTA
    s.token_confirmacion = s.token_confirmacion or secrets.token_urlsafe(32)
    s.confirmaciones_enviadas += 1
    s.confirmacion_enviada_en = _ahora()
    session.add(s)
    try:
        session.commit()
    except IntegrityError:  # el mismo email en dos peticiones a la vez: la otra ya lo ha guardado
        session.rollback()
        return RESPUESTA
    tareas.add_task(enviar_confirmacion, email, s.token_confirmacion)
    return RESPUESTA


Token = Query(..., min_length=10, max_length=100)


def _a_la_web(pagina: str, valido: bool) -> RedirectResponse:
    return RedirectResponse(f"{plantilla.SITIO}/newsletter/{pagina}" + ("" if valido else "?error=token"), status_code=303)


@router.get("/confirmar")
def confirmar(token: str = Token, session: Session = Depends(get_session)):
    s = session.exec(select(Suscriptor).where(Suscriptor.token_confirmacion == token,
                                              Suscriptor.estado == "pendiente")).first()
    if s:
        s.estado, s.confirmado_en, s.token_confirmacion = "activo", _ahora(), None
        session.add(s)
        session.commit()
    return _a_la_web("confirmada", bool(s))


def dar_de_baja(session: Session, token: str) -> bool:
    s = session.exec(select(Suscriptor).where(Suscriptor.token_baja == token)).first()
    if s and s.estado != "baja":
        s.estado, s.baja_en, s.token_confirmacion = "baja", _ahora(), None
        session.add(s)
        session.commit()
    return bool(s)


@router.get("/baja")
def baja(token: str = Token, session: Session = Depends(get_session)):
    return _a_la_web("baja", dar_de_baja(session, token))


# Baja en un clic (List-Unsubscribe-Post): el gestor de correo hace POST a la URL de List-Unsubscribe; el cuerpo
# (List-Unsubscribe=One-Click) no hace falta leerlo.
@router.post("/baja")
def baja_un_clic(token: str = Token, session: Session = Depends(get_session)):
    if not dar_de_baja(session, token):
        raise HTTPException(status_code=404, detail="Enlace de baja no válido")
    return {"mensaje": "Te has dado de baja."}
