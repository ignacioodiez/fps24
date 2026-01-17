import time
import sys
import os

# Aseguramos que Python encuentre los módulos de la app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- IMPORTAMOS TUS AGENTES ---
from app.scrapers.cines.dore import scrapear_dore
from app.scrapers.cines.equis import scrapear_equis
from app.scrapers.cines.cineteca import scrapear_cineteca
from app.scrapers.cines.renoir_princesa import scrapear_renoir_princesa
from app.scrapers.cines.renoir_plazaesp import scrapear_renoir_plazaesp
from app.scrapers.cines.renoir_retiro import scrapear_renoir_retiro
from app.scrapers.cines.verdi import scrapear_verdi

def lanzar_todo():
    print("\n🚀 INICIANDO PROTOCOLO 'MADRID INDIE' - EXTRACCIÓN MASIVA")
    print("===========================================================\n")

    # --- 1. LOS CLÁSICOS & ALTERNATIVOS ---
    try:
        scrapear_dore()
    except Exception as e:
        print(f"❌ Error crítico en Doré: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_equis()
    except Exception as e:
        print(f"❌ Error crítico en Sala Equis: {e}")

    print("\n-----------------------------------------------------------")

    try:
        scrapear_cineteca()
    except Exception as e:
        print(f"❌ Error crítico en Cineteca: {e}")

    # --- 2. LOS RENOIR (VOSE COMERCIAL) ---
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

    # --- 3. LA JOYA DE LA CORONA ---
    print("\n-----------------------------------------------------------")

    try:
        scrapear_verdi()
    except Exception as e:
        print(f"❌ Error crítico en Cines Verdi: {e}")

    print("\n===========================================================")
    print("✅ ¡TODO TERMINADO! La base de datos está calentita. 🍿")
    print("===========================================================\n")

if __name__ == "__main__":
    lanzar_todo()