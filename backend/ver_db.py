from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Pase

def leer_db():
    with Session(engine) as session:
        # Buscamos todo lo de Sala Equis
        pases = session.exec(select(Pase)).all()
        
        print(f"\n📊 TOTAL ENCONTRADO EN BBDD: {len(pases)} pases de Sala Equis.\n")
        
        # Imprimimos los 10 primeros para ver si son fechas futuras
        for pase in pases:
            print(f"   🎬 {pase.pelicula} | 📅 {pase.fecha_hora.strftime('%d/%m %H:%M')}")

if __name__ == "__main__":
    leer_db()