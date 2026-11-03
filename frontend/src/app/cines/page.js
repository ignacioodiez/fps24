import TodayHeader from "@/components/TodayHeader";
import SalasYPrecios from "@/components/SalasYPrecios";
import { hoyMadrid } from "@/lib/fechasMadrid";

export const metadata = {
  title: "Cines de Madrid: mapa, precios y sesiones cerca de ti | fps24",
  description: "Mapa de los cines de Madrid con los precios de hoy, el día del espectador y las sesiones que empiezan cerca de ti. Elige sala, horario y cómo llegar.",
};

// "de las 22 salas"; sin cines (error o lista vacía), sin cifra
const deLasSalas = (n) => (n === 1 ? " de la única sala" : n > 1 ? ` de las ${n} salas` : "");

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

export default async function CinesPage() {
  const cines = await leerCines();

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader showTitle={false} />

      <div className="max-w-6xl mx-auto px-4 md:px-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground mb-4">
            Cines de <span className="text-primary">Madrid</span>
          </h1>
          <p className="text-muted text-lg max-w-2xl mx-auto">
            Mapa, sesiones cerca de ti y precios{deLasSalas(cines?.length)}
          </p>
        </div>

        {/* Hoy en Madrid, el mismo en servidor y cliente. shortcut: con la caché de 5 min puede ir hasta 5 min tarde a medianoche */}
        {cines ? (
          <SalasYPrecios cines={cines} fechaHoy={hoyMadrid()} />
        ) : (
          <p className="text-center text-muted py-16">No se han podido cargar los cines. Vuelve a intentarlo en unos minutos.</p>
        )}
      </div>
    </main>
  );
}
