"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { Filter, X, Star, Clock, MapPin, Calendar } from "lucide-react"; 

// Ayudante para saber si es mañana, tarde o noche
const getTimeCategory = (dateString) => {
  const hour = new Date(dateString).getHours();
  if (hour < 15) return "morning"; 
  if (hour < 21) return "afternoon"; 
  return "night"; 
};

export default function Cartelera() {
  const [pases, setPases] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // ESTADOS DE FILTRO Y ORDEN
  const [isFilterOpen, setIsFilterOpen] = useState(false); 
  const [selectedCines, setSelectedCines] = useState([]);
  const [sortBy, setSortBy] = useState("pases"); // 'pases' | 'nota'
  const [timeFilter, setTimeFilter] = useState("all"); 

  // 1. CARGA DE DATOS
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/pases`)
      .then((res) => res.json())
      .then((data) => {
        setPases(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error cargando pases:", err);
        setLoading(false);
      });
  }, []);

  // 🚨 1.5 EL PORTERO: FILTRO "ANTI-AYER" (NUEVO) 🚨
  // Creamos una lista maestra que solo contiene pases de HOY en adelante.
  // Usamos esta lista para todo lo demás. Si es de ayer, no existe.
  const futurePases = useMemo(() => {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0); // Ponemos el reloj a las 00:00 de hoy

    return pases.filter(pase => {
      const fechaPase = new Date(pase.fecha_hora);
      return fechaPase >= hoy; // Solo pasa si es hoy o futuro
    });
  }, [pases]);

  // 2. EXTRAER CINES DINÁMICAMENTE (Usando futurePases)
  // Nota: Si un cine solo tenía pelis ayer, ya no saldrá aquí. ¡Limpieza total!
  const uniqueCines = useMemo(() => {
    const nombres = futurePases.map(p => p.cine);
    return [...new Set(nombres)].sort(); 
  }, [futurePases]);

  // 3. LÓGICA DE FILTRADO Y AGRUPACIÓN (Usando futurePases)
  const filteredRawPases = futurePases.filter((pase) => {
    // Filtro Cine
    const matchCine = selectedCines.length === 0 || selectedCines.includes(pase.cine);
    // Filtro Hora
    const matchTime = timeFilter === "all" || getTimeCategory(pase.fecha_hora) === timeFilter;
    
    return matchCine && matchTime;
  });

  // Agrupar por película
  const moviesMap = {};
  filteredRawPases.forEach((pase) => {
    const movieId = pase.pelicula_id;
    if (!moviesMap[movieId]) {
      moviesMap[movieId] = {
        id: pase.pelicula_id,
        titulo: pase.titulo,
        poster: pase.poster,
        nota: pase.nota_tmdb || 0,
        generos: pase.generos,
        pases: [],
      };
    }
    moviesMap[movieId].pases.push(pase);
  });

  // Convertir a array y ORDENAR
  const sortedMovies = Object.values(moviesMap).sort((a, b) => {
    if (sortBy === "nota") {
      return b.nota - a.nota;
    } else {
      return b.pases.length - a.pases.length;
    }
  });

  // MANEJADORES
  const toggleCine = (cine) => {
    setSelectedCines((prev) =>
      prev.includes(cine) ? prev.filter((c) => c !== cine) : [...prev, cine]
    );
  };

  const clearFilters = () => {
    setSelectedCines([]);
    setTimeFilter("all");
    setSortBy("pases");
  };

  // --- RENDER ---
  if (loading)
    return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-yellow-500 font-bold text-xl">Cargando cartelera...</div>;

  return (
    <main className="min-h-screen bg-gray-950 text-gray-100 font-sans pb-20 relative">
      
      {/* HEADER FIJO */}
      <header className="sticky top-0 z-30 bg-gray-950/90 backdrop-blur-md border-b border-gray-800 p-4 flex justify-between items-center shadow-lg">
        <div>
            <h1 className="text-2xl font-black text-yellow-500 tracking-tighter uppercase font-kanit">
            FPS<span className="text-white">24</span>
            </h1>
            <p className="text-xs text-gray-400">Madrid Cinema Scraper</p>
        </div>
        
        {/* BOTÓN FILTROS */}
        <button 
            onClick={() => setIsFilterOpen(true)}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white px-4 py-2 rounded-full border border-gray-700 transition-all font-semibold text-sm"
        >
            <Filter size={16} className="text-yellow-500" />
            Filtros
            {(selectedCines.length > 0 || timeFilter !== 'all') && (
                <span className="flex h-2 w-2 rounded-full bg-red-500 absolute top-0 right-0 -mt-1 -mr-1"></span>
            )}
        </button>
      </header>

      {/* MODAL DE FILTROS (Overlay) */}
      {isFilterOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end">
            <div className="w-full max-w-sm bg-gray-900 h-full shadow-2xl p-6 overflow-y-auto animate-in slide-in-from-right duration-300">
                
                <div className="flex justify-between items-center mb-8">
                    <h2 className="text-xl font-bold text-white">Configuración</h2>
                    <button onClick={() => setIsFilterOpen(false)} className="p-2 bg-gray-800 rounded-full hover:bg-gray-700 text-white">
                        <X size={20} />
                    </button>
                </div>

                {/* ORDENAR */}
                <div className="mb-8">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">Ordenar Por</h3>
                    <div className="grid grid-cols-2 gap-3">
                        <button 
                            onClick={() => setSortBy("pases")}
                            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition-all ${sortBy === 'pases' ? 'bg-yellow-500/10 border-yellow-500 text-yellow-400' : 'bg-gray-800 border-gray-800 text-gray-400'}`}
                        >
                            <Calendar size={20} />
                            <span className="text-sm font-semibold">Más Pases</span>
                        </button>
                        <button 
                            onClick={() => setSortBy("nota")}
                            className={`p-3 rounded-xl border flex flex-col items-center gap-2 transition-all ${sortBy === 'nota' ? 'bg-yellow-500/10 border-yellow-500 text-yellow-400' : 'bg-gray-800 border-gray-800 text-gray-400'}`}
                        >
                            <Star size={20} />
                            <span className="text-sm font-semibold">Mejor Nota</span>
                        </button>
                    </div>
                </div>

                {/* HORARIO */}
                <div className="mb-8">
                    <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-3">Horario</h3>
                    <div className="flex flex-wrap gap-2">
                        {[
                            { id: 'all', label: 'Todo el día' },
                            { id: 'morning', label: 'Mañana (<15h)' },
                            { id: 'afternoon', label: 'Tarde (15-21h)' },
                            { id: 'night', label: 'Noche (>21h)' }
                        ].map((opt) => (
                            <button
                                key={opt.id}
                                onClick={() => setTimeFilter(opt.id)}
                                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${timeFilter === opt.id ? 'bg-white text-black' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                            >
                                {opt.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* CINES (DINÁMICO) */}
                <div className="mb-8">
                    <div className="flex justify-between items-center mb-3">
                        <h3 className="text-xs font-bold text-gray-500 uppercase tracking-widest">Cines</h3>
                        <span className="text-xs text-gray-500">{selectedCines.length} seleccionados</span>
                    </div>
                    <div className="flex flex-col gap-2">
                        {uniqueCines.map((cine) => (
                            <button
                                key={cine}
                                onClick={() => toggleCine(cine)}
                                className={`w-full text-left px-4 py-3 rounded-xl border transition-all flex justify-between items-center ${
                                    selectedCines.includes(cine) 
                                    ? 'bg-blue-600/20 border-blue-500 text-blue-400' 
                                    : 'bg-gray-800 border-gray-800 text-gray-400 hover:bg-gray-750'
                                }`}
                            >
                                <span className="font-medium">{cine}</span>
                                {selectedCines.includes(cine) && <MapPin size={16} />}
                            </button>
                        ))}
                    </div>
                </div>

                {/* FOOTER */}
                <div className="pt-4 border-t border-gray-800">
                    <button 
                        onClick={clearFilters}
                        className="w-full py-3 text-sm text-gray-500 hover:text-white transition-colors"
                    >
                        Limpiar todos los filtros
                    </button>
                    <button 
                        onClick={() => setIsFilterOpen(false)}
                        className="w-full mt-2 bg-yellow-500 hover:bg-yellow-400 text-black font-bold py-3 rounded-xl transition-colors"
                    >
                        Ver {sortedMovies.length} Películas
                    </button>
                </div>

            </div>
        </div>
      )}

      {/* LISTA */}
      <div className="max-w-7xl mx-auto p-4">
        {sortedMovies.length === 0 ? (
            <div className="text-center py-20 opacity-50">
                <p className="text-xl">No hay sesiones con estos filtros 😢</p>
                <button onClick={clearFilters} className="mt-4 text-yellow-500 underline">Borrar filtros</button>
            </div>
        ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            {sortedMovies.map((peli) => (
                <Link
                key={peli.id}
                href={`/pelicula/${peli.id}`}
                className="group relative bg-gray-900 rounded-xl overflow-hidden shadow-lg hover:shadow-yellow-500/10 transition-all hover:-translate-y-1 border border-gray-800 hover:border-yellow-500/50 block"
                >
                {/* NOTA TMDB */}
                {peli.nota > 0 && (
                    <div className="absolute top-2 right-2 z-10 bg-black/70 backdrop-blur text-yellow-400 text-xs font-bold px-2 py-1 rounded flex items-center gap-1 border border-yellow-500/20 shadow-lg">
                    <Star size={12} fill="currentColor" />
                    {peli.nota.toFixed(1)}
                    </div>
                )}

                {/* POSTER */}
                <div className="aspect-[2/3] w-full overflow-hidden bg-gray-800 relative">
                    {peli.poster ? (
                    <img
                        src={peli.poster}
                        alt={peli.titulo}
                        className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
                        loading="lazy"
                    />
                    ) : (
                    <div className="flex items-center justify-center h-full text-gray-600">
                        Sin imagen
                    </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-gray-900 via-transparent to-transparent opacity-80" />
                </div>

                {/* INFO */}
                <div className="p-3 absolute bottom-0 w-full">
                    <h2 className="font-bold text-sm leading-tight text-white mb-1 drop-shadow-md line-clamp-2 uppercase">
                    {peli.titulo}
                    </h2>
                    
                    <div className="flex items-center justify-between text-xs text-gray-400 mt-2">
                        <span className="flex items-center gap-1 bg-gray-800 px-2 py-1 rounded-full border border-gray-700">
                            <Clock size={12} />
                            {peli.pases.length} pases
                        </span>
                    </div>
                </div>
                </Link>
            ))}
            </div>
        )}
      </div>

    </main>
  );
}