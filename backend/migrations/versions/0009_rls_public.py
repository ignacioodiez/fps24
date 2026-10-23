"""RLS en todas las tablas de public y sin permisos para anon/authenticated (API REST de Supabase)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, Sequence[str], None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Idempotente: en producción ya se aplicó a mano. Sin FORCE y sin políticas: el backend
# conecta como postgres (BYPASSRLS) y la clave pública de Supabase no ve ninguna fila.
SQL_UPGRADE = """
DO $$
DECLARE
    t record;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user AND (rolsuper OR rolbypassrls)) THEN
        RAISE EXCEPTION 'Migración RLS abortada: el rol % no es superuser ni tiene BYPASSRLS; '
                        'con RLS activado la API se quedaría sin datos', current_user;
    END IF;

    FOR t IN SELECT c.relname FROM pg_class c
             WHERE c.relnamespace = 'public'::regnamespace AND c.relkind IN ('r', 'p') AND NOT c.relrowsecurity
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t.relname);
    END LOOP;

    -- En el Postgres local de Docker estos roles no existen; en Supabase sí
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
       AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
        REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
        REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated;
        -- Sin FOR ROLE: vale para los objetos que cree el rol actual (el de Alembic)
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated;
    END IF;
END
$$;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(SQL_UPGRADE)


def downgrade() -> None:
    """No-op a propósito: desactivar RLS volvería a exponer las tablas por la API REST de Supabase."""
