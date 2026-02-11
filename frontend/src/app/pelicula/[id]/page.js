"use client";

import { useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import LiteYouTubeEmbed from 'react-lite-youtube-embed'; // <--- IMPORTANTE
import 'react-lite-youtube-embed/dist/LiteYouTubeEmbed.css'; // <--- ESTILOS YOUTUBE

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
  const { id } = use(params);
  const router = useRouter();
  
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // NUEVO ESTADO: ¿Agrupar por cine?
  const [groupByCinema, setGroupByCinema] = useState(false);

  useEffect(() => {
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
        console.error(err);
        setLoading(false);
      });
  }, [id]);

  if (loading) return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Cargando...</div>;
  if (!movie) return <div className="min-h-screen bg-gray-900 flex items-center justify-center text-white">Película no encontrada</div>;

  // 1. FILTRO ANTI-AYER (EL PORTERO 🛡️)
  const futurePases = movie.pases.filter((pase) => {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0); 
    const fechaPase = new Date(pase.fecha_hora);
    return fechaPase >= hoy;
  });

  // 2. AGRUPAR POR DÍA (Lógica Base)
  const passesByDate = futurePases.reduce((acc, pase) => {
    const dateKey = new Date(pase.fecha_hora).toDateString(); 
    if (!acc[dateKey]) acc[dateKey] = [];
    acc[dateKey].push(pase);
    return acc;
  }, {});

  // Ordenar los días
  const sortedDates = Object.entries(passesByDate).sort(
    (a, b) => new Date(a[1][0].fecha_hora) - new Date(b[1][0].fecha_hora)
  );

  // 3. AYUDANTE PARA AGRUPAR POR CINE (DENTRO DE UN DÍA)
  const groupSessionsByCinema = (sessions) => {
    return sessions.reduce((acc, session) => {
      const cineName = session.cine;
      if (!acc[cineName]) acc[cineName] = [];
      acc[cineName].push(session);
      return acc;
    }, {});
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white font-sans pb-20">
      
      {/* --- HERO SECTION --- */}
      <div className="relative h-[50vh] w-full overflow-hidden">
        <div 
            className="absolute inset-0 bg-cover bg-center transition-transform duration-1000 hover:scale-105"
            style={{ 
                backgroundImage: `url(${movie.backdrop_url || movie.poster_url})`,
                filter: movie.backdrop_url ? "brightness(0.5)" : "blur(20px) brightness(0.4)" 
            }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-gray-900/60 to-transparent" />

        <button 
            onClick={() => router.back()} 
            className="absolute top-6 left-6 z-50 bg-black/50 backdrop-blur-md p-2 rounded-full hover:bg-white/20 transition cursor-pointer group border border-white/10"
        >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6 text-white group-hover:text-yellow-400 transition-colors">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
        </button>

        <div className="absolute bottom-0 left-0 w-full p-6 md:p-12 flex flex-col md:flex-row gap-8 items-end z-10">
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
                
                <div className="flex flex-wrap items-center gap-4 mt-4 text-sm font-semibold tracking-wide">
                    {movie.anio && <span className="bg-white/10 px-3 py-1 rounded border border-white/10">{movie.anio}</span>}
                    {movie.duracion > 0 && <span className="bg-white/10 px-3 py-1 rounded border border-white/10 flex items-center gap-1">⏱️ {movie.duracion} min</span>}
                    {movie.nota_tmdb > 0 && <span className="text-yellow-400 flex items-center gap-1">⭐ {movie.nota_tmdb.toFixed(1)}</span>}
                    {movie.tmdb_id && (
                        <a href={`https://letterboxd.com/tmdb/${movie.tmdb_id}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-green-400 hover:text-green-300 transition-colors">
                            Letterboxd
                        </a>
                    )}
                </div>
            </div>
        </div>
      </div>

      {/* --- CONTENIDO PRINCIPAL --- */}
      <div className="max-w-6xl mx-auto px-6 py-10">
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* IZQUIERDA: SINOPSIS + TRÁILER */}
            <div className="lg:col-span-1 space-y-8">
                
                {/* Sinopsis */}
                <div>
                    <h3 className="text-xl font-bold text-yellow-500 mb-2 uppercase">Sinopsis</h3>
                    <p className="text-gray-300 leading-relaxed text-lg font-light">
                        {movie.sinopsis || "No hay sinopsis disponible."}
                    </p>
                </div>

                {/* Géneros */}
                {movie.generos && (
                    <div>
                        <h3 className="text-sm font-bold text-gray-500 mb-2 uppercase">Géneros</h3>
                        <div className="flex flex-wrap gap-2">
                            {movie.generos.split(",").map((g, i) => (
                                <span key={i} className="text-xs border border-gray-600 px-2 py-1 rounded-full text-gray-400">{g.trim()}</span>
                            ))}
                        </div>
                    </div>
                )}

                {/* 🔥 NUEVO: TRÁILER (Aquí queda de lujo) */}
                {movie.youtube_id && (
                    <div className="pt-4 border-t border-gray-800">
                        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                             🎬 Tráiler
                        </h3>
                        <div className="rounded-xl overflow-hidden border border-white/10 shadow-lg">
                            <LiteYouTubeEmbed 
                                id={movie.youtube_id} 
                                title={`Tráiler de ${movie.titulo}`}
                                poster="maxresdefault"
                                webp={true}
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* DERECHA: SESIONES */}
            <div className="lg:col-span-2">
                
                {/* CABECERA CON BOTÓN TOGGLE */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 border-b border-gray-700 pb-4 gap-4">
                    <h3 className="text-2xl font-bold text-white flex items-center gap-2">
                        🎟️ Próximas Sesiones
                    </h3>
                    
                    <button
                        onClick={() => setGroupByCinema(!groupByCinema)}
                        className={`
                            px-4 py-2 rounded-full text-sm font-bold transition-all flex items-center gap-2 border
                            ${groupByCinema 
                                ? "bg-yellow-500 text-black border-yellow-400 shadow-[0_0_15px_rgba(234,179,8,0.4)]" 
                                : "bg-gray-800 text-gray-300 border-gray-600 hover:bg-gray-700"
                            }
                        `}
                    >
                        {groupByCinema ? <>🎬 Agrupado por Cine</> : <>Agrupar por Cine</>}
                    </button>
                </div>

                <div className="space-y-10">
                    {sortedDates.length === 0 && (
                        <p className="text-gray-500 italic">No hay sesiones programadas próximamente.</p>
                    )}
                    {sortedDates.map(([dateKey, sessions]) => (
                        <div key={dateKey} className="animate-fade-in-up">
                            {/* Fecha Cabecera */}
                            <div className="flex items-center gap-3 mb-4 sticky top-0 bg-gray-900/95 backdrop-blur py-2 z-10">
                                <div className="w-1.5 h-8 bg-yellow-500 rounded-full"></div>
                                <h4 className="text-xl font-semibold capitalize text-gray-200">
                                    {formatDate(sessions[0].fecha_hora)}
                                </h4>
                            </div>

                            <div className="pl-5 border-l border-gray-800 ml-1">
                                {groupByCinema ? (
                                    /* MODO A: AGRUPADO POR CINE */
                                    <div className="space-y-6">
                                        {Object.entries(groupSessionsByCinema(sessions))
                                            .sort((a, b) => a[0].localeCompare(b[0]))
                                            .map(([cineName, cineSessions]) => (
                                            <div key={cineName} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                                                <h5 className="text-yellow-400 font-bold uppercase text-sm mb-3 flex items-center gap-2">
                                                    📍 {cineName}
                                                </h5>
                                                <div className="flex flex-wrap gap-3">
                                                    {cineSessions.map((sesion) => (
                                                        <a 
                                                            key={sesion.id}
                                                            href={sesion.link_compra}
                                                            target="_blank" rel="noopener noreferrer"
                                                            className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg border border-gray-600 hover:border-white/30 transition-all flex items-center gap-2 group"
                                                        >
                                                            <span className="text-lg font-bold text-white group-hover:text-yellow-400">
                                                                {formatTime(sesion.fecha_hora)}
                                                            </span>
                                                            {sesion.idioma === 'VOSE' && <span className="text-[10px] font-bold bg-black/40 px-1.5 py-0.5 rounded text-gray-400 border border-white/5">VO</span>}
                                                        </a>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    /* MODO B: LISTA NORMAL */
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        {sessions.map((sesion) => (
                                            <a 
                                                key={sesion.id}
                                                href={sesion.link_compra}
                                                target="_blank" rel="noopener noreferrer"
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
                                                    {sesion.idioma === 'VOSE' && <span className="text-[10px] font-bold bg-black/40 px-1.5 py-0.5 rounded text-gray-400 border border-gray-600">VO</span>}
                                                    <div className="bg-gray-900 px-3 py-1 rounded-lg text-lg font-bold text-white group-hover:text-yellow-400 transition-colors">
                                                        {formatTime(sesion.fecha_hora)}
                                                    </div>
                                                </div>
                                            </a>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>

        {/* 🔥 NUEVO: GALERÍA DE FOTOS (OCUPANDO TODO EL ANCHO ABAJO) */}
        {movie.imagenes_galeria && movie.imagenes_galeria.length > 0 && (
            <div className="mt-16 pt-10 border-t border-gray-800">
                <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
                    📸 Galería de Imágenes
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    {movie.imagenes_galeria.map((imgUrl, index) => (
                        <div key={index} className="relative group rounded-xl overflow-hidden aspect-video border border-white/10 shadow-lg cursor-pointer">
                            <img 
                                src={imgUrl} 
                                alt={`Escena ${index + 1}`} 
                                className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                            />
                            {/* Overlay sutil */}
                            <div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors"></div>
                        </div>
                    ))}
                </div>
            </div>
        )}

      </div>
    </main>
  );
}