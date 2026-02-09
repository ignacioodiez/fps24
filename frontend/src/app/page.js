"use client";

import { useState, useEffect, useMemo } from "react";
// Importamos Helpers
import { isSameDay, normalizeTitle, cleanForSearch } from "@/utils/helpers";
// Importamos Componentes
import Header from "@/components/Header";
import DateSelector from "@/components/DateSelector";
import FilterBar from "@/components/FilterBar";
import CinemaSelector from "@/components/CinemaSelector";
import MovieGrid from "@/components/MovieGrid";

export default function Home() {
  const [pases, setPases] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [weekOffset, setWeekOffset] = useState(0);
  const [onlySpecials, setOnlySpecials] = useState(false);
  const [searchTerm, setSearchTerm] = useState(""); 
  const [selectedCinema, setSelectedCinema] = useState("Todos");

  // 1. DATA LOADING
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

  // 🚨 1.5 FILTRO "ANTI-AYER" (EL PORTERO) 🚨
  // Creamos una lista maestra que solo contiene pases de HOY (00:00) en adelante.
  // Usaremos "futurePases" para TODO en lugar de "pases".
  const futurePases = useMemo(() => {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0); // Reseteamos horas para que incluya todo el día de hoy

    return pases.filter(pase => {
      const fechaPase = new Date(pase.fecha_hora);
      return fechaPase >= hoy; 
    });
  }, [pases]);

  // 2. EXTRAER CINES DISPONIBLES (Usando futurePases)
  const availableCinemas = useMemo(() => {
    const pasesDelDia = futurePases.filter(p => isSameDay(p.fecha_hora, selectedDate));
    const uniqueCinemas = new Set(pasesDelDia.map(p => p.cine));
    return ["Todos", ...Array.from(uniqueCinemas).sort()];
  }, [futurePases, selectedDate]); // <--- OJO: Dependencia futurePases

  useEffect(() => {
    if (selectedCinema !== "Todos" && !availableCinemas.includes(selectedCinema)) {
        setSelectedCinema("Todos");
    }
  }, [selectedDate, availableCinemas, selectedCinema]);


  // 3. FILTRADO PRINCIPAL (Usando futurePases)
  const filteredPases = useMemo(() => {
    let data = futurePases; // <--- Usamos la lista filtrada
    data = data.filter((pase) => isSameDay(pase.fecha_hora, selectedDate));
    
    if (onlySpecials) {
      data = data.filter((pase) => pase.es_evento_especial);
    }

    if (selectedCinema !== "Todos") {
        data = data.filter((pase) => pase.cine === selectedCinema);
    }

    return data;
  }, [futurePases, selectedDate, onlySpecials, selectedCinema]);

  // 4. AGRUPACIÓN
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
    return movies;
  }, [filteredPases, searchTerm]);

  // 5. LÓGICA DE DÍAS (Usando futurePases)
  const allDays = useMemo(() => {
      // Usamos futurePases para que los días pasados NO entren en la lista
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

  return (
    <main className="min-h-screen bg-gray-900 text-white p-4 md:p-8 font-sans pb-24">
      
      <Header />

      <div className="flex flex-col xl:flex-row items-center justify-between gap-8 mt-10 md:mt-12 max-w-9xl mx-auto w-full">
        
        <DateSelector 
            visibleDays={visibleDays}
            selectedDate={selectedDate}
            setSelectedDate={setSelectedDate}
            weekOffset={weekOffset}
            changeWeek={changeWeek}
            hasMoreDays={hasMoreDays}
        />

        <FilterBar 
            onlySpecials={onlySpecials}
            setOnlySpecials={setOnlySpecials}
            searchTerm={searchTerm}
            setSearchTerm={setSearchTerm}
        />
      </div>

      <CinemaSelector 
          availableCinemas={availableCinemas}
          selectedCinema={selectedCinema}
          setSelectedCinema={setSelectedCinema}
      />

      <MovieGrid 
          groupedMovies={groupedMovies}
          searchTerm={searchTerm}
          selectedCinema={selectedCinema}
      />

    </main>
  );
}