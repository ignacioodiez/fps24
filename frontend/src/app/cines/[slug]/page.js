import Link from "next/link";
import { notFound } from "next/navigation";
import TodayHeader from "@/components/TodayHeader";
import CarteleraCine from "@/components/CarteleraCine";
import { Boton } from "@/components/SalasYPrecios";
import { ChipDato } from "@/components/FichaPelicula";

// Como /cines: ISR de 5 minutos
export const revalidate = 300;

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITIO = "https://fps24.es";

// notFound() solo con un 404 de la API. Cualquier otro fallo se lanza: Next no cachea la página y, en una
// regeneración, sigue sirviendo la última buena. fetch con las mismas opciones se comparte con generateMetadata.
async function leerCine(slug) {
  const res = await fetch(`${API}/cines/${encodeURIComponent(slug)}`, { next: { revalidate } });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`/cines/${slug}: HTTP ${res.status}`);
  return res.json();
}

// Los cines que conozca la API en el build; si no responde, ninguno y se generan bajo demanda
export async function generateStaticParams() {
  try {
    const res = await fetch(`${API}/cines`, { next: { revalidate } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).map(({ slug }) => ({ slug }));
  } catch (err) {
    console.error("generateStaticParams /cines/[slug]:", err);
    return [];
  }
}

export async function generateMetadata({ params }) {
  const { slug } = await params;
  const cine = await leerCine(slug);
  const lugar = [cine.direccion, cine.zona].filter(Boolean).join(", ");
  return {
    title: `${cine.nombre} (Madrid): cartelera, horarios y precios | fps24`,
    description: `Horarios de hoy y de los próximos días en ${cine.nombre}${lugar ? ` (${lugar})` : ""}, con precios, día del espectador y enlaces para comprar entradas.`,
    alternates: { canonical: `${SITIO}/cines/${cine.slug}` },
  };
}

// MovieTheater de schema.org solo con los datos que tenemos
const jsonLd = (cine) => ({
  "@context": "https://schema.org",
  "@type": "MovieTheater",
  name: cine.nombre,
  url: `${SITIO}/cines/${cine.slug}`,
  ...(cine.direccion && { address: { "@type": "PostalAddress", streetAddress: cine.direccion, addressLocality: "Madrid", addressCountry: "ES" } }),
  ...(cine.telefono && { telephone: `+34 ${cine.telefono}` }),
  ...(cine.lat != null && cine.lng != null && { geo: { "@type": "GeoCoordinates", latitude: cine.lat, longitude: cine.lng } }),
  ...(cine.web && { sameAs: cine.web }),
});

export default async function CinePage({ params }) {
  const { slug } = await params;
  const cine = await leerCine(slug);
  const telefono = cine.telefono?.replace(/\s+/g, "");

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      {/* "<" escapado: el JSON no puede cerrar el <script> */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(cine)).replace(/</g, "\\u003c") }} />
      <TodayHeader />

      <div className="max-w-6xl mx-auto px-4 md:px-6 space-y-8">
        <Link href="/cines" className="inline-block text-sm font-semibold text-muted hover:text-primary transition-colors rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">
          ← Todos los cines
        </Link>

        <header className="space-y-3">
          <h1 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground leading-none">{cine.nombre}</h1>
          <div className="flex flex-wrap gap-1.5">
            {cine.zona && <ChipDato>{cine.zona}</ChipDato>}
            {cine.tipo === "autor" && (
              <span className="text-xs px-2 py-0.5 rounded-md border bg-primary-soft text-primary border-primary">Autor</span>
            )}
            {cine.tipo === "comercial" && <ChipDato>Comercial</ChipDato>}
          </div>
          {cine.direccion && <p className="text-sm text-muted">{cine.direccion}</p>}
          <div className="flex flex-wrap gap-2">
            {cine.lat != null && cine.lng != null && (
              <Boton href={`https://www.google.com/maps/dir/?api=1&destination=${cine.lat},${cine.lng}`} nueva>Cómo llegar</Boton>
            )}
            {cine.web && <Boton href={cine.web} nueva>Web</Boton>}
            {telefono && <Boton href={`tel:+34${telefono}`}>{cine.telefono}</Boton>}
          </div>
        </header>

        <CarteleraCine cine={cine} />
      </div>
    </main>
  );
}
