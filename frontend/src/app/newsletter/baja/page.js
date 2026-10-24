import Link from "next/link";
import TodayHeader from "@/components/TodayHeader";

// Aquí redirige GET /newsletter/baja de la API (?error=token si el enlace no vale)
export const metadata = { title: "Baja de la newsletter - FPS24", robots: { index: false, follow: false } };

export default async function BajaPage({ searchParams }) {
  const { error } = await searchParams;
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <div className="max-w-xl mx-auto px-4 md:px-6 text-center space-y-6">
        <h2 className="text-4xl md:text-5xl font-black font-display uppercase text-primary">
          {error ? "Enlace no válido" : "Te has dado de baja"}
        </h2>
        <p className="text-muted text-lg">
          {error
            ? "No hemos encontrado ninguna suscripción con este enlace. Si sigues recibiendo correos, escríbenos y te damos de baja a mano."
            : "No te enviaremos más correos de «Esta semana en Madrid». Si cambias de idea, puedes volver a suscribirte cuando quieras."}
        </p>
        <Link href={error ? "/privacidad" : "/newsletter"} className="inline-block px-4 py-2 border border-line text-sm font-bold text-foreground hover:border-primary hover:text-primary transition-colors">
          {error ? "Contacto y privacidad" : "Volver a suscribirme"}
        </Link>
      </div>
    </main>
  );
}
