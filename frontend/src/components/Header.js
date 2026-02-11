import Link from "next/link";

export default function Header() {
  return (
    <div className="w-full flex flex-col mb-8 text-center xl:text-left">
      
      {/* 1. w-full: Ocupa todo el ancho.
          2. justify-between: Título a la izquierda, Botón a la derecha.
          3. items-end: Alineado abajo.
      */}
      <div className="w-full flex flex-col md:flex-row items-center md:items-end justify-between gap-6 border-b border-white/10 pb-6">
        
        {/* --- IZQUIERDA: TÍTULO --- */}
        <div>
          <h1 className="text-5xl md:text-7xl font-kanit font-black text-yellow-400 tracking-tighter drop-shadow-lg uppercase leading-none">
              MADRID<span className="text-white block md:inline md:ml-2">FPS24</span>
          </h1>
        </div>

        {/* --- DERECHA: BOTÓN --- */}
        <Link 
          href="/cines" 
          className="flex items-center gap-2 px-5 py-2 rounded-full border border-gray-600 text-gray-300 hover:text-white hover:border-white hover:bg-gray-800 transition-all text-sm font-bold uppercase tracking-wide"
        >
        
           Salas y Precios
        </Link>

      </div>

      {/* --- SUBTÍTULO (Debajo) --- */}
      <p className="text-gray-400 text-sm md:text-base mt-4 font-raleway font-medium tracking-wide">
        Cartelera Madrid <span className="text-yellow-500 mx-1">•</span> Cartelera Actualizada <span className="text-yellow-500 mx-1">•</span> Sesiones Especiales
      </p>

    </div>
  );
}