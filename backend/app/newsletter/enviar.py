"""Cron de la newsletter: python -m app.newsletter.enviar [--dry-run [--fecha AAAA-MM-DD]] [--forzar] [--salida archivo.html]

Se programa dos veces los lunes (14:00 y 15:00 UTC) y el script decide: solo envía si en Europe/Madrid es lunes, son
las 16 y esa semana ISO no consta en newsletter_envio. Así cubre el horario de verano (UTC+2) y el de invierno (UTC+1).
--dry-run: no envía ni escribe en la BD; deja el HTML en --salida y dice qué habría hecho. Con --fecha, como si se
enviara ese día a las 16:00 (ventana de ese día y los 6 siguientes).
--forzar: envía aunque no sea lunes a las 16 o la semana ya conste (para reenviar a mano tras un fallo)."""
import argparse
from datetime import date
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select, update

from app.database.engine import engine
from app.database.models import NewsletterEnvio, Suscriptor
from app.newsletter import correo, plantilla
from app.newsletter.contenido import HORA_ENVIO, datos_semana, momento_envio
from app.services.tiempo import ahora_madrid

HORA = HORA_ENVIO


def semana_iso(ahora: datetime) -> str:
    anio, semana, _ = ahora.isocalendar()
    return f"{anio}-W{semana:02d}"


def toca(ahora: datetime) -> bool:
    return ahora.weekday() == 0 and ahora.hour == HORA


def correos_semana(session: Session, datos: dict) -> list:
    """Un correo por suscriptor activo (cada uno con su enlace de baja). Nunca a pendientes ni a bajas."""
    activos = session.exec(select(Suscriptor.email, Suscriptor.token_baja)
                           .where(Suscriptor.estado == "activo").order_by(Suscriptor.id)).all()
    return [correo.mensaje(email, *plantilla.semanal(datos, correo.url_baja(token), correo.contacto()), token_baja=token)
            for email, token in activos]


def main(argv=None, ahora: datetime = None, envio=None) -> str:
    """Devuelve qué ha hecho (para los tests): no-toca, ya-enviada, vacia, dry-run o enviada."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--forzar", action="store_true")
    p.add_argument("--salida", default="newsletter_preview.html")
    p.add_argument("--fecha", type=date.fromisoformat, help="solo con --dry-run: fecha de envío simulada")
    args = p.parse_args(argv)
    if args.fecha and not args.dry_run:
        p.error("--fecha solo vale con --dry-run")
    ahora = ahora or (momento_envio(args.fecha) if args.fecha else ahora_madrid())
    semana = semana_iso(ahora)

    with Session(engine) as session:
        ya_enviada = session.exec(select(NewsletterEnvio.id).where(NewsletterEnvio.semana == semana)).first() is not None
        datos = datos_semana(session, ahora)
        if args.dry_run:
            Path(args.salida).write_text(plantilla.semanal(datos, correo.url_baja("vista-previa"), correo.contacto())[1],
                                         encoding="utf-8")
            print(f"[dry-run] {semana}: toca={toca(ahora)} ya_enviada={ya_enviada} estrenos={len(datos['estrenos'])} "
                  f"especiales={len(datos['especiales'])} destinatarios={len(correos_semana(session, datos))} "
                  f"ventana={datos['desde']}..{datos['hasta']} -> HTML en {args.salida}")
            for clave in ("estrenos", "especiales"):
                print(f"  {clave}: " + "; ".join(f"{f['titulo']} ({plantilla.dia_corto(f['fecha_hora'])})" for f in datos[clave]))
            return "dry-run"
        if not args.forzar and not toca(ahora):
            print(f"No toca: {ahora:%A %H:%M} en Madrid (sale los lunes a las {HORA})")
            return "no-toca"
        if not datos["estrenos"] and not datos["especiales"]:
            print(f"{semana}: sin estrenos ni especiales, no se envía")
            return "vacia"
        if not os.getenv("API_URL_PUBLICA"):
            sys.exit("Falta API_URL_PUBLICA: los enlaces de baja apuntarían a localhost")

        # Se reserva la semana antes de enviar: dos ejecuciones a la vez no pueden mandarla dos veces
        reservada = session.exec(insert(NewsletterEnvio).values(semana=semana)
                                 .on_conflict_do_nothing(index_elements=["semana"]).returning(NewsletterEnvio.id)).first()
        session.commit()
        if reservada is None and not args.forzar:
            print(f"{semana} ya enviada")
            return "ya-enviada"

        correos = correos_semana(session, datos)
        ok, errores = correo.enviar_por_lotes(correos, envio)
        session.exec(update(NewsletterEnvio).where(NewsletterEnvio.semana == semana)
                     .values(destinatarios=len(correos), ok=ok, errores=errores, enviado_en=datetime.now(timezone.utc)))
        session.commit()
    print(f"{semana}: {ok} enviados, {errores} errores de {len(correos)}")
    if errores:
        sys.exit(1)  # el cron de Render marca la ejecución como fallida
    return "enviada"


if __name__ == "__main__":
    main()
