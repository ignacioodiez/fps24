"""Self-check de app/auth.py y GET /me, sin red ni BD: claves EC generadas aquí y JWKS falso.
Uso: docker compose exec api python tests/check_auth.py"""
import os
import sys
import time
from pathlib import Path

os.environ["SUPABASE_URL"] = "https://prueba.supabase.co"  # antes de importar app.auth
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app import auth
from main import leer_me  # no conecta con la BD: solo crea el engine

ISS = "https://prueba.supabase.co/auth/v1"
clave = ec.generate_private_key(ec.SECP256R1())
otra = ec.generate_private_key(ec.SECP256R1())


class JwksFalso:
    """Sustituye a PyJWKClient: solo conoce la clave pública 'k1' (como el JWKS de Supabase)."""
    def get_signing_key_from_jwt(self, token):
        kid = jwt.get_unverified_header(token).get("kid")
        if kid != "k1":
            raise jwt.PyJWKClientError(f"Unable to find a signing key that matches: {kid}")
        return jwt.PyJWK.from_json(jwt.algorithms.ECAlgorithm.to_jwk(clave.public_key()), algorithm="ES256")


auth._jwks = JwksFalso()


def token(firma=clave, alg="ES256", **cambios):
    datos = {"sub": "uuid-123", "email": "ana@example.com", "aud": "authenticated", "iss": ISS,
             "exp": int(time.time()) + 3600, "role": "authenticated", **cambios}
    return jwt.encode(datos, firma, algorithm=alg, headers={"kid": "k1"})


def estado(authorization):
    try:
        return 200, leer_me(auth.usuario_actual(authorization))
    except HTTPException as e:
        return e.status_code, e.detail


assert estado(f"Bearer {token()}") == (200, {"id": "uuid-123", "email": "ana@example.com"})
print("OK: token válido -> 200")

casos = {
    "sin token": None,
    "sin Bearer": token(),
    "Bearer vacío": "Bearer ",
    "caducado": f"Bearer {token(exp=int(time.time()) - 10)}",
    "aud incorrecta": f"Bearer {token(aud='anon')}",
    "iss incorrecto": f"Bearer {token(iss='https://otro.supabase.co/auth/v1')}",
    "sin exp": f"Bearer {jwt.encode({'sub': 'x', 'aud': 'authenticated', 'iss': ISS}, clave, algorithm='ES256', headers={'kid': 'k1'})}",
    "otra clave": f"Bearer {token(firma=otra)}",
    "alg none": f"Bearer {jwt.encode({'sub': 'x', 'aud': 'authenticated', 'iss': ISS, 'exp': int(time.time()) + 60}, None, algorithm='none', headers={'kid': 'k1'})}",
    "kid desconocido": "Bearer " + jwt.encode({"sub": "x"}, clave, algorithm="ES256", headers={"kid": "zz"}),
    "basura": "Bearer no.es.jwt",
}
for nombre, cabecera in casos.items():
    codigo, detalle = estado(cabecera)
    assert codigo == 401, (nombre, codigo, detalle)
    print(f"OK: {nombre} -> 401 ({detalle})")

# HS256 (secreto compartido): solo se aceptan ES256/RS256
hs = token(firma="secreto", alg="HS256")
assert estado(f"Bearer {hs}")[0] == 401
print("OK: HS256 -> 401")

auth.SUPABASE_URL = ""
assert estado(f"Bearer {token()}")[0] == 503
print("OK: sin SUPABASE_URL -> 503")
print("TODO OK")
