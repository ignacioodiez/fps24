"use client";

import { useState, useEffect, use } from "react";
import Header from "@/components/Header";
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

  if (loading) return <div className="min-h-screen bg-background flex items-center justify-center text-muted">Cargando...</div>;
  if (!movie) return <div className="min-h-screen bg-background flex items-center justify-center text-muted">Película no encontrada</div>;

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
    <main className="min-h-screen bg-background text-foreground pb-20">
      
      <Header backdrop={movie.backdrop_url} showTitle={false} />

      {/* Ficha bajo el Header */}
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row gap-8 items-end">
            <img
                src={movie.poster_url}
                alt={movie.titulo}
                className="hidden md:block w-48 rounded-xl border border-line bg-background"
            />

            <div className="flex-1 mb-2">
                <h1 className="text-4xl md:text-6xl font-black font-display uppercase leading-none text-foreground">
                    {movie.titulo}
                </h1>
                <h2 className="text-xl text-muted mt-2 font-display">{movie.titulo_original}</h2>

                <div className="flex flex-wrap items-center gap-4 mt-4 text-sm font-semibold tracking-wide">
                    {movie.anio && <span className="bg-surface px-3 py-1 rounded border border-line">{movie.anio}</span>}
                    {movie.duracion > 0 && <span className="bg-surface px-3 py-1 rounded border border-line flex items-center gap-1">{movie.duracion} min</span>}
                    {movie.nota_tmdb > 0 && <span className="bg-primary-soft text-primary px-3 py-1 rounded border border-primary flex items-center gap-1">TMDB {movie.nota_tmdb.toFixed(1)}</span>}
                    {movie.tmdb_id && (
                        <a href={`https://letterboxd.com/tmdb/${movie.tmdb_id}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 bg-accent-soft text-foreground px-3 py-1 rounded border border-accent hover:bg-accent transition-colors">
                            Letterboxd
                        </a>
                    )}
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
                    <h3 className="text-xl font-bold font-display text-primary mb-2 uppercase">Sinopsis</h3>
                    <p className="text-foreground leading-relaxed text-lg">
                        {movie.sinopsis || "No hay sinopsis disponible."}
                    </p>
                </div>

                {/* Géneros */}
                {movie.generos && (
                    <div>
                        <h3 className="text-sm font-bold text-muted mb-2 uppercase">Géneros</h3>
                        <div className="flex flex-wrap gap-2">
                            {movie.generos.split(",").map((g, i) => (
                                <span key={i} className="text-xs border border-line bg-surface px-2 py-1 rounded-full text-muted">{g.trim()}</span>
                            ))}
                        </div>
                    </div>
                )}

                {/* 🔥 NUEVO: TRÁILER (Aquí queda de lujo) */}
                {movie.youtube_id && (
                    <div className="pt-4 border-t border-line">
                        <h3 className="text-xl font-bold font-display text-foreground mb-4 flex items-center gap-2">
                             Tráiler
                        </h3>
                        <div className="rounded-xl overflow-hidden border border-line">
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
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 border-b border-line pb-4 gap-4">
                    <h3 className="text-2xl font-bold font-display text-foreground flex items-center gap-2">
                        Próximas Sesiones
                    </h3>
                    
                    <button
                        onClick={() => setGroupByCinema(!groupByCinema)}
                        className={`
                            px-4 py-2 rounded-full text-sm font-bold transition-colors flex items-center gap-2 border
                            ${groupByCinema 
                                ? "bg-primary text-white border-primary" 
                                : "bg-background text-foreground border-line hover:bg-surface"
                            }
                        `}
                    >
                        {groupByCinema ? <>Agrupado por Cine</> : <>Agrupar por Cine</>}
                    </button>
                </div>

                <div className="space-y-10">
                    {sortedDates.length === 0 && (
                        <p className="text-muted italic">No hay sesiones programadas próximamente.</p>
                    )}
                    {sortedDates.map(([dateKey, sessions]) => (
                        <div key={dateKey} className="animate-fade-in-up">
                            {/* Fecha Cabecera */}
                            <div className="flex items-center gap-3 mb-4 sticky top-0 bg-background py-2 z-10">
                                <div className="w-1.5 h-8 bg-primary rounded-full"></div>
                                <h4 className="text-xl font-semibold capitalize text-foreground">
                                    {formatDate(sessions[0].fecha_hora)}
                                </h4>
                            </div>

                            <div className="pl-5 border-l border-line ml-1">
                                {groupByCinema ? (
                                    /* MODO A: AGRUPADO POR CINE */
                                    <div className="space-y-6">
                                        {Object.entries(groupSessionsByCinema(sessions))
                                            .sort((a, b) => a[0].localeCompare(b[0]))
                                            .map(([cineName, cineSessions]) => (
                                            <div key={cineName} className="bg-background rounded-xl p-4 border border-line">
                                                <h5 className="text-primary font-bold uppercase text-sm mb-3 flex items-center gap-2">
                                                    {cineName}
                                                </h5>
                                                <div className="flex flex-wrap gap-3">
                                                    {cineSessions.map((sesion) => (
                                                        <a 
                                                            key={sesion.id}
                                                            href={sesion.link_compra}
                                                            target="_blank" rel="noopener noreferrer"
                                                            className="bg-background px-4 py-2 rounded-lg border border-line hover:border-primary transition-colors flex items-center gap-2 group"
                                                        >
                                                            <span className="text-lg font-bold text-foreground group-hover:text-primary">
                                                                {formatTime(sesion.fecha_hora)}
                                                            </span>
                                                            {sesion.idioma === 'VOSE' && <span className="text-[10px] font-bold bg-surface px-1.5 py-0.5 rounded text-muted border border-line">VO</span>}
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
                                                className="bg-background p-4 rounded-xl border border-line hover:border-primary transition-colors group flex justify-between items-center"
                                            >
                                                <div>
                                                    <div className="text-primary font-bold text-sm uppercase tracking-wider mb-1">
                                                        {sesion.cine}
                                                    </div>
                                                    <div className="text-xs text-muted">
                                                        {sesion.sala || "Sala estándar"}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    {sesion.idioma === 'VOSE' && <span className="text-[10px] font-bold bg-surface px-1.5 py-0.5 rounded text-muted border border-line">VO</span>}
                                                    <div className="bg-surface px-3 py-1 rounded-lg text-lg font-bold text-foreground group-hover:text-primary transition-colors">
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
            <div className="mt-16 pt-10 border-t border-line">
                <h3 className="text-2xl font-bold font-display text-foreground mb-6 flex items-center gap-2">
                    Galería de Imágenes
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    {movie.imagenes_galeria.map((imgUrl, index) => (
                        <div key={index} className="relative group rounded-xl overflow-hidden aspect-video border border-line">
                            <img 
                                src={imgUrl} 
                                alt={`Escena ${index + 1}`} 
                                className="w-full h-full object-cover"
                            />
                        </div>
                    ))}
                </div>
            </div>
        )}

      </div>
    </main>
  );
}