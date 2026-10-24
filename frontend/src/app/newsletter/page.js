import TodayHeader from "@/components/TodayHeader";
import FormNewsletter from "@/components/FormNewsletter";

export const metadata = {
  title: "Newsletter - FPS24",
  description: "Esta semana en Madrid: cada lunes, los estrenos y las sesiones especiales de los cines de Madrid en tu correo.",
};

export default function NewsletterPage() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <div className="max-w-xl mx-auto px-4 md:px-6">
        <div className="text-center mb-10">
          <h2 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground mb-4">
            <span className="text-primary">Newsletter</span>
          </h2>
          <p className="text-muted text-lg">
            Los lunes a las 16:00: los estrenos del viernes, las sesiones especiales de la semana y la mejor sesión en VOSE de cada una.
          </p>
        </div>
        <div className="border border-line bg-surface p-6">
          <FormNewsletter />
        </div>
      </div>
    </main>
  );
}
