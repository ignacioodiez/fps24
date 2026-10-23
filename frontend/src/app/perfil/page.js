import TodayHeader from "@/components/TodayHeader";
import Perfil from "@/components/Perfil";

export const metadata = {
  title: "Mi perfil - FPS24",
  description: "Tu diario de películas vistas en los cines independientes de Madrid.",
  robots: { index: false, follow: false },
};

export default function PerfilPage() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <Perfil />
    </main>
  );
}
