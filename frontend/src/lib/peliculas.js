import { normalizeTitle } from "@/utils/helpers";

// Agrupa pases por película y los ordena como el MovieGrid
export const groupMovies = (pases, sortBy) =>
  Object.values(
    pases.reduce((acc, pase) => {
      const rawTitle = pase.pelicula?.titulo || "Título Desconocido";
      const titleKey = normalizeTitle(rawTitle);

      if (!acc[titleKey]) {
        acc[titleKey] = {
          id: pase.pelicula?.id,
          titulo: rawTitle.toUpperCase(),
          poster: pase.pelicula?.poster_url,
          backdrop: pase.pelicula?.backdrop_url,
          nota: pase.pelicula?.nota_tmdb || 0,
          anio: pase.pelicula?.anio || null,
          fecha_estreno: pase.pelicula?.fecha_estreno || null, // "YYYY-MM-DD" (Madrid) o null
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

// Backdrop de la primera película de HOY (Madrid) que lo tenga, en el orden por defecto del MovieGrid
export const backdropDeHoy = (pases) => {
  // fecha_hora viene en hora local de Madrid sin zona: comparamos el prefijo YYYY-MM-DD
  const hoy = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Madrid" });
  const pasesHoy = pases.filter((p) => p.fecha_hora?.startsWith(hoy));
  return groupMovies(pasesHoy, "sesiones").find((m) => m.backdrop)?.backdrop || null;
};
