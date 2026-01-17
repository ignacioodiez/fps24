from playwright.sync_api import sync_playwright

def debug_equis():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Lo vemos en directo
        page = browser.new_page()
        
        print("🕵️‍♂️ Entrando a la Sala Equis...")
        page.goto("https://salaequis.es/taquilla/")
        
        # Esperamos bastante para asegurar que carga todo
        page.wait_for_timeout(5000)
        
        # Guardamos lo que ve el robot en un archivo
        content = page.content()
        
        with open("debug_salaequis.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("📸 ¡Foto tomada! He guardado el código en 'debug_salaequis.html'")
        
        # Si hay IFRAMES, también los chivamos
        for frame in page.frames:
            print(f"🖼️ Detectado marco (frame): {frame.url}")

        browser.close()

if __name__ == "__main__":
    debug_equis()