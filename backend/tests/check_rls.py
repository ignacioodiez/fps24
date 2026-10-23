"""Self-check de la migración 0009 (RLS en public). Solo BD local.
Uso: docker compose exec api python tests/check_rls.py
Aplica alembic upgrade head, comprueba relrowsecurity en todas las tablas de public, prueba en una
transacción con rollback los roles anon/authenticated y el aborto sin BYPASSRLS, y relanza los check_* de BD."""
import importlib.util
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database.engine import engine

if engine.url.host not in ("db", "localhost", "127.0.0.1"):
    sys.exit(f"Me niego: la BD no es local (host {engine.url.host!r})")

subprocess.run(["alembic", "upgrade", "head"], cwd=BACKEND, check=True)

with engine.connect() as conn:
    sin_rls = conn.execute(text("SELECT relname FROM pg_class WHERE relnamespace = 'public'::regnamespace "
                                "AND relkind IN ('r', 'p') AND NOT relrowsecurity")).scalars().all()
    tablas = conn.execute(text("SELECT count(*) FROM pg_class WHERE relnamespace = 'public'::regnamespace "
                               "AND relkind IN ('r', 'p')")).scalar()
    assert not sin_rls, f"Tablas sin RLS: {sin_rls}"
    assert tablas >= 4, tablas  # pelicula, pase, cine, alembic_version
    assert conn.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = 'public.alembic_version'::regclass")).scalar()
print(f"OK: RLS activado en las {tablas} tablas de public")

spec = importlib.util.spec_from_file_location("m0009", BACKEND / "migrations/versions/0009_rls_public.py")
m0009 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m0009)

# Simula Supabase: CREATE ROLE y los GRANT son transaccionales, el rollback lo deshace todo
with engine.connect() as conn:
    try:
        for rol in ("anon", "authenticated"):
            if not conn.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :r"), {"r": rol}).scalar():
                conn.execute(text(f"CREATE ROLE {rol} NOLOGIN"))
        conn.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated"))
        conn.execute(text("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated"))
        conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon, authenticated"))
        conn.execute(text(m0009.SQL_UPGRADE))
        conn.execute(text(m0009.SQL_UPGRADE))  # idempotente
        for rol in ("anon", "authenticated"):
            assert not conn.execute(text("SELECT has_table_privilege(:r, 'public.pase', 'SELECT')"), {"r": rol}).scalar(), rol
        conn.execute(text("CREATE TABLE public.check_rls_futura (id int)"))
        assert not conn.execute(text("SELECT has_table_privilege('anon', 'public.check_rls_futura', 'SELECT')")).scalar()
        print("OK: anon/authenticated sin permisos, también en tablas futuras")

        conn.execute(text("CREATE ROLE check_rls_sin_bypass NOLOGIN"))
        conn.execute(text("SET LOCAL ROLE check_rls_sin_bypass"))
        try:
            with conn.begin_nested():
                conn.execute(text(m0009.SQL_UPGRADE))
            raise AssertionError("sin BYPASSRLS la migración debería abortar")
        except DBAPIError as e:
            assert "Migración RLS abortada" in str(e), e
        print("OK: aborta si el rol no es superuser ni tiene BYPASSRLS")
    finally:
        conn.rollback()

for check in ("check_destacadas.py", "check_estrenos_especiales.py", "check_cine_detalle.py"):
    subprocess.run([sys.executable, str(BACKEND / "tests" / check)], cwd=BACKEND, check=True)
print("OK: check_rls")
