import Link from "next/link";

// Atajos de la portada a las páginas con intención de búsqueda. Componente de servidor: app/page.js se lo pasa a
// Cartelera (cliente) ya pintado, así que los enlaces van en el HTML sin depender de JavaScript.
// Estilo de los chips inactivos de los filtros (ChipFiltro).
const CHIP = "px-3 py-1.5 rounded-full border border-line bg-background text-foreground text-xs font-bold hover:border-primary hover:text-primary transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";

export default function AtajosPortada() {
  return (
    <nav aria-label="Atajos" className="flex flex-wrap justify-center xl:justify-start gap-2">
      <Link href="/cine-vose-madrid" className={CHIP}>Solo VOSE</Link>
      <Link href="/dia-del-espectador-madrid" className={CHIP}>Día del espectador</Link>
    </nav>
  );
}
