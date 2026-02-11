import time
import sys
import os
from sqlmodel import Session, delete

# Aseguramos que Python encuentre los módulos de la app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- IMPORTAMOS LA BBDD Y LOS MODELOS ---
from app.database.engine import engine
from app.database.models import Pase, Pelicula # <--- AÑADIDO PELICULA

# --- IMPORTAMOS TUS AGENTES ---
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
# CORREGIDO: yelmo_ideal en vez de yelmo
from app.scrapers.cines.yelmo_ideal import scrapear_yelmo_ideal 
from app.scrapers.cines.cinesa import scrapear_cinesa
from app.scrapers.cines.palacio_prensa import scrapear_palacio_prensa

def limpiar_base_datos():
    print("🧹 LIMPIEZA TOTAL: Borrando datos antiguos...")
    try:
        with Session(engine) as session:
            # 1. Borrar PASES primero (porque dependen de las pelis)
            statement_pases = delete(Pase)
            res_pases = session.exec(statement_pases)
            
            # 2. Borrar PELÍCULAS después (para regenerarlas limpias)
            statement_pelis = delete(Pelicula)
            res_pelis = session.exec(statement_pelis)
            
            session.commit()
            print(f"🗑️  ¡Hecho! Eliminados {res_pases.rowcount} pases y {res_pelis.rowcount} películas.")
    except Exception as e:
        print(f"⚠️ Error limpiando base de datos: {e}")

def lanzar_todo():
    # INICIO CRONÓMETRO
    inicio = time.time()

    print("\n🚀 INICIANDO PROTOCOLO 'MADRID FPS24' - RECARGA COMPLETA")
    print("===========================================================\n")

    # 1. LIMPIEZA
    limpiar_base_datos()
    print("\n-----------------------------------------------------------")

    # 2. CARGA DE DATOS
    
    # --- GRUPO 1: INSTITUCIONES & ALTERNATIVOS ---
    try: scrapear_dore()
    except Exception as e: print(f"❌ Error crítico en Doré: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_cineteca()
    except Exception as e: print(f"❌ Error crítico en Cineteca: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_cine_estudio()
    except Exception as e: print(f"❌ Error crítico en Cine Estudio: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_equis()
    except Exception as e: print(f"❌ Error crítico en Sala Equis: {e}")

    # --- GRUPO 2: LOS RENOIR ---
    print("\n-----------------------------------------------------------")
    try: scrapear_renoir_princesa()
    except Exception as e: print(f"❌ Error crítico en Renoir Princesa: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_renoir_plazaesp()
    except Exception as e: print(f"❌ Error crítico en Renoir Plaza España: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_renoir_retiro()
    except Exception as e: print(f"❌ Error crítico en Renoir Retiro: {e}")

    # --- GRUPO 3: LOS CLÁSICOS VOSE ---
    print("\n-----------------------------------------------------------")
    try: scrapear_verdi()
    except Exception as e: print(f"❌ Error crítico en Cines Verdi: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_golem()
    except Exception as e: print(f"❌ Error crítico en Cine Golem: {e}")
    print("\n-----------------------------------------------------------")

    try: scrapear_embajadores() 
    except Exception as e: print(f"❌ Error crítico en Cine Embajadores: {e}") 

    # --- GRUPO 4: LOS GRANDES (MK2 & PAZ) ---
    print("\n-----------------------------------------------------------")
    try: scrapear_cine_paz()
    except Exception as e: print(f"❌ Error crítico en Cine Paz: {e}")
    print("\n-----------------------------------------------------------")
    
    try: scrapear_mk2_palacio_hielo()
    except Exception as e: print(f"❌ Error crítico en Palacio de Hielo: {e}")

    # --- GRUPO 5: MAINSTREAM (YELMO) ---
    print("\n-----------------------------------------------------------")
    try: scrapear_yelmo_ideal()          
    except Exception as e: print(f"❌ Error crítico en Yelmo Ideal: {e}")  

    print("\n-----------------------------------------------------------")  
    try: scrapear_cinesa()          
    except Exception as e: print(f"❌ Error crítico en Cinesa: {e}")

   
    # FIN CRONÓMETRO
    fin = time.time()
    tiempo_total = fin - inicio
    minutos = int(tiempo_total // 60)
    segundos = int(tiempo_total % 60)

    print("\n===========================================================")
    print(f"✅ ¡TODO LISTO! 🍿")
    print(f"⏱️ Tiempo total de ejecución: {minutos} min {segundos} s")
    print("===========================================================\n")

if __name__ == "__main__":
    lanzar_todo()