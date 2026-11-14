// Qué pinta SiSoyYo (components/Perfil.js) y el panel admin. Sin imports, para poder probarlo con node (siSoyYo.check.mjs).

// Los nombres son únicos sin distinguir mayúsculas: /u/nacho y /u/Nacho son el mismo perfil
export const usuarioDeRuta = (ruta) => decodeURIComponent(ruta.split("/")[2] ?? "").toLowerCase();

// "mio": la vista del dueño; "aviso": hay sesión pero GET /me/perfil falló (no se sabe si es el dueño: nunca el 404);
// "esperar": esqueleto mientras no se sabe; "ajeno": children (la vista pública o el 404 neutro).
// usuario: el de la sesión (null sin sesión). esperar: en el 404, para no enseñarle al dueño "no existe".
export function vistaSiSoyYo({ usuario, cargando, miPerfil, ruta, esperar }) {
  if (miPerfil?.usuario && miPerfil.usuario.toLowerCase() === usuarioDeRuta(ruta)) return "mio";
  if (!esperar) return "ajeno";
  if (cargando || miPerfil === undefined) return "esperar";
  if (usuario && miPerfil?.error) return "aviso";
  return "ajeno";
}

// esAdmin: true, false, undefined (aún no se sabe) o null (GET /me falló: no cuenta como "no")
export function vistaAdmin({ disponible, usuario, cargando, esAdmin }) {
  if (!disponible || (!cargando && esAdmin === false)) return "404";
  if (cargando || esAdmin === undefined) return "esperar";
  if (usuario && esAdmin === null) return "aviso";
  return esAdmin ? "panel" : "404";
}
