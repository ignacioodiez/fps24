# backend/cron_job.py
import logging
from app.database import SessionLocal
from app.scrapers.cines.cine_estudio import scrapear_cine_estudio
from app.scrapers.cines.cine_paz import scrapear_cine_paz
from app.scrapers.cines.cineteca import scrapear_cineteca
from app.scrapers.cines.dore import scrapear_dore
from app.scrapers.cines.embajadores import scrapear_embajadores
from app.scrapers.cines.equis import scrapear_equis
from app.scrapers.cines.golem  import scrapear_golem
from app.scrapers.cines.mk2_palacio_hielo import scrapear_mk2_palacio_hielo
from app.scrapers.cines.renoir_plazaesp import scrapear_renoir_plazaesp
from app.scrapers.cines.renoir_princesa import scrapear_renoir_princesa
from app.scrapers.cines.renoir_retiro import scrapear_renoir_retiro
from app.scrapers.cines.verdi import scrapear_verdi
from app.scrapers.cines.yelmo_ideal import scrapear_yelmo_ideal
  
# Configuración de logs para ver qué pasa en la consola de Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 INICIANDO ACTUALIZACIÓN DIARIA DE CARTELERA...")
    db = SessionLocal()
    
    try:
        # 1. RENOIR
        logger.info("🍿 Actualizando Renoir...")
        scrapear_renoir_plazaesp(db)
        scrapear_renoir_princesa(db)
        scrapear_renoir_retiro(db)
        
        # 2. YELMO
        logger.info("🍿 Actualizando Yelmo...")
        scrapear_yelmo_ideal(db)

        # 3. GOLEM
        logger.info("🍿 Actualizando Golem...")
        scrapear_golem(db)

        # 4. CINE ESTUDIO
        logger.info("🍿 Actualizando Cine Estudio..."   )
        scrapear_cine_estudio(db)

        # 5. CINE PAZ
        logger.info("🍿 Actualizando Cine Paz...")
        scrapear_cine_paz(db)

        # 6. CINETECA
        logger.info("🍿 Actualizando Cineteca...")
        scrapear_cineteca(db)

        # 7. DORE
        logger.info("🍿 Actualizando Dore...")
        scrapear_dore(db)

        # 8. EMBAJADORES
        logger.info("🍿 Actualizando Embajadores...")
        scrapear_embajadores(db)

        # 9. EQUIS
        logger.info("🍿 Actualizando Equis...")
        scrapear_equis(db)

        # 10. MK2 PALACIO HIELO
        logger.info("🍿 Actualizando MK2 Palacio Hielo...")
        scrapear_mk2_palacio_hielo(db)

        #11. VERDI
        logger.info("🍿 Actualizando Verdi...")
        scrapear_verdi(db)

        
        
        logger.info("✅ TODO ACTUALIZADO CORRECTAMENTE. HASTA MAÑANA.")
        
    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO EN EL CRON JOB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()