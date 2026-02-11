// src/utils/helpers.js

export const isSameDay = (d1, d2) => {
  const f1 = new Date(d1);
  const f2 = new Date(d2);
  return (
    f1.getDate() === f2.getDate() &&
    f1.getMonth() === f2.getMonth() &&
    f1.getFullYear() === f2.getFullYear()
  );
};

export const extractTime = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

export const normalizeTitle = (title) => {
  if (!title) return ""; 
  return title
    .toUpperCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") 
    .replace(/[^A-Z0-9]/g, ""); 
};

export const cleanForSearch = (text) => {
  return text
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
};

export const cleanCinemaName = (name) => {
    return name.replace("Cine ", "").replace("Madrid", "").replace("Cines ", "").trim();
};

export const isDiaEspectador = (cineNombre, fechaString) => {
  if (!cineNombre || !fechaString) return false;
  
  const date = new Date(fechaString);
  const diaSemana = date.getDay(); // 1 = Lunes, 2 = Martes, 3 = Miércoles...
  const nombre = cineNombre.toLowerCase();

  // 🟣 GRUPO 1: LUNES Y MIÉRCOLES (Renoir, Golem, Embajadores)
  if ((nombre.includes("renoir") || 
       nombre.includes("golem") || 
       nombre.includes("embajadores")) && (diaSemana === 1 || diaSemana === 3)) {
      return true;
  }

  // 🟢 GRUPO 2: SOLO LUNES (Verdi)
  if (nombre.includes("verdi") && diaSemana === 1) {
      return true;
  }

  // 🔵 GRUPO 3: SOLO MIÉRCOLES (Paz, Pequeño Cine Estudio, MK2)
  if ((nombre.includes("paz") || 
       nombre.includes("pequeño") || 
       nombre.includes("mk2")) && diaSemana === 3) {
      return true;
  }

  // Nota: Sala Equis, Cineteca y Doré no tienen día "fijo" o tienen precio único, así que devuelven false.
  return false;
};