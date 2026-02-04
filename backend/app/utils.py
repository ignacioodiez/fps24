from datetime import datetime

def es_programacion_especial(cine: str, titulo: str, anio: int | None) -> bool:
    """
    Decide si es especial por Cine, Título o AÑO.
    """
    # 1. CRITERIO DE AÑO (Clásicos)
    # Si la peli tiene año y es anterior a 2023 (hace más de 2-3 años), es 'Especial'
    anio_actual = datetime.now().year
    if anio and anio < (anio_actual - 2): # Ej: < 2024
        return True

    titulo_upper = titulo.upper()
    cine_upper = cine.upper()

    # 2. CINES SIEMPRE ESPECIALES
    cines_speciales = ["CINE DORÉ", "FILMOTECA", "CÍRCULO DE BELLAS ARTES", "CINETECA", "SALA BERLANGA"]
    if any(c in cine_upper for c in cines_speciales):
        return True

    # 3. KEYWORDS EN EL TÍTULO
    keywords = [
        "ÓPERA", "OPERA", "BALLET", "DOCUMENTAL", "COLOQUIO", "PRESENTACIÓN",
        "CICLO", "REESTRENO", "ANIVERSARIO", "CONCIERTO", "RECITAL", 
        "EN DIRECTO", "DIFERIDO", "FESTIVAL", "CLÁSICOS", "PROYECCIÓN ESPECIAL",
        "MET OPERA", "ROYAL BALLET"
    ]
    keywords_seguras = [k for k in keywords if k != "VOSE"]
    
    if any(k in titulo_upper for k in keywords_seguras):
        return True

    return False