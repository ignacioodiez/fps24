export default function Header() {
  return (
    <div className="flex flex-col items-center xl:items-start text-center xl:text-left mb-8">
      {/* Contenedor Logo + Título */}
      <div className="flex flex-col md:flex-row items-center gap-4 md:gap-6">
        {/* Título de Texto */}
        <div>
          <h1 className="text-5xl md:text-7xl font-kanit font-black text-yellow-400 tracking-tighter drop-shadow-lg uppercase leading-none">
            MADRID<span className="text-white block md:inline md:ml-2">FPS24</span>
          </h1>
        </div>
      </div>

      {/* Subtítulo */}
      <p className="text-gray-400 text-sm md:text-base mt-4 font-raleway font-medium tracking-wide">
        Cartelera Madrid <span className="text-yellow-500 mx-1">•</span> Eventos Especiales y Sesiones Únicas
      </p>
    </div>
  );
}