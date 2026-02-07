"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link"; // <--- 1. IMPORTANTE

// --- HELPERS ---
const isSameDay = (d1, d2) => {
  const f1 = new Date(d1);
  const f2 = new Date(d2);
  return (
    f1.getDate() === f2.getDate() &&
    f1.getMonth() === f2.getMonth() &&
    f1.getFullYear() === f2.getFullYear()
  );
};

const extractTime = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

// --- NORMALIZATION ---
const normalizeTitle = (title) => {
  if (!title) return ""; 
  return title
    .toUpperCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") 
    .replace(/[^A-Z0-9]/g, ""); 
};

const cleanForSearch = (text) => {
  return text
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
};

// Limpia el nombre del cine para que quede bonito en el botón
const cleanCinemaName = (name) => {
    return name.replace("Cine ", "").replace("Madrid", "").replace("Cines ", "").trim();
};

export default function Home() {
  const [pases, setPases] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [weekOffset, setWeekOffset] = useState(0);
  const [onlySpecials, setOnlySpecials] = useState(false);
  const [searchTerm, setSearchTerm] = useState(""); 
  const [selectedCinema, setSelectedCinema] = useState("Todos");

 // 1. DATA LOADING
  useEffect(() => {
    // Definimos la URL: Si hay variable de entorno (Vercel) úsala, si no (tu casa), usa localhost.
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

    // Usamos comillas invertidas ` ` para meter la variable en la cadena
    fetch(`${apiUrl}/pases`)
      .then((res) => res.json())
      .then((data) => {
        // AQUÍ ESTABA EL ERROR: Quitamos ": any"
        const sortedData = data.sort(
          (a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora)
        );
        setPases(sortedData);
      })
      .catch((err) => console.error("Error loading sessions:", err));
  }, []);

  
  // 2. EXTRAER CINES DISPONIBLES
  const availableCinemas = useMemo(() => {
    const pasesDelDia = pases.filter(p => isSameDay(p.fecha_hora, selectedDate));
    const uniqueCinemas = new Set(pasesDelDia.map(p => p.cine));
    return ["Todos", ...Array.from(uniqueCinemas).sort()];
  }, [pases, selectedDate]);

  // Volver a "Todos" si el cine seleccionado no está disponible
  useEffect(() => {
    if (selectedCinema !== "Todos" && !availableCinemas.includes(selectedCinema)) {
        setSelectedCinema("Todos");
    }
  }, [selectedDate, availableCinemas, selectedCinema]);


  // 3. FILTRADO PRINCIPAL
  const filteredPases = useMemo(() => {
    let data = pases;
    
    data = data.filter((pase) => isSameDay(pase.fecha_hora, selectedDate));
    
    if (onlySpecials) {
      data = data.filter((pase) => pase.es_evento_especial);
    }

    if (selectedCinema !== "Todos") {
        data = data.filter((pase) => pase.cine === selectedCinema);
    }

    return data;
  }, [pases, selectedDate, onlySpecials, selectedCinema]);

  // 4. AGRUPACIÓN Y BÚSQUEDA
  const groupedMovies = Object.values(
    filteredPases.reduce((acc, pase) => {
      const rawTitle = pase.pelicula?.titulo || "Título Desconocido";
      const titleKey = normalizeTitle(rawTitle);

      if (!acc[titleKey]) {
        acc[titleKey] = {
          id: pase.pelicula?.id, // <--- 2. AÑADIDO ID AQUÍ 🔑
          titulo: rawTitle.toUpperCase(),
          poster: pase.pelicula?.poster_url, 
          nota: pase.pelicula?.nota_tmdb || 0,
          anio: pase.pelicula?.anio || null,
          es_especial: false,
          cines: {},
          total_sesiones: 0 
        };
      }
      
      if (pase.es_evento_especial) acc[titleKey].es_especial = true;

      const cinemaKey = pase.cine;
      if (!acc[titleKey].cines[cinemaKey]) {
        acc[titleKey].cines[cinemaKey] = [];
      }

      acc[titleKey].cines[cinemaKey].push(pase);
      acc[titleKey].total_sesiones += 1;

      return acc;
    }, {})
  )
  .filter((movie) => {
      if (!searchTerm) return true;
      return cleanForSearch(movie.titulo).includes(cleanForSearch(searchTerm));
  })
  .sort((a, b) => {
      if (b.total_sesiones !== a.total_sesiones) {
          return b.total_sesiones - a.total_sesiones;
      }
      return a.titulo.localeCompare(b.titulo);
  });

  // Generar lista de días
  const allDays = pases.reduce((acc, pase) => {
    const date = pase.fecha_hora;
    const exists = acc.find((d) => isSameDay(d, date));
    if (!exists) acc.push(date);
    return acc;
  }, []);

  const DAYS_PER_PAGE = 7;
  const start = weekOffset * DAYS_PER_PAGE;
  const end = start + DAYS_PER_PAGE;
  const visibleDays = allDays.slice(start, end);
  const hasMoreDays = allDays.length > end;

  const changeWeek = (direction) => {
    const newOffset = weekOffset + direction;
    setWeekOffset(newOffset);
    const newStart = newOffset * DAYS_PER_PAGE;
    if (allDays[newStart]) {
        setSelectedDate(new Date(allDays[newStart]));
    }
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white p-4 md:p-8 font-sans pb-24">
      
      {/* 1. HEADER */}
     {/* 1. HEADER */}
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

      {/* 2. CONTROLES SUPERIORES */}
      <div className="flex flex-col xl:flex-row items-center justify-between gap-8 mt-10 md:mt-12 max-w-9xl mx-auto w-full">
        
        {/* Selector de Días */}
        <div className="flex flex-wrap justify-center items-center gap-3">
            {weekOffset > 0 && (
                <button 
                    onClick={() => changeWeek(-1)} 
                    className="h-16 w-12 md:h-20 md:w-14 rounded-2xl bg-gray-800/50 border border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-yellow-400 hover:border-yellow-400/50 transition-all flex items-center justify-center backdrop-blur-sm"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                    </svg>
                </button>
            )}

            {visibleDays.map((dateStr, index) => {
            const active = isSameDay(dateStr, selectedDate);
            return (
                <button
                key={index}
                onClick={() => setSelectedDate(new Date(dateStr))}
                className={`
                    flex flex-col items-center justify-center w-16 md:w-20 py-3 rounded-2xl transition-all duration-300
                    ${active
                    ? "bg-gradient-to-br from-yellow-400 to-orange-500 text-black shadow-lg shadow-yellow-500/40 ring-2 ring-yellow-300 transform -translate-y-1 scale-105"
                    : "bg-gray-800/50 text-gray-400 hover:bg-gray-800 hover:text-white backdrop-blur-sm border border-gray-700 hover:border-gray-500"
                    }
                `}
                >
                <span className="text-xs font-semibold uppercase tracking-wide opacity-90">
                    {new Date(dateStr).toLocaleDateString('es-ES', { weekday: 'short' }).replace('.', '')}
                </span>
                <span className="text-2xl md:text-3xl font-bold mt-0.5">
                    {new Date(dateStr).getDate()}
                </span>
                
                {active && (
                    <div className="w-1.5 h-1.5 bg-black rounded-full mt-1"></div>
                )}
                </button>
            );
            })}

            {hasMoreDays && (
                <button 
                    onClick={() => changeWeek(1)} 
                    className="h-16 w-12 md:h-20 md:w-14 rounded-2xl bg-gray-800/50 border border-gray-700 text-gray-400 hover:bg-gray-800 hover:text-yellow-400 hover:border-yellow-400/50 transition-all flex items-center justify-center backdrop-blur-sm"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-6 h-6">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                </button>
            )}
        </div>

        {/* Filtros Derecha */}
        <div className="flex flex-col sm:flex-row gap-4 w-full xl:w-auto">
            <button
            onClick={() => setOnlySpecials(!onlySpecials)}
            className={`
                h-14 px-6 rounded-2xl font-semibold transition-all shadow-xl flex items-center justify-center gap-2 text-sm md:text-base border w-full sm:w-auto
                ${onlySpecials 
                ? "bg-purple-600 text-white border-purple-400 shadow-purple-500/50 ring-2 ring-purple-400/30" 
                : "bg-gray-800/50 text-gray-300 hover:bg-gray-700 border-gray-700 hover:border-gray-500 hover:text-white backdrop-blur-sm"}
            `}
            >
            {onlySpecials ? "⭐  ESPECIALES" : "⭐ VER ESPECIALES"}
            </button>

            <div className="relative w-full sm:w-64 group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-gray-500 group-focus-within:text-yellow-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input
                    type="text"
                    placeholder="Buscar película..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="block w-full h-14 pl-10 pr-3 rounded-2xl bg-gray-800/50 border border-gray-700 text-gray-300 placeholder-gray-500 focus:outline-none focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 focus:text-white transition-all backdrop-blur-sm"
                />
                 {searchTerm && (
                    <button 
                        onClick={() => setSearchTerm("")}
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-white"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                    </button>
                )}
            </div>
        </div>
      </div>

      {/* 3. SELECTOR DE CINES */}
      <div className="mt-8 mb-10 max-w-9xl mx-auto">
        <div className="flex gap-3 overflow-x-auto pb-4 px-2 md:px-0 custom-scrollbar">
            {availableCinemas.map((cine, index) => (
                <button
                    key={index}
                    onClick={() => setSelectedCinema(cine)}
                    className={`
                        whitespace-nowrap px-6 py-3 rounded-xl font-bold text-sm md:text-base transition-all duration-300 border
                        ${selectedCinema === cine
                            ? "bg-yellow-400 text-black border-yellow-300 shadow-lg shadow-yellow-400/20 scale-105"
                            : "bg-gray-800 text-gray-400 border-gray-700 hover:bg-gray-700 hover:text-white hover:border-gray-500"
                        }
                    `}
                >
                    {cleanCinemaName(cine)}
                </button>
            ))}
        </div>
      </div>

      {/* 4. GRID PELÍCULAS */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 max-w-9xl mx-auto px-2 md:px-0">
        {groupedMovies.length === 0 ? (
          <div className="col-span-full text-center py-24 bg-gray-800/30 rounded-3xl border border-gray-700/50 border-dashed">
            <p className="text-3xl text-gray-500 font-medium">
                {searchTerm 
                    ? "🔍 No encuentro esa peli..." 
                    : (selectedCinema !== "Todos" ? `😴 No hay sesiones en ${cleanCinemaName(selectedCinema)} hoy.` : "😴 No hay sesiones para este día.")
                }
            </p>
          </div>
        ) : (
            groupedMovies.map((movie, index) => (
            <div
              key={index}
              className={`
                bg-gray-800 rounded-3xl overflow-hidden shadow-2xl border flex flex-col sm:flex-row 
                h-auto sm:h-64 
                transition-all hover:bg-gray-750 group
                ${movie.es_especial ? "border-purple-500/60 shadow-purple-900/30" : "border-gray-700 hover:border-gray-500"}
              `}
            >
              {/* PÓSTER (ENLAZADO A DETALLE) 🔗 */}
              <Link href={`/pelicula/${movie.id}`} className="w-full sm:w-40 flex-shrink-0 relative h-64 sm:h-auto overflow-hidden bg-gray-900 flex items-center justify-center cursor-pointer">
                {movie.poster ? (
                    <img
                    src={movie.poster}
                    alt={movie.titulo}
                    className="w-full h-full object-cover opacity-95 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500"
                    />
                ) : (
                    // Placeholder Nativo (cuando no hay foto)
                    <div className="flex flex-col items-center justify-center text-gray-600 p-4 text-center">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-12 h-12 mb-2 opacity-50">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
                        </svg>
                        <span className="text-xs font-bold uppercase tracking-wider opacity-70">Sin Imagen</span>
                    </div>
                )}
                
                {/* Nota TMDB */}
                {movie.nota > 0 && (
                    <div className="absolute top-2 left-2 bg-black/80 backdrop-blur-md text-yellow-400 text-xs font-bold px-2 py-1 rounded-lg flex items-center gap-1 shadow-lg border border-white/10">
                        ⭐ {movie.nota.toFixed(1)}
                    </div>
                )}
              </Link>

              {/* Info */}
              <div className="flex-1 p-4 flex flex-col min-w-0 overflow-y-auto custom-scrollbar bg-gray-800">
                
                {/* Header (TÍTULO ENLAZADO A DETALLE) 🔗 */}
                <div className="mb-3 border-b border-gray-700 pb-2">
                    <Link href={`/pelicula/${movie.id}`}>
                        <h2 className="text-xl md:text-2xl font-raleway font-bold leading-tight text-white mb-1 truncate hover:text-yellow-400 transition-colors cursor-pointer" title={movie.titulo}>
                            {movie.titulo}
                        </h2>
                    </Link>
                    
                    <div className="flex flex-wrap items-center gap-2">
                        {movie.es_especial && (
                            <span className="bg-purple-600 text-white text-[10px] px-2 py-0.5 rounded-full uppercase font-semibold tracking-wider shadow-lg shadow-purple-900/50">
                                Especial
                            </span>
                        )}
                        {movie.anio && (
                            <span className="text-gray-300 text-xs font-mono bg-gray-700 px-2 py-0.5 rounded-md border border-gray-600">
                                {movie.anio}
                            </span>
                        )}
                    </div>
                </div>

                {/* Cinemas & Times */}
                <div className="space-y-3">
                  {Object.entries(movie.cines).map(([cinemaName, sessions]) => (
                    <div key={cinemaName} className="flex flex-col gap-1">
                      
                      <h3 className="text-yellow-500 font-semibold text-xs uppercase tracking-wide flex items-center gap-2">
                        📍 {cinemaName.replace("Cine ", "").replace("Madrid", "").replace("Cines ", "")}
                      </h3>
                      
                      <div className="flex flex-wrap gap-2">
                        {sessions.map((session) => (
                          <a
                            key={session.id}
                            href={session.link_compra}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`
                              px-3 py-1 rounded-lg text-xs font-semibold transition-all transform hover:scale-105 active:scale-95 flex items-center gap-2 shadow-md
                              ${session.es_evento_especial 
                                  ? 'bg-gradient-to-r from-purple-900 to-indigo-900 text-white border border-purple-500/50 hover:border-purple-400' 
                                  : (session.idioma === 'VOSE' 
                                    ? 'bg-gray-700 text-white hover:bg-gray-600 border border-gray-500'
                                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600 border border-gray-600')
                              }
                            `}
                          >
                            <span className="text-sm">{extractTime(session.fecha_hora)}</span>
                            {session.idioma === 'VOSE' && (
                                <span className="text-[9px] bg-black/30 px-1 rounded font-medium text-gray-400 border border-white/5">VO</span>
                            )}
                          </a>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </main>
  );
}