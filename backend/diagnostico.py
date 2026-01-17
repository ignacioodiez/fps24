from playwright.sync_api import sync_playwright

def espiar_web():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("🕵️‍♂️ Entrando en modo espía...")
        page.goto("https://entradasfilmoteca.sacatuentrada.es/")
        
        # Buscamos algo que sabemos que existe seguro: el texto de la fecha
        try:
            # Esperamos a que aparezca cualquier texto que diga "Fecha y Hora"
            page.wait_for_selector("text=Fecha y Hora", timeout=10000)
            print("✅ He encontrado una película. Analizando su estructura...")

            # Seleccionamos ese elemento
            elemento_fecha = page.query_selector("text=Fecha y Hora")
            
            # Subimos 3 niveles hacia arriba para ver la "caja" completa
            # (Padre -> Abuelo -> Bisabuelo)
            padre = elemento_fecha.evaluate_handle("el => el.parentElement")
            abuelo = padre.evaluate_handle("el => el.parentElement")
            bisabuelo = abuelo.evaluate_handle("el => el.parentElement")
            
            print("\n--- AQUÍ TIENES EL CÓDIGO DE UNA CAJA DE PELÍCULA ---")
            print(bisabuelo.inner_html())
            print("-----------------------------------------------------\n")
            
        except Exception as e:
            print(f"❌ Algo falló: {e}")
        
        browser.close()

if __name__ == "__main__":
    espiar_web()