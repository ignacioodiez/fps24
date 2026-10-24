import TodayHeader from "@/components/TodayHeader";
import { SiSoyYo } from "@/components/Perfil";

// La misma pantalla para un perfil privado y uno que no existe: no se distingue cuál de los dos es.
// Solo el dueño, con su sesión, ve aquí su perfil privado (SiSoyYo lo comprueba con /me/perfil en el navegador).
export const metadata = { title: "Perfil - FPS24", robots: { index: false, follow: false } };

export default function PerfilNoDisponible() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <SiSoyYo esperar>
        <div className="max-w-3xl mx-auto px-4 md:px-6 py-12 text-center">
          <p className="text-xl text-foreground">Este perfil no existe o es privado.</p>
        </div>
      </SiSoyYo>
    </main>
  );
}
