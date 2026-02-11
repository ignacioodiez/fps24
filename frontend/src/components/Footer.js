import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-black border-t border-white/5 py-12 mt-auto">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between gap-10">
        
        {/* 1. LA MARCA */}
        <div className="max-w-sm">
            <h3 className="text-3xl font-black font-kanit tracking-tighter text-yellow-500 mb-4">
                FPS24
            </h3>
            <p className="text-white text-sm leading-relaxed">
                La cartelera actualizada de Madrid. Recopilamos las sesiones de los cines, 
                filmotecas y salas VOSE en una única plataforma.
            </p>
        </div>

        {/* 2. ENLACES RÁPIDOS */}
        <div>
            <h4 className="font-bold text-white mb-4 uppercase tracking-wider text-xs">Navegación</h4>
            <ul className="space-y-2 text-sm">
                <li>
                    <Link href="/" className="text-white hover:text-yellow-400 transition-colors">
                        Inicio
                    </Link>
                </li>
                <li>
                    <a href="mailto:ignacio.diez.vergara@gmail.com" className="text-white hover:text-yellow-400 transition-colors">
                        Contacto
                    </a>
                </li>
                 {/* Aquí pondremos el Ko-fi luego */}
            </ul>
        </div>

        {/* 3. CRÉDITOS */}
        <div>
            <h4 className="font-bold text-white mb-4 uppercase tracking-wider text-xs">El Autor</h4>
            <p className="text-white text-sm mb-2">
                 Ignacio Díez Vergara 🎬 <br/>
            </p>
            <li>
                    <a href="https://www.linkedin.com/in/ignacio-d%C3%ADez-vergara/" className="text-white hover:text-yellow-400 transition-colors">
                        Linkedin
                    </a>
                </li>
           
        </div>

      </div>
      
      {/* COPYRIGHT */}
      <div className="max-w-7xl mx-auto px-6 mt-12 pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center text-xs text-white">
        <p>© {new Date().getFullYear()} FPS24. Todos los derechos reservados.</p>
        <p>Los pósters e imágenes son propiedad de sus distribuidoras.</p>
        <p>Las notas de las películas son asignadas por TMDB.</p>
      </div>
    </footer>
  );
}