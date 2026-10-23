import Link from "next/link";
import Logo from "@/components/Logo";
import BotonEntrar from "@/components/BotonEntrar";

// showTitle=false donde la página ya tiene su propio h1 (un solo h1 por página)
export default function Header({ backdrop, showTitle = true }) {
  return (
    <header className="w-full flex flex-col mb-8 text-center xl:text-left">

      {/* Fondo a ancho completo: backdrop de la primera película de hoy, limpio (sin capa ni degradado). Sin backdrop queda blanco. */}
      <div
        className="w-full bg-background bg-cover bg-center"
        style={backdrop ? { backgroundImage: `url(${backdrop})` } : undefined}
      >
      {/* Mismo max-w y padding que el contenido de abajo para alinear logo y botón */}
      <div className="max-w-9xl mx-auto px-4 md:px-8 py-4 md:py-6 min-h-[180px] md:min-h-[260px] flex flex-col md:flex-row items-center md:items-end justify-between gap-4">

        {/* --- IZQUIERDA: LOGO --- */}
        <div className="bg-background rounded-xl px-2 py-1">
          {showTitle && <h1 className="sr-only">MadridFPS24</h1>}
          <Logo className="h-12 md:h-32" />
        </div>

        {/* --- DERECHA: BOTONES --- */}
        <div className="flex flex-wrap items-center justify-center gap-2 max-w-full">
        <Link 
          href="/cines" 
          className="flex items-center gap-2 px-5 py-2 rounded-full border border-line bg-background text-foreground hover:border-primary hover:text-primary transition-colors text-sm font-bold uppercase tracking-wide"
        >
        
           Salas y Precios
        </Link>
        <BotonEntrar />
        </div>

      </div>
      </div>

      {/* --- SUBTÍTULO (Debajo) --- */}
      <p className="max-w-9xl mx-auto w-full px-4 md:px-8 text-muted text-sm md:text-base mt-4 font-medium tracking-wide">
        Cartelera Madrid <span className="text-primary mx-1">•</span> Cartelera Actualizada <span className="text-primary mx-1">•</span> Sesiones Especiales
      </p>

    </header>
  );
}