"use client";

import { useState, useEffect, useMemo } from "react";
// Importamos Helpers
import { isSameDay, normalizeTitle, cleanForSearch, isDiaEspectador } from "@/utils/helpers"; // 🆕 Importamos isDiaEspectador
// Importamos Componentes
import Header from "@/components/Header";
import DateSelector from "@/components/DateSelector";
import MovieGrid from "@/components/MovieGrid";
import FilterMenu from "@/components/FilterMenu"; 
import { usePathname, useSearchParams } from "next/navigation"; // 👈 NUEVO
import * as gtag from "@/lib/gtag"; // 👈 NUEVO


export default function Home() {
  const [pases, setPases] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [weekOffset, setWeekOffset] = useState(0);
  
  // 🆕 ESTADOS DEL NUEVO FILTRO
  const [selectedCinema, setSelectedCinema] = useState("Todos");
  const [timeRange, setTimeRange] = useState([6, 24]); // De 6am a 24pm (Medianoche)
  const [spectatorOnly, setSpectatorOnly] = useState(false);
  const [onlySpecials, setOnlySpecials] = useState(false);
  
  const [searchTerm, setSearchTerm] = useState(""); 
  const [sortBy, setSortBy] = useState("sesiones"); 

   const pathname = usePathname(); // 👈 NUEVO
   const searchParams = useSearchParams(); // 👈 NUEVO

  // 1. DATA LOADING
   // 👇 TRACKING DE NAVEGACIÓN
  useEffect(() => {
    if (pathname) {
      const url = pathname + (searchParams?.toString() ? `?${searchParams.toString()}` : '');
      gtag.pageview(url);
    }
  }, [pathname, searchParams]);



  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    fetch(`${apiUrl}/pases`)
      .then((res) => res.json())
      .then((data) => {
        const sortedData = data.sort(
          (a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora)
        );
        setPases(sortedData);
      })
      .catch((err) => console.error("Error loading sessions:", err));
  }, []);

  // 1.5 FILTRO "ANTI-AYER"
  const futurePases = useMemo(() => {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0); 
    return pases.filter(pase => {
      const fechaPase = new Date(pase.fecha_hora);
      return fechaPase >= hoy; 
    });
  }, [pases]);

  // 2. EXTRAER CINES DISPONIBLES
  const availableCinemas = useMemo(() => {
    const pasesDelDia = futurePases.filter(p => isSameDay(p.fecha_hora, selectedDate));
    const uniqueCinemas = new Set(pasesDelDia.map(p => p.cine));
    return ["Todos", ...Array.from(uniqueCinemas).sort()];
  }, [futurePases, selectedDate]);

  // RESETEAR CINE SI NO EXISTE ESE DÍA
  useEffect(() => {
    if (selectedCinema !== "Todos" && !availableCinemas.includes(selectedCinema)) {
        setSelectedCinema("Todos");
    }
  }, [selectedDate, availableCinemas, selectedCinema]);


  // 🚨 3. LOGICA DE FILTRADO MAESTRA (AQUÍ ESTÁ LA MAGIA) 🚨
  const filteredPases = useMemo(() => {
    let data = futurePases;
    
    // A. Filtro por Fecha
    data = data.filter((pase) => isSameDay(pase.fecha_hora, selectedDate));
    
    // B. Filtro por Cine
    if (selectedCinema !== "Todos") {
        data = data.filter((pase) => pase.cine === selectedCinema);
    }

    // C. 🆕 Filtro por Hora (Rango)
    if (timeRange[0] > 6 || timeRange[1] < 24) {
      data = data.filter((pase) => {
        const hour = new Date(pase.fecha_hora).getHours();
        // Si el rango acaba en 24, incluimos las de la madrugada (0, 1, 2) del día siguiente
        // Pero por simplicidad, vamos a filtrar horas exactas del día seleccionado
        return hour >= timeRange[0] && hour < timeRange[1];
      });
    }

    // D. 🆕 Filtro Día del Espectador
    if (spectatorOnly) {
      data = data.filter((pase) => isDiaEspectador(pase.cine, pase.fecha_hora));
    }

    // E. Filtro Especiales
    if (onlySpecials) {
      data = data.filter((pase) => pase.es_evento_especial);
    }

    return data;
  }, [futurePases, selectedDate, selectedCinema, timeRange, spectatorOnly, onlySpecials]);


  // 4. AGRUPACIÓN (Esto sigue igual, pero usa 'filteredPases' que ya viene limpito)
  const groupedMovies = useMemo(() => {
  const movies = Object.values(
    filteredPases.reduce((acc, pase) => {
      const rawTitle = pase.pelicula?.titulo || "Título Desconocido";
      const titleKey = normalizeTitle(rawTitle);

      if (!acc[titleKey]) {
        acc[titleKey] = {
          id: pase.pelicula?.id,
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
    }, {}) // ✅ IMPORTANTE: objeto vacío
  )
    .filter((movie) => {
      if (!searchTerm) return true;
      return cleanForSearch(movie.titulo || "").includes(cleanForSearch(searchTerm));
    })
    .sort((a, b) => {
      const at = a.titulo || "";
      const bt = b.titulo || "";

      if (sortBy === "nota") {
        const diffNota = (b.nota ?? 0) - (a.nota ?? 0);
        if (diffNota !== 0) return diffNota;

        const diffSesiones = (b.total_sesiones ?? 0) - (a.total_sesiones ?? 0);
        if (diffSesiones !== 0) return diffSesiones;

        return at.localeCompare(bt);
      }

      if (sortBy === "titulo") {
        return at.localeCompare(bt);
      }

      // default: "sesiones"
      const diffSesiones = (b.total_sesiones ?? 0) - (a.total_sesiones ?? 0);
      if (diffSesiones !== 0) return diffSesiones;

      return at.localeCompare(bt);
    });

  return movies;
}, [filteredPases, searchTerm, sortBy]); // ✅ sortBy aquí


  // 5. LÓGICA DE DÍAS
  const allDays = useMemo(() => {
      return futurePases.reduce((acc, pase) => {
        const date = pase.fecha_hora;
        const exists = acc.find((d) => isSameDay(d, date));
        if (!exists) acc.push(date);
        return acc;
      }, []);
  }, [futurePases]);

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

  const resetFilters = () => {
    setSelectedCinema("Todos");
    setTimeRange([6, 24]);
    setSpectatorOnly(false);
    setOnlySpecials(false);
  }

  return (
    <main className="min-h-screen bg-gray-900 text-white p-4 md:p-8 font-sans pb-24">
      
      <Header />

      {/* --- NUEVA BARRA DE CONTROLES --- */}
      <div className="flex flex-col xl:flex-row items-center justify-between gap-6 mt-8 md:mt-10 max-w-9xl mx-auto w-full sticky top-0 z-40 py-4 bg-gray-900/95 backdrop-blur-sm border-b border-white/5">
        
        {/* SELECTOR DE FECHA (IZQUIERDA) */}
        <div className="w-full xl:w-auto overflow-x-auto no-scrollbar">
            <DateSelector 
                visibleDays={visibleDays}
                selectedDate={selectedDate}
                setSelectedDate={setSelectedDate}
                weekOffset={weekOffset}
                changeWeek={changeWeek}
                hasMoreDays={hasMoreDays}
            />
        </div>

        {/* ZONA DERECHA: BUSCADOR + BOTÓN FILTROS */}
        <div className="flex items-center gap-3 w-full xl:w-auto">
            
            {/* Buscador Simple */}
            <div className="relative flex-grow xl:flex-grow-0 xl:w-64">
                <input 
                    type="text" 
                    placeholder="Buscar película..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-full px-4 py-3 pl-10 text-sm focus:outline-none focus:border-yellow-500 transition-colors"
                />
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400 absolute left-3.5 top-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
            </div>

            {/* 🆕 BOTÓN FILTRO (Menú Desplegable) */}
            <FilterMenu 
                availableCinemas={availableCinemas}
                selectedCinema={selectedCinema}
                setSelectedCinema={setSelectedCinema}
                timeRange={timeRange}
                setTimeRange={setTimeRange}
                spectatorOnly={spectatorOnly}
                setSpectatorOnly={setSpectatorOnly}
                onlySpecials={onlySpecials}
                setOnlySpecials={setOnlySpecials}
                resetFilters={resetFilters}
                setSortBy={setSortBy}
            />

        </div>
      </div>

      {/* YA NO NECESITAMOS FilterBar NI CinemaSelector SUELTOS */}

      {/* --- LEYENDA DE COLORES --- */}
<div className="flex justify-center items-center gap-6 mt-6 mb-2 text-xs font-medium text-gray-400 uppercase tracking-wider">
  
  {/* Leyenda Día Espectador */}
  <div className="flex items-center gap-2">
    <span className="w-3 h-3 rounded-full bg-[#42E2B8] shadow-[0_0_8px_rgba(66,226,184,0.6)]"></span>
    <span>Día del Espectador</span>
  </div>

  {/* Separador sutil */}
  <div className="w-px h-3 bg-gray-700"></div>

  {/* Leyenda Especial */}
  <div className="flex items-center gap-2">
    <span className="w-3 h-3 rounded-full bg-purple-600 shadow-[0_0_8px_rgba(147,51,234,0.6)]"></span>
    <span>Sesión Especial</span>
  </div>

</div>
      
      <div className="mt-8">
        <MovieGrid 
            groupedMovies={groupedMovies}
            searchTerm={searchTerm}
            selectedCinema={selectedCinema}
        />
      </div>

    </main>
  );
}