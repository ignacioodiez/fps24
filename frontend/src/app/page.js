"use client";

import { useState, useEffect, useMemo } from "react";
// Importamos Helpers
import { isSameDay, cleanForSearch, isDiaEspectador } from "@/utils/helpers"; // 🆕 Importamos isDiaEspectador
// Importamos Componentes
import Header from "@/components/Header";
import DateSelector from "@/components/DateSelector";
import MovieGrid from "@/components/MovieGrid";
import FilterMenu from "@/components/FilterMenu"; 
import SeccionDestacadas from "@/components/SeccionDestacadas";
import { groupMovies, backdropDeHoy } from "@/lib/peliculas";
import { guardarDia } from "@/lib/diaSeleccionado";


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

   

  // 1. DATA LOADING
   // 👇 TRACKING DE NAVEGACIÓN
 



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

  // La vista rápida (modal) muestra primero las sesiones del día elegido
  useEffect(() => guardarDia(selectedDate), [selectedDate]);

  // CINE EFECTIVO: si el elegido no tiene sesiones ese día, se usa "Todos" (derivado, sin efecto)
  const cineActivo = availableCinemas.includes(selectedCinema) ? selectedCinema : "Todos";


  // 🚨 3. LOGICA DE FILTRADO MAESTRA (AQUÍ ESTÁ LA MAGIA) 🚨
  const filteredPases = useMemo(() => {
    let data = futurePases;
    
    // A. Filtro por Fecha
    data = data.filter((pase) => isSameDay(pase.fecha_hora, selectedDate));
    
    // B. Filtro por Cine
    if (cineActivo !== "Todos") {
        data = data.filter((pase) => pase.cine === cineActivo);
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
  }, [futurePases, selectedDate, cineActivo, timeRange, spectatorOnly, onlySpecials]);


  // 4. AGRUPACIÓN (Esto sigue igual, pero usa 'filteredPases' que ya viene limpito)
  const groupedMovies = useMemo(() => {
    return groupMovies(filteredPases, sortBy).filter((movie) => {
      if (!searchTerm) return true;
      return cleanForSearch(movie.titulo || "").includes(cleanForSearch(searchTerm));
    });
  }, [filteredPases, searchTerm, sortBy]);

  // 4.5 FONDO DEL HEADER: fijo en la película de hoy, no depende de filtros ni del día elegido
  const headerBackdrop = useMemo(() => backdropDeHoy(pases), [pases]);


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

  // Desde el calendario: el mismo efecto que pulsar en la tira, pasando a la página de 7 días que lo contiene
  const elegirDia = (dateStr) => {
    setWeekOffset(Math.floor(allDays.indexOf(dateStr) / DAYS_PER_PAGE));
    setSelectedDate(new Date(dateStr));
  };

  const resetFilters = () => {
    setSelectedCinema("Todos");
    setTimeRange([6, 24]);
    setSpectatorOnly(false);
    setOnlySpecials(false);
  }

  return (
    <main className="min-h-screen bg-background text-foreground pb-24">
      
      {/* Header a ancho completo, fuera del contenedor con padding */}
      <Header backdrop={headerBackdrop} />

      <div className="px-4 md:px-8">

      {/* Destacadas de la semana: se ocultan al buscar o filtrar por cine */}
      <SeccionDestacadas oculta={Boolean(searchTerm) || cineActivo !== "Todos"} />

      {/* --- NUEVA BARRA DE CONTROLES --- */}
      <div className="flex flex-col xl:flex-row items-center justify-between gap-6 mt-8 md:mt-10 max-w-9xl mx-auto w-full sticky top-0 z-40 py-4 bg-background border-b border-line">
        
        {/* SELECTOR DE FECHA (IZQUIERDA) */}
        {/* Sin overflow aquí: recortaría el calendario; la tira ya se desplaza dentro de DateSelector */}
        <div className="w-full xl:w-auto min-w-0">
            <DateSelector 
                visibleDays={visibleDays}
                allDays={allDays}
                selectedDate={selectedDate}
                setSelectedDate={setSelectedDate}
                elegirDia={elegirDia}
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
                    className="w-full bg-background border border-line text-foreground placeholder-muted rounded-full px-4 py-3 pl-10 text-sm focus:outline-none focus:border-primary transition-colors"
                />
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-muted absolute left-3.5 top-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
            </div>

            {/* 🆕 BOTÓN FILTRO (Menú Desplegable) */}
            <FilterMenu 
                availableCinemas={availableCinemas}
                selectedCinema={cineActivo}
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
<div className="flex justify-center items-center gap-6 mt-6 mb-2 text-xs font-medium text-muted uppercase tracking-wider">
  
  {/* Leyenda Día Espectador */}
  <div className="flex items-center gap-2">
    <span className="w-3 h-3 rounded-full bg-accent"></span>
    <span>Día del Espectador</span>
  </div>

  {/* Separador sutil */}
  <div className="w-px h-3 bg-line"></div>

  {/* Leyenda Especial */}
  <div className="flex items-center gap-2">
    <span className="w-3 h-3 rounded-full bg-primary"></span>
    <span>Sesión Especial</span>
  </div>

</div>
      
      <div className="mt-8">
        <MovieGrid 
            groupedMovies={groupedMovies}
            selectedDate={selectedDate}
            searchTerm={searchTerm}
            selectedCinema={cineActivo}
        />
      </div>
      </div>

    </main>
  );
}