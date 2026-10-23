"""Autenticación con Supabase Auth: valida el JWT del usuario con el JWKS público (claves asimétricas, sin secretos)."""
import os
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Header, HTTPException

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
ALGORITMOS = ["ES256", "RS256"]  # nunca "none" ni HS*: con HS* bastaría la clave pública como secreto

_jwks: Optional[jwt.PyJWKClient] = None


@dataclass
class Usuario:
    id: str
    email: Optional[str]


def cliente_jwks() -> jwt.PyJWKClient:
    # Perezoso: la API arranca aunque falte SUPABASE_URL; PyJWKClient cachea las claves
    global _jwks
    if _jwks is None:
        _jwks = jwt.PyJWKClient(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json", cache_keys=True, lifespan=600)
    return _jwks


def no_autorizado(detalle: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detalle, headers={"WWW-Authenticate": "Bearer"})


def usuario_actual(authorization: Optional[str] = Header(None)) -> Usuario:
    if not SUPABASE_URL:
        raise HTTPException(status_code=503, detail="Autenticación no configurada (falta SUPABASE_URL)")
    esquema, _, token = (authorization or "").partition(" ")
    if esquema.lower() != "bearer" or not token.strip():
        raise no_autorizado("Falta el token (Authorization: Bearer <token>)")
    try:
        clave = cliente_jwks().get_signing_key_from_jwt(token.strip())
        datos = jwt.decode(
            token.strip(), clave.key, algorithms=ALGORITMOS, audience="authenticated",
            issuer=f"{SUPABASE_URL}/auth/v1", options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.ExpiredSignatureError:
        raise no_autorizado("La sesión ha caducado")
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(status_code=503, detail="No se pudieron obtener las claves de Supabase")
    except jwt.PyJWTError:
        raise no_autorizado("Token no válido")
    return Usuario(id=datos["sub"], email=datos.get("email"))
