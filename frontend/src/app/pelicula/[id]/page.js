"use client";

import { useState, useEffect, use } from "react";
import Header from "@/components/Header";
import LiteYouTubeEmbed from 'react-lite-youtube-embed'; // <--- IMPORTANTE
import 'react-lite-youtube-embed/dist/LiteYouTubeEmbed.css'; // <--- ESTILOS YOUTUBE
// Mismos bloques que la vista rápida (modal) y la cartelera de la portada
import { ChipDato, ChipsGeneros, LineaDireccion, NotaPelicula, duracionTexto } from "@/components/FichaPelicula";
import { SelectorAgrupacion, SesionesPorDias, diaConSesiones, useAgrupacion } from "@/components/Sesiones";
import BotonDiario from "@/components/BotonDiario";

export default function MovieDetail({ params, searchParams }) {
  const { id } = use(params);
  const { dia } = use(searchParams); // de una tarjeta con sesión sugerida
  
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Sesiones "Por cine" (por defecto) o "Por hora"; se recuerda en localStorage (igual que en la vista rápida)
  const [modo, setModo] = useAgrupacion();

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

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      
      <Header backdrop={movie.backdrop_url} showTitle={false} />

      {/* Ficha bajo el Header */}
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row gap-8 items-end">
            <div className="hidden md:flex w-48 aspect-[2/3] shrink-0 rounded-2xl overflow-hidden border border-line bg-surface items-center justify-center">
                {movie.poster_url ? (
                    <img src={movie.poster_url} alt={movie.titulo} className="w-full h-full object-cover" />
                ) : (
                    <span className="p-3 text-center font-display font-bold text-muted">{movie.titulo}</span>
                )}
            </div>

            <div className="flex-1 mb-2">
                <h1 className="text-4xl md:text-6xl font-bold font-display uppercase leading-none text-foreground">
                    {movie.titulo}
                </h1>
                <h2 className="text-xl text-muted mt-2 font-display">{movie.titulo_original}</h2>

                <LineaDireccion director={movie.director} className="mt-2" />

                <div className="flex flex-wrap items-center gap-2 mt-4">
                    {movie.anio && <ChipDato>{movie.anio}</ChipDato>}
                    {movie.duracion > 0 && <ChipDato>{duracionTexto(movie.duracion)}</ChipDato>}
                    <NotaPelicula nota={movie.nota_tmdb} votos={movie.votos} />
                    {movie.tmdb_id && (
                        <a href={`https://letterboxd.com/tmdb/${movie.tmdb_id}`} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold bg-accent-soft text-foreground px-2 py-1 rounded-lg border border-accent hover:bg-accent transition-colors">
                            Letterboxd
                        </a>
                    )}
                </div>

                <BotonDiario pelicula={movie} dia={dia} className="mt-4" />
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
                        <ChipsGeneros generos={movie.generos} />
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
                
                {/* CABECERA CON EL SELECTOR "POR CINE | POR HORA" */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 border-b border-line pb-4 gap-4">
                    <h3 className="text-2xl font-bold font-display text-foreground flex items-center gap-2">
                        Próximas Sesiones
                    </h3>
                    
                    <SelectorAgrupacion modo={modo} onCambiar={setModo} />
                </div>

                {/* Primer día con sesiones abierto y "Otros días" plegados, con los límites de la página completa */}
                <SesionesPorDias pases={movie.pases} pelicula={movie} modo={modo} contexto="pagina" diaElegido={diaConSesiones(dia, movie.pases)} />
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