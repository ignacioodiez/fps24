import sys
import traceback

print("🔍 INTENTANDO IMPORTAR APP.MAIN...")

try:
    from app.main import app
    print("✅ ¡ÉXITO! La app se importa bien. El error es de Uvicorn.")
except Exception:
    print("❌ ¡CAZADO! Aquí está el error real:")
    print("-" * 30)
    traceback.print_exc()
    print("-" * 30)