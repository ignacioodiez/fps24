"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";

// --- AYUDANTES ---
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
};

const formatTime = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

export default function MovieDetail({ params }) {
  // Desempaquetamos los params (Next.js 15+)
  const { id } = use(params);
  const router = useRouter();
  
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // ⬇️ AQUÍ ESTÁ EL CAMBIO IMPORTANTE ⬇️
    // Si estamos en Vercel, usa la variable de entorno. Si no, usa localhost.
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    fetch(`${apiUrl}/pelicula/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Error fetching movie");
        return res.json();
      })
      .then((data) => {
        setMovie(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error cargando la peli:", err);
        setLoading(false);
      });
  }, [id]);

  if (loading) return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Cargando...</div>;
  if (!movie) return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Película no encontrada</div>;

  // AGRUPAR PASES POR DÍA
  const passesByDate = movie.pases.reduce((acc, pase) => {
    const dateKey = new Date(pase.fecha_hora).toDateString(); 
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(pase);
    return acc;
  }, {});

  const sortedDates = Object.entries(passesByDate).sort(
    (a, b) => new Date(a[1][0].fecha_hora) - new Date(b[1][0].fecha_hora)
  );

  return (
    <main className="min-h-screen bg-gray-900 text-white font-sans pb-20">
      
      {/* 1. HERO SECTION (BACKDROP) */}
      <div className="relative h-[50vh] w-full overflow-hidden">
        {/* Imagen de Fondo */}
        <div 
            className="absolute inset-0 bg-cover bg-center"
            style={{ 
                backgroundImage: `url(${movie.backdrop_url || movie.poster_url})`,
                filter: movie.backdrop_url ? "brightness(0.6)" : "blur(20px) brightness(0.4)" 
            }}
        />
        {/* Degradado para texto */}
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/60 to-transparent" />

        <button 
            onClick={() => router.back()} 
            className="absolute top-6 left-6 z-50 bg-black/50 backdrop-blur-md p-2 rounded-full hover:bg-white/20 transition cursor-pointer group border border-white/10"
        >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6 text-white group-hover:text-yellow-400 transition-colors">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
        </button>

        {/* INFO PRINCIPAL */}
        <div className="absolute bottom-0 left-0 w-full p-6 md:p-12 flex flex-col md:flex-row gap-8 items-end z-10">
            {/* Póster Flotante */}
            <img 
                src={movie.poster_url} 
                alt={movie.titulo} 
                className="hidden md:block w-48 rounded-xl shadow-2xl border-2 border-white/10"
            />
            
            <div className="flex-1 mb-2">
                <h1 className="text-4xl md:text-6xl font-black font-kanit uppercase leading-none drop-shadow-lg text-yellow-400">
                    {movie.titulo}
                </h1>
                <h2 className="text-xl text-gray-300 mt-2 font-raleway">{movie.titulo_original}</h2>
                
                {/* Metadatos */}
                <div className="flex flex-wrap items-center gap-4 mt-4 text-sm font-semibold tracking-wide">
                    {movie.anio && (
                        <span className="bg-white/10 px-3 py-1 rounded backdrop-blur-sm border border-white/10">
                            {movie.anio}
                        </span>
                    )}
                    {movie.duracion > 0 && (
                        <span className="bg-white/10 px-3 py-1 rounded backdrop-blur-sm border border-white/10 flex items-center gap-1">
                            ⏱️ {movie.duracion} min
                        </span>
                    )}
                    {movie.nota_tmdb > 0 && (
                        <span className="text-yellow-400 flex items-center gap-1">
                            ⭐ {movie.nota_tmdb.toFixed(1)}
                        </span>
                    )}
                    {/* Letterboxd Link */}
                    {movie.tmdb_id && (
                        <a 
                            href={`https://letterboxd.com/tmdb/${movie.tmdb_id}`} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-green-400 hover:text-green-300 transition-colors"
                        >
                            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 4.364c1.76 0 3.273 1.513 3.273 3.273S13.76 10.91 12 10.91s-3.273-1.514-3.273-3.273S10.24 4.364 12 4.364zM6.545 13.818c0-1.76 1.514-3.273 3.273-3.273s3.273 1.514 3.273 3.273-1.513 3.273-3.273 3.273-3.273-1.513-3.273-3.273zm10.91 3.273c-1.76 0-3.273-1.513-3.273-3.273s1.513-3.273 3.273-3.273 3.273 1.513 3.273 3.273-1.513 3.273-3.273 3.273z"/></svg>
                            Letterboxd
                        </a>
                    )}
                </div>
            </div>
        </div>
      </div>

      {/* 2. CONTENIDO (SINOPSIS Y HORARIOS) */}
      <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-3 gap-12">
        
        {/* Columna Izquierda: Sinopsis y Géneros */}
        <div className="lg:col-span-1 space-y-6">
            <div>
                <h3 className="text-xl font-bold text-yellow-500 mb-2 uppercase">Sinopsis</h3>
                <p className="text-gray-300 leading-relaxed text-lg">
                    {movie.sinopsis || "No hay sinopsis disponible."}
                </p>
            </div>
            {movie.generos && (
                <div>
                    <h3 className="text-sm font-bold text-gray-500 mb-2 uppercase">Géneros</h3>
                    <div className="flex flex-wrap gap-2">
                        {movie.generos.split(",").map((g, i) => (
                            <span key={i} className="text-xs border border-gray-600 px-2 py-1 rounded-full text-gray-400">
                                {g.trim()}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>

        {/* Columna Derecha: HORARIOS POR DÍA (Calendario) */}
        <div className="lg:col-span-2">
            <h3 className="text-2xl font-bold text-white mb-6 border-b border-gray-700 pb-2 flex items-center gap-2">
                🎟️ Próximas Sesiones
            </h3>

            <div className="space-y-8">
                {sortedDates.map(([dateKey, sessions]) => (
                    <div key={dateKey} className="animate-fade-in-up">
                        {/* Fecha Cabecera */}
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-2 h-8 bg-yellow-500 rounded-full"></div>
                            <h4 className="text-xl font-semibold capitalize text-gray-200">
                                {formatDate(sessions[0].fecha_hora)}
                            </h4>
                        </div>

                        {/* Grid de Sesiones */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-5 border-l border-gray-800 ml-1">
                            {sessions.map((sesion) => (
                                <a 
                                    key={sesion.id}
                                    href={sesion.link_compra}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="bg-gray-800 hover:bg-gray-700 p-4 rounded-xl border border-gray-700 hover:border-yellow-500/50 transition-all group flex justify-between items-center"
                                >
                                    <div>
                                        <div className="text-yellow-400 font-bold text-sm uppercase tracking-wider mb-1">
                                            {sesion.cine}
                                        </div>
                                        <div className="text-xs text-gray-400">
                                            {sesion.sala || "Sala estándar"}
                                        </div>
                                    </div>
                                    
                                    <div className="flex items-center gap-3">
                                        {sesion.idioma === 'VOSE' && (
                                            <span className="text-[10px] font-bold bg-black/40 px-1.5 py-0.5 rounded text-gray-400 border border-gray-600">
                                                VO
                                            </span>
                                        )}
                                        <div className="bg-gray-900 px-3 py-1 rounded-lg text-lg font-bold text-white group-hover:text-yellow-400 transition-colors">
                                            {formatTime(sesion.fecha_hora)}
                                        </div>
                                    </div>
                                </a>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>

      </div>
    </main>
  );
}