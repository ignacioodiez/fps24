import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-background border-t border-line py-12 mt-auto">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between gap-10">
        
        {/* 1. LA MARCA */}
        <div className="max-w-sm">
            <h3 className="text-3xl font-black font-display tracking-tighter text-primary mb-4">
                FPS24
            </h3>
            <p className="text-muted text-sm leading-relaxed">
                La cartelera actualizada de Madrid. Recopilamos las sesiones de los cines, 
                filmotecas y salas VOSE en una única plataforma.
            </p>
        </div>

        {/* 2. ENLACES RÁPIDOS */}
        <div>
            <h4 className="font-bold text-foreground mb-4 uppercase tracking-wider text-xs">Navegación</h4>
            <ul className="space-y-2 text-sm">
                <li>
                    <Link href="/" className="text-muted hover:text-primary transition-colors">
                        Inicio
                    </Link>
                </li>
                <li>
                    <Link href="/cines" className="text-muted hover:text-primary transition-colors">
                        Cines
                    </Link>
                </li>
                <li>
                    <Link href="/estrenos" className="text-muted hover:text-primary transition-colors">
                        Estrenos
                    </Link>
                </li>
                <li>
                    <Link href="/especiales" className="text-muted hover:text-primary transition-colors">
                        Especiales
                    </Link>
                </li>
                <li>
                    <a href="mailto:ignacio.diez.vergara@gmail.com" className="text-muted hover:text-primary transition-colors">
                        Contacto
                    </a>
                </li>
                <li>
                    <Link href="/privacidad" className="text-muted hover:text-primary transition-colors">
                        Privacidad
                    </Link>
                </li>
                 {/* Aquí pondremos el Ko-fi luego */}
            </ul>
        </div>

        {/* 3. CRÉDITOS */}
        <div>
            <h4 className="font-bold text-foreground mb-4 uppercase tracking-wider text-xs">El Autor</h4>
            <p className="text-muted text-sm mb-2">
                 Ignacio Díez Vergara <br/>
            </p>
            <li>
                    <a href="https://www.linkedin.com/in/ignacio-d%C3%ADez-vergara/" className="text-muted hover:text-primary transition-colors">
                        Linkedin
                    </a>
                </li>
           
        </div>

      </div>
      
      {/* COPYRIGHT */}
      <div className="max-w-7xl mx-auto px-6 mt-12 pt-8 border-t border-line flex flex-col md:flex-row md:flex-wrap justify-between items-center gap-2 text-center text-xs text-muted">
        <p>© {new Date().getFullYear()} FPS24. Todos los derechos reservados.</p>
        <p>Los pósters e imágenes son propiedad de sus distribuidoras.</p>
        <p>Las notas de las películas son asignadas por TMDB.</p>
        <p>
          Este producto usa la API de{" "}
          <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer" className="hover:text-primary underline">TMDB</a>{" "}
          pero no está respaldado ni certificado por TMDB.
        </p>
      </div>
    </footer>
  );
}