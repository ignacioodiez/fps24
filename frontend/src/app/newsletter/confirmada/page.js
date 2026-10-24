import Link from "next/link";
import TodayHeader from "@/components/TodayHeader";

// Aquí redirige GET /newsletter/confirmar de la API (?error=token si el enlace no vale)
export const metadata = { title: "Suscripción confirmada - FPS24", robots: { index: false, follow: false } };

export default async function ConfirmadaPage({ searchParams }) {
  const { error } = await searchParams;
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <div className="max-w-xl mx-auto px-4 md:px-6 text-center space-y-6">
        <h2 className="text-4xl md:text-5xl font-black font-display uppercase text-primary">
          {error ? "Enlace no válido" : "¡Suscripción confirmada!"}
        </h2>
        <p className="text-muted text-lg">
          {error
            ? "Este enlace ya se ha usado o no es correcto. Si ya confirmaste, no tienes que hacer nada; si no, vuelve a suscribirte."
            : "Desde el próximo lunes recibirás «Esta semana en Madrid» a las 16:00. Puedes darte de baja con un clic en cada correo."}
        </p>
        <Link href={error ? "/newsletter" : "/"} className="inline-block px-4 py-2 bg-primary text-white text-sm font-bold hover:opacity-90 transition-opacity">
          {error ? "Volver a suscribirme" : "Ver la cartelera"}
        </Link>
      </div>
    </main>
  );
}
