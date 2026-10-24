import TodayHeader from "@/components/TodayHeader";
import EditarPerfil from "@/components/Perfil";

export const metadata = {
  title: "Editar mi perfil - FPS24",
  description: "Tu nombre de usuario, tu bio y quién puede ver tu perfil y tu diario.",
  robots: { index: false, follow: false },
};

export default function EditarPerfilPage() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <EditarPerfil />
    </main>
  );
}
