import { CINES_INFO } from "@/data/cines";
import Link from "next/link";

export const metadata = {
  title: "Cines y Precios - FPS24",
  description: "Consulta los precios y el día del espectador de los cines independientes de Madrid.",
};

export default function CinesPage() {
  return (
    <main className="min-h-screen bg-gray-900 text-white pb-20 font-sans">
      
      {/* --- 1. BARRA DE NAVEGACIÓN SUPERIOR --- */}
      <nav className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-4">
        
        {/* LOGO FPS24 (Click para ir al Inicio) */}
        <Link href="/" className="group">
            <h1 className="text-3xl md:text-4xl font-kanit font-black text-yellow-400 tracking-tighter uppercase leading-none transition-transform group-hover:scale-105">
                MADRID<span className="text-white ml-2">FPS24</span>
            </h1>
        </Link>

        {/* BOTÓN VOLVER */}
       
      </nav>

      {/* --- 2. CABECERA DE LA PÁGINA --- */}
      <div className="bg-black/20 border-y border-white/5 py-12 md:py-16 mb-12">
        
        {/* Contenedor centralizado (para alinear con el grid de abajo) */}
        <div className="max-w-6xl mx-auto px-6">
          
          {/* BOTÓN ALINEADO A LA IZQUIERDA */}
          <div className="flex justify-start mb-6"> {/* justify-start lo manda a la izquierda */}
            <Link 
              href="/" 
              // Añadido 'w-fit' para que no ocupe todo el ancho
              className="w-fit flex items-center gap-2 px-5 py-2 rounded-full border border-gray-600 text-gray-300 hover:text-white hover:border-white hover:bg-gray-800 transition-all text-sm font-bold uppercase tracking-wide"
            >
              <span>←</span> Volver a Cartelera
            </Link>
          </div>

          {/* TÍTULO Y DESCRIPCIÓN (Centrados) */}
          <div className="text-center">
            <h2 className="text-4xl md:text-6xl font-black font-kanit uppercase text-white mb-4 drop-shadow-lg">
              Salas y <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-yellow-600">Precios</span>
            </h2>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto font-raleway">
              Guía rápida para saber cuánto cuesta ir al cine en Madrid y qué día es más barato en cada sala.
            </p>
          </div>

        </div>
      </div>

      {/* --- 3. GRID DE CINES --- */}
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            
            {CINES_INFO.map((cine) => (
                <div key={cine.id} className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden hover:border-yellow-500/50 transition-all group shadow-lg flex flex-col">
                    
                    {/* Nombre del Cine */}
                    <div className="p-6 border-b border-gray-700 bg-gray-800 group-hover:bg-gray-750 transition-colors">
                        <h3 className="text-xl font-bold font-kanit text-white mb-1">
                            {cine.nombre}
                        </h3>
                        <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
                             📍 {cine.direccion}
                        </div>
                    </div>

                    {/* Precios */}
                    <div className="p-6 space-y-5 flex-grow">
                        
                        {/* Entrada Normal */}
                        <div className="flex justify-between items-start">
                            <span className="text-gray-400 text-sm font-medium">Entrada Normal</span>
                            <span className="text-lg font-bold text-white text-right leading-tight">{cine.precio_normal}</span>
                        </div>

                        {/* Separador */}
                        <div className="h-px bg-gray-700/50 w-full"></div>

                        {/* Día del Espectador (Destacado) */}
                        <div className="bg-gradient-to-br from-gray-700/50 to-gray-800 border border-gray-600 rounded-xl p-4 relative overflow-hidden">
                            {/* Brillo decorativo */}
                            <div className="absolute top-0 right-0 w-16 h-16 bg-yellow-500/10 rounded-full blur-xl -mr-8 -mt-8"></div>

                            <div className="flex justify-between items-center mb-2 relative z-10">
                                <span className="text-yellow-400 text-[10px] font-black uppercase tracking-widest border border-yellow-500/30 px-2 py-0.5 rounded-full bg-yellow-500/10">
                                    Día del Espectador
                                </span>
                            </div>
                            <div className="flex justify-between items-end relative z-10">
                                <span className="text-gray-200 font-bold text-sm">{cine.dia_espectador}</span>
                                <span className="text-2xl font-black text-yellow-400">{cine.precio_espectador}</span>
                            </div>
                        </div>

                        {/* Notas extra */}
                        {cine.notas && (
                            <p className="text-xs text-gray-500 italic leading-relaxed border-t border-gray-700/50 pt-4">
                                ℹ️ {cine.notas}
                            </p>
                        )}
                    </div>

                    {/* Botón Web (Pie de tarjeta) */}
                    <div className="p-4 bg-black/20 border-t border-gray-700">
                        <a 
                            href={cine.web} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="block w-full text-center py-2.5 rounded-lg bg-gray-700 hover:bg-white hover:text-black text-sm text-gray-300 font-bold transition-all"
                        >
                            Visitar Web Oficial ↗
                        </a>
                    </div>

                </div>
            ))}

        </div>
      </div>

    </main>
  );
}