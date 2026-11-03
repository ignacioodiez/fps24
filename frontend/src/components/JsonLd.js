import Link from "next/link";

export const SITIO = "https://fps24.es";

// <script> de JSON-LD; "<" escapado: el JSON no puede cerrar el <script>
export default function JsonLd({ datos }) {
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(datos).replace(/</g, "\\u003c") }} />;
}

// BreadcrumbList de schema.org: Cartelera (portada) > la página. ruta: "/cine-vose-madrid"
export const migas = (nombre, ruta) => ({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    { "@type": "ListItem", position: 1, name: "Cartelera", item: SITIO },
    { "@type": "ListItem", position: 2, name: nombre, item: `${SITIO}${ruta}` },
  ],
});

// Las mismas migas, visibles (como "← Todos los cines" en la ficha de un cine)
export function Migas({ nombre }) {
  return (
    <nav aria-label="Migas de pan" className="text-sm font-semibold text-muted">
      <Link href="/" className="hover:text-primary transition-colors rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary">Cartelera</Link>
      <span aria-hidden="true" className="mx-2">/</span>
      <span aria-current="page" className="text-foreground">{nombre}</span>
    </nav>
  );
}
