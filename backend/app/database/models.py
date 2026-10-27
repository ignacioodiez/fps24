from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import CheckConstraint, Column, DateTime, Index, JSON, SmallInteger, Text, UniqueConstraint, false, func, text, true  # <--- IMPORTANTE: Desde SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB, UUID
from typing import Optional, List
import uuid
from datetime import date, datetime, time, timezone


# 1. ESQUELETO DE LA PELÍCULA
class PeliculaBase(SQLModel):
    titulo: str
    titulo_original: Optional[str] = None
    tmdb_id: Optional[int] = None
    poster_url: Optional[str] = None
    backdrop_url: Optional[str] = None # <--- NUEVO 🖼️
    sinopsis: Optional[str] = None
    nota_tmdb: Optional[float] = None
    anio: Optional[int] = None
    duracion: Optional[int] = None     # <--- NUEVO (minutos) ⏱️
    generos: Optional[str] = None
    youtube_id: Optional[str] = Field(default=None, description="ID del video de YouTube")
    created_at: datetime = Field(default_factory=datetime.now)

# 2. TABLA PELÍCULA
class Pelicula(PeliculaBase, table=True):
    __table_args__ = (Index("ix_pelicula_tmdb_id_unico", "tmdb_id", unique=True,
                            postgresql_where=text("tmdb_id IS NOT NULL")),)
    id: Optional[int] = Field(default=None, primary_key=True)
    imagenes_galeria: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    # Solo en la tabla, no en PeliculaBase: la API no cambia. UTC; None: no se reintenta TMDB.
    tmdb_reintentar_en: Optional[datetime] = None
    # De TMDB (migración 0007), también solo en la tabla
    votos: Optional[int] = None
    fecha_estreno: Optional[date] = None  # estreno en cines en España (release_dates ES, tipo 2 o 3)
    idioma_original: Optional[str] = None
    director: Optional[str] = None
    imdb_id: Optional[str] = None
    tmdb_actualizado_en: Optional[datetime] = None  # UTC; último refresco desde TMDB
    pases: List["Pase"] = Relationship(back_populates="pelicula")

# 3. ESQUELETO DEL PASE
class PaseBase(SQLModel):
    sala: Optional[str] = None
    fecha_hora: datetime
    precio: Optional[str] = None
    link_compra: Optional[str] = None
    idioma: Optional[str] = "Español"
    es_evento_especial: bool = False
    pelicula_id: Optional[int] = Field(default=None, foreign_key="pelicula.id")

# 4. TABLA PASE
class Pase(PaseBase, table=True):
    # Identidad del pase (migración 0006); registrar_pase busca por ella.
    __table_args__ = (Index("ux_pase_identidad", "cine_id", "pelicula_id", "fecha_hora",
                            text("coalesce(idioma, '')"), text("coalesce(sala, '')"), unique=True),)
    id: Optional[int] = Field(default=None, primary_key=True)
    # Solo en la tabla, no en PaseBase: las respuestas de la API no cambian.
    cine_id: int = Field(foreign_key="cine.id", index=True)
    activo: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
    visto_ultima_vez: Optional[datetime] = None  # UTC
    creado_en: Optional[datetime] = None  # UTC; NULL en los pases anteriores a la migración 0007
    pelicula: Optional[Pelicula] = Relationship(back_populates="pases")
    cine_rel: "Cine" = Relationship()

    @property
    def cine(self) -> str:
        """Nombre del cine, como el antiguo campo de texto: la API lo sigue devolviendo."""
        return self.cine_rel.nombre

    @property
    def cine_slug(self) -> str:
        """Slug del cine: con él el front ordena por los cines favoritos del usuario."""
        return self.cine_rel.slug

# 5. TABLA CINE
class Cine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True)
    nombre: str
    ultima_ejecucion_ok: Optional[datetime] = None
    # Ficha del cine (migración 0007)
    direccion: Optional[str] = None
    web: Optional[str] = None
    zona: Optional[str] = None
    tipo: Optional[str] = None
    telefono: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    # Precios (migración 0008): {"entrada", "entrada_laboral", "entrada_finde", "dia_espectador": {"dias", "precio"}, "notas"}
    tarifas: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


# 6. TABLA ALIAS: título de la web normalizado -> película (caché del emparejamiento).
# Las correcciones manuales no van aquí: están en app/services/correcciones_peliculas.py.
class PeliculaAlias(SQLModel, table=True):
    __tablename__ = "pelicula_alias"
    titulo_norm: str = Field(primary_key=True)
    pelicula_id: int = Field(foreign_key="pelicula.id", index=True, ondelete="CASCADE")
    creado_en: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))  # UTC


# 7. DIARIO (migración 0010): películas vistas en sala por cada usuario. Privado: siempre se filtra por user_id.
class DiarioEntrada(SQLModel, table=True):
    __tablename__ = "diario_entrada"
    __table_args__ = (
        UniqueConstraint("user_id", "pelicula_id", "fecha_vista", name="uq_diario_entrada_usuario_pelicula_fecha"),
        CheckConstraint("nota BETWEEN 1 AND 10", name="ck_diario_entrada_nota"),
        CheckConstraint("char_length(comentario) <= 2000", name="ck_diario_entrada_comentario"),
        Index("ix_diario_entrada_usuario_fecha", "user_id", text("fecha_vista DESC")),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))  # sub del JWT, sin FK
    pelicula_id: int = Field(foreign_key="pelicula.id")
    cine_id: Optional[int] = Field(default=None, foreign_key="cine.id", ondelete="SET NULL")
    pase_id: Optional[int] = Field(default=None, foreign_key="pase.id", ondelete="SET NULL")
    fecha_vista: date
    nota: Optional[int] = Field(default=None, sa_column=Column(SmallInteger))  # 1-10 = ½ a 5 estrellas
    comentario: Optional[str] = Field(default=None, sa_column=Column(Text))
    repeticion: bool = Field(default=False, sa_column_kwargs={"server_default": false()})
    creado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    actualizado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    pelicula: Pelicula = Relationship()
    cine: Optional[Cine] = Relationship()


# 8. PERFIL (migración 0011): nombre de usuario único (en minúsculas) y visibilidad. Privado por defecto.
# Migración 0020: privado/amigos/publico para el perfil, el diario y los cines; una sección nunca más abierta que el perfil.
class Perfil(SQLModel, table=True):
    __tablename__ = "perfil"
    __table_args__ = (
        Index("uq_perfil_usuario", text("lower(usuario)"), unique=True),
        CheckConstraint("char_length(bio) <= 160", name="ck_perfil_bio"),
        CheckConstraint("visibilidad IN ('privado', 'amigos', 'publico')", name="ck_perfil_visibilidad"),
        CheckConstraint("diario_visibilidad IN ('privado', 'amigos', 'publico')", name="ck_perfil_diario_visibilidad"),
        CheckConstraint("cines_visibilidad IN ('privado', 'amigos', 'publico')", name="ck_perfil_cines_visibilidad"),
        CheckConstraint("diario_visibilidad = 'privado' OR diario_visibilidad = visibilidad OR visibilidad = 'publico'",
                        name="ck_perfil_diario_visibilidad_perfil"),
        CheckConstraint("cines_visibilidad = 'privado' OR cines_visibilidad = visibilidad OR visibilidad = 'publico'",
                        name="ck_perfil_cines_visibilidad_perfil"),
        # Migración 0018
        CheckConstraint("avatar_tipo IN ('iniciales', 'pelicula')", name="ck_perfil_avatar_tipo"),
        CheckConstraint("letterboxd_usuario ~ '^[A-Za-z0-9_]{2,20}$'", name="ck_perfil_letterboxd"),
    )
    user_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), primary_key=True))  # sub del JWT, sin FK
    usuario: str = Field(sa_column=Column(Text, nullable=False))
    bio: Optional[str] = Field(default=None, sa_column=Column(Text))
    visibilidad: str = Field(default="privado", sa_column=Column(Text, nullable=False, server_default="privado"))
    diario_visibilidad: str = Field(default="privado", sa_column=Column(Text, nullable=False, server_default="privado"))
    # Migración 0018. avatar_color: id de PALETA_AVATAR (app/perfil.py); None = color sacado del nombre
    avatar_tipo: str = Field(default="iniciales", sa_column=Column(Text, nullable=False, server_default="iniciales"))
    avatar_color: Optional[str] = Field(default=None, sa_column=Column(Text))
    avatar_pelicula_id: Optional[int] = Field(default=None, foreign_key="pelicula.id", ondelete="SET NULL")
    letterboxd_usuario: Optional[str] = Field(default=None, sa_column=Column(Text))
    cines_visibilidad: str = Field(default="privado", sa_column=Column(Text, nullable=False, server_default="privado"))
    # Tope de solicitudes de amistad nuevas por día de Madrid (app/amigos.py)
    solicitudes_dia: Optional[date] = None
    solicitudes_hoy: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    creado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    actualizado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))


# 9. CINES FAVORITOS (migración 0013): de cada usuario, sin límite. Privado: siempre se filtra por user_id.
class CineFavorito(SQLModel, table=True):
    __tablename__ = "cine_favorito"
    user_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), primary_key=True))  # sub del JWT, sin FK
    cine_id: int = Field(foreign_key="cine.id", primary_key=True, ondelete="CASCADE", index=True)
    creado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))


# 10. PELÍCULAS OCULTAS (migración 0014): el admin las quita de /destacadas, /estrenos y /especiales. Siguen en la
# cartelera, en /pelicula/{id} y en la búsqueda.
class PeliculaOculta(SQLModel, table=True):
    __tablename__ = "pelicula_oculta"
    pelicula_id: int = Field(foreign_key="pelicula.id", primary_key=True, ondelete="CASCADE")
    motivo: Optional[str] = Field(default=None, sa_column=Column(Text))
    creado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))


# 11. NEWSLETTER (migración 0015). suscriptor: doble opt-in; el email siempre en minúsculas. Nunca sale por la API.
class Suscriptor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    estado: str = Field(default="pendiente", sa_column=Column(Text, nullable=False, server_default="pendiente"))  # pendiente/activo/baja
    token_confirmacion: Optional[str] = Field(default=None, sa_column=Column(Text, unique=True))  # None al confirmar
    token_baja: str = Field(sa_column=Column(Text, nullable=False, unique=True))  # va en cada correo semanal
    confirmaciones_enviadas: int = Field(default=0, sa_column=Column(SmallInteger, nullable=False, server_default="0"))
    confirmacion_enviada_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    user_id: Optional[uuid.UUID] = Field(default=None, sa_column=Column(UUID(as_uuid=True)))  # sin uso en la v1
    creado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    confirmado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    baja_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))


# newsletter_envio: una fila por semana enviada ("2026-W44"); la unicidad hace idempotente el cron
class NewsletterEnvio(SQLModel, table=True):
    __tablename__ = "newsletter_envio"
    id: Optional[int] = Field(default=None, primary_key=True)
    semana: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    enviado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    destinatarios: int = 0
    ok: int = 0
    errores: int = 0


# 12. PRÓXIMOS ESTRENOS (migración 0016): de TMDB, los refresca a diario app.proximamente.actualizar. Sin FK a pelicula:
# la mayoría aún no tiene sesiones; el enlace a la ficha sale de pelicula.tmdb_id al leer.
class EstrenoProximo(SQLModel, table=True):
    __tablename__ = "estreno_proximo"
    tmdb_id: int = Field(primary_key=True, sa_column_kwargs={"autoincrement": False})
    titulo: str = Field(sa_column=Column(Text, nullable=False))
    titulo_original: Optional[str] = Field(default=None, sa_column=Column(Text))
    fecha_es: date = Field(index=True)
    fecha_confirmada: bool = Field(default=False, sa_column_kwargs={"server_default": false()})
    poster_path: str = Field(sa_column=Column(Text, nullable=False))  # "/abc.jpg"; sin póster no se guarda
    sinopsis: Optional[str] = Field(default=None, sa_column=Column(Text))
    popularidad: Optional[float] = None
    votos: Optional[int] = None
    generos: Optional[str] = Field(default=None, sa_column=Column(Text))  # "Drama, Comedia", como pelicula.generos
    idioma_original: Optional[str] = Field(default=None, sa_column=Column(Text))
    # 0017: el admin la quita de /estrenos (las que tienen ficha usan pelicula_oculta). El cron no la toca.
    oculta: bool = Field(default=False, sa_column_kwargs={"server_default": false()})
    actualizado_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))


# 13. SESIONES GUARDADAS (migración 0019): agenda privada de cada usuario. Copia de la sesión al guardarla, para que
# sobreviva aunque el scraper retire el pase; pase_id solo sirve para casarla con la sesión viva de la cartelera.
class SesionGuardada(SQLModel, table=True):
    __tablename__ = "sesion_guardada"
    __table_args__ = (
        UniqueConstraint("user_id", "cine_nombre", "fecha", "hora", "titulo", name="uq_sesion_guardada_usuario_sesion"),
        Index("ix_sesion_guardada_usuario_fecha", "user_id", "fecha", "hora"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(sa_column=Column(UUID(as_uuid=True), nullable=False))  # sub del JWT, sin FK
    pase_id: Optional[int] = Field(default=None, foreign_key="pase.id", ondelete="SET NULL", index=True)
    pelicula_id: Optional[int] = Field(default=None, foreign_key="pelicula.id", ondelete="SET NULL")
    titulo: str = Field(sa_column=Column(Text, nullable=False))
    poster_url: Optional[str] = Field(default=None, sa_column=Column(Text))
    cine_id: Optional[int] = Field(default=None, foreign_key="cine.id", ondelete="SET NULL")
    cine_nombre: str = Field(sa_column=Column(Text, nullable=False))
    cine_slug: str = Field(sa_column=Column(Text, nullable=False))
    fecha: date  # hora local de Madrid, como pase.fecha_hora
    hora: time
    idioma: Optional[str] = Field(default=None, sa_column=Column(Text))  # tal cual pase.idioma ("VOSE", "Español"...)
    link_compra: Optional[str] = Field(default=None, sa_column=Column(Text))
    diario_entrada_id: Optional[int] = Field(default=None, foreign_key="diario_entrada.id", ondelete="SET NULL")  # "La vi"
    creada_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))


# 14. AMIGOS (migración 0020). Un único par por usuarios (uq_amistad_par, sin importar el orden); rechazar o cancelar
# borra la fila. FK a perfil con CASCADE: borrar la cuenta (el perfil) borra sus amistades y bloqueos.
class Amistad(SQLModel, table=True):
    __table_args__ = (
        Index("uq_amistad_par", text("least(solicitante_id, destinatario_id)"), text("greatest(solicitante_id, destinatario_id)"), unique=True),
        CheckConstraint("estado IN ('pendiente', 'aceptada')", name="ck_amistad_estado"),
        CheckConstraint("solicitante_id <> destinatario_id", name="ck_amistad_distintos"),
        Index("ix_amistad_destinatario", "destinatario_id"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")))
    solicitante_id: uuid.UUID = Field(foreign_key="perfil.user_id", ondelete="CASCADE")
    destinatario_id: uuid.UUID = Field(foreign_key="perfil.user_id", ondelete="CASCADE")
    estado: str = Field(default="pendiente", sa_column=Column(Text, nullable=False, server_default="pendiente"))
    creada_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    respondida_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class Bloqueo(SQLModel, table=True):
    __table_args__ = (CheckConstraint("bloqueador_id <> bloqueado_id", name="ck_bloqueo_distintos"),
                      Index("ix_bloqueo_bloqueado", "bloqueado_id"))
    bloqueador_id: uuid.UUID = Field(foreign_key="perfil.user_id", ondelete="CASCADE", primary_key=True)
    bloqueado_id: uuid.UUID = Field(foreign_key="perfil.user_id", ondelete="CASCADE", primary_key=True)
    creada_en: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
