"""Cines favoritos de cada usuario. Privado: toda consulta filtra por el user_id del token. Los endpoints públicos
(/pases, /cines...) no dependen del usuario: el orden por favoritos lo hace el front con el cine_slug de cada pase."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, delete, select

from app.auth import Usuario, usuario_actual
from app.database.engine import get_session
from app.database.models import Cine, CineFavorito
from app.diario import _uid

router = APIRouter()


def _cine(session: Session, slug: str):
    return session.exec(select(Cine).where(Cine.slug == slug)).first()


@router.get("/me/cines-favoritos", response_model=List[str])
def leer_favoritos(usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Slugs de mis favoritos, del más antiguo al más reciente."""
    return session.exec(
        select(Cine.slug).join(CineFavorito, CineFavorito.cine_id == Cine.id)
        .where(CineFavorito.user_id == _uid(usuario))
        .order_by(CineFavorito.creado_en, Cine.slug)
    ).all()


@router.put("/me/cines-favoritos/{slug}", status_code=204)
def anadir_favorito(slug: str, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    uid = _uid(usuario)
    cine = _cine(session, slug)
    if cine is None:
        raise HTTPException(status_code=404, detail="Cine no encontrado")
    # Idempotente y sin carreras: si ya estaba (o llega otra petición igual a la vez), no hace nada
    session.exec(insert(CineFavorito).values(user_id=uid, cine_id=cine.id).on_conflict_do_nothing())
    session.commit()
    return Response(status_code=204)


@router.delete("/me/cines-favoritos/{slug}", status_code=204)
def quitar_favorito(slug: str, usuario: Usuario = Depends(usuario_actual), session: Session = Depends(get_session)):
    """Idempotente: si no estaba, o el cine ya no existe, también 204."""
    uid = _uid(usuario)
    cine = _cine(session, slug)
    if cine is not None:
        session.exec(delete(CineFavorito).where(CineFavorito.user_id == uid, CineFavorito.cine_id == cine.id))
        session.commit()
    return Response(status_code=204)
