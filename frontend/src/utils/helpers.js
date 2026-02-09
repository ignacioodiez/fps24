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