import TodayHeader from "@/components/TodayHeader";
import SalasYPrecios from "@/components/SalasYPrecios";

export const metadata = {
  title: "Cines y Precios - FPS24",
  description: "Consulta los precios y el día del espectador de los cines independientes de Madrid.",
};

// Se regenera cada 5 minutos (ISR): HTML con los cines para buscadores, datos de hoy casi al día
export const revalidate = 300;

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function leerCines() {
  try {
    const res = await fetch(`${API}/cines`, { next: { revalidate } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("Error loading cines:", err);
    return null;
  }
}

// Día de la semana de hoy en Madrid ("Jueves"), el mismo para el HTML del servidor y el cliente (sin desajustes
// al hidratar). shortcut: con la caché de 5 min puede ir hasta 5 min tarde a medianoche, igual que sesiones_hoy.
const diaHoyMadrid = () => {
  const dia = new Intl.DateTimeFormat("es-ES", { weekday: "long", timeZone: "Europe/Madrid" }).format(new Date());
  return dia.charAt(0).toUpperCase() + dia.slice(1);
};

export default async function CinesPage() {
  const cines = await leerCines();

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />

      <div className="max-w-6xl mx-auto px-4 md:px-6">
        <div className="text-center mb-8">
          <h2 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground mb-4">
            Salas y <span className="text-primary">Precios</span>
          </h2>
          <p className="text-muted text-lg max-w-2xl mx-auto">
            Guía rápida para saber cuánto cuesta ir al cine en Madrid y qué día es más barato en cada sala.
          </p>
        </div>

        {cines ? (
          <SalasYPrecios cines={cines} diaHoy={diaHoyMadrid()} />
        ) : (
          <p className="text-center text-muted py-16">No se han podido cargar los cines. Vuelve a intentarlo en unos minutos.</p>
        )}
      </div>
    </main>
  );
}
