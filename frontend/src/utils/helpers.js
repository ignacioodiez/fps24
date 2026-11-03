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
  // Locale fijo: con [] el servidor (Node, en-US) y el navegador darían horas distintas al hidratar
  return date.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
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

// Sala a mostrar ("Sala 9") o null si no aporta nada: vacía o solo repite el nombre del cine
// ("Cines Verdi" en Cines Verdi, "Cine Paz" en Cine MK2 Paz). "4" -> "Sala 4", "Renoir Princesa (Sala 07)" -> "Sala 7".
const PALABRAS_VACIAS = new Set(["cine", "cines", "sala", "de", "del", "la", "el"]);
const palabras = (texto) =>
  cleanForSearch(texto).replace(/[^a-z0-9ñ]+/g, " ").split(" ").filter((p) => p && !PALABRAS_VACIAS.has(p));

export const textoSala = (sala, cine) => {
  if (!sala || !sala.trim()) return null;
  const numerada = sala.match(/sala\s+0*(\d[^)]*)/i) || sala.trim().match(/^0*(\d.*)$/);
  if (numerada) return `Sala ${numerada[1].trim()}`;
  const deCine = new Set(palabras(cine || ""));
  const propias = palabras(sala);
  if (propias.every((p) => deCine.has(p))) return null;
  return /^sala\b/i.test(sala.trim()) ? sala.trim() : `Sala ${sala.trim()}`;
};
