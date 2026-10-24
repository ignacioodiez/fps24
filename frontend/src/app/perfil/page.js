import TodayHeader from "@/components/TodayHeader";
import { IrAMiPerfil } from "@/components/Perfil";

export const metadata = {
  title: "Mi perfil - FPS24",
  robots: { index: false, follow: false },
};

// Solo redirige: a /u/<mi usuario> o a /perfil/editar. "Mi perfil" de la barra ya apunta allí cuando se sabe.
export default function PerfilPage() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <IrAMiPerfil />
    </main>
  );
}
