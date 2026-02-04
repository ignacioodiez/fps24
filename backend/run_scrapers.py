import time
import sys
import os
from sqlmodel import Session, delete

# Aseguramos que Python encuentre los módulos de la app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- IMPORTAMOS LA BBDD PARA PODER BORRARLA ---
from app.database.engine import engine
from app.database.models import Pase

# --- IMPORTAMOS TUS AGENTES (Todos los cines) ---
from app.scrapers.cines.dore import scrapear_dore
from app.scrapers.cines.equis import scrapear_equis
from app.scrapers.cines.cineteca import scrapear_cineteca
from app.scrapers.cines.cine_estudio import scrapear_cine_estudio
from app.scrapers.cines.renoir_princesa import scrapear_renoir_princesa
from app.scrapers.cines.renoir_plazaesp import scrapear_renoir_plazaesp
from app.scrapers.cines.renoir_retiro import scrapear_renoir_retiro
from app.scrapers.cines.verdi import scrapear_verdi
from app.scrapers.cines.cine_paz import scrapear_cine_paz
from app.scrapers.cines.mk2_palacio_hielo import scrapear_mk2_palacio_hielo
from app.scrapers.cines.embajadores import scrapear_embajadores
from app.scrapers.cines.golem import scrapear_golem
from app.scrapers.cines.yelmo import scrapear_yelmo_ideal


def limpiar_base_datos():
    print("🧹 LIMPIEZA: Borrando sesiones antiguas...")
    try:
        with Session(engine) as session:
            # Esta sentencia borra TODAS las filas de la tabla Pase
            statement = delete(Pase)
            resultado = session.exec(statement)
            session.commit()
            print(f"🗑️  ¡Hecho! Se han eliminado {resultado.rowcount} pases antiguos.")
    except Exception as e:
        print(f"⚠️ Error limpiando base de datos (quizás estaba vacía): {e}")

def lanzar_todo():
    print("\n🚀 INICIANDO PROTOCOLO 'MADRID INDIE' - RECARGA COMPLETA")
    print("===========================================================\n")

    # 1. PRIMERO LIMPIAMOS LA CASA
    limpiar_base_datos()
    print("\n-----------------------------------------------------------")

    # 2. LUEGO LLENAMOS LA DESPENSA
    
    # --- GRUPO 1: INSTITUCIONES & ALTERNATIVOS ---
    try:
        scrapear_dore()
    except Exception as e:
        print(f"❌ Error crítico en Doré: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_cineteca()
    except Exception as e:
        print(f"❌ Error crítico en Cineteca: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_cine_estudio() # Círculo de Bellas Artes
    except Exception as e:
        print(f"❌ Error crítico en Cine Estudio: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_equis()
    except Exception as e:
        print(f"❌ Error crítico en Sala Equis: {e}")

    # --- GRUPO 2: LOS RENOIR ---
    print("\n-----------------------------------------------------------")
    
    try:
        scrapear_renoir_princesa()
    except Exception as e:
        print(f"❌ Error crítico en Renoir Princesa: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_renoir_plazaesp()
    except Exception as e:
        print(f"❌ Error crítico en Renoir Plaza España: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_renoir_retiro()
    except Exception as e:
        print(f"❌ Error crítico en Renoir Retiro: {e}")

    # --- GRUPO 3: LOS CLÁSICOS VOSE ---
    print("\n-----------------------------------------------------------")

    try:
        scrapear_verdi()
    except Exception as e:
        print(f"❌ Error crítico en Cines Verdi: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_golem()
    except Exception as e:
        print(f"❌ Error crítico en Cine Golem: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_embajadores() 
    except Exception as e:
        print(f"❌ Error crítico en Cine Embajadores: {e}") 

    # --- GRUPO 4: LOS GRANDES (MK2 & PAZ) ---
    print("\n-----------------------------------------------------------")
    
    try:
        scrapear_cine_paz()
    except Exception as e:
        print(f"❌ Error crítico en Cine Paz: {e}")

    print("\n-----------------------------------------------------------")
    
    try:
        scrapear_mk2_palacio_hielo()
    except Exception as e:
        print(f"❌ Error crítico en Palacio de Hielo: {e}")

    # --- GRUPO 5: MAINSTREAM (YELMO) ---
    print("\n-----------------------------------------------------------")
    
    try:
        scrapear_yelmo_ideal()          
    except Exception as e:
        print(f"❌ Error crítico en Yelmo Ideal: {e}")  


    print("\n===========================================================")
    print("✅ ¡TODO NUEVO! La base de datos está fresca y actualizada. 🍿")
    print("===========================================================\n")

if __name__ == "__main__":
    lanzar_todo()