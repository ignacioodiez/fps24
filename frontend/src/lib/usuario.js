// Formato del nombre de usuario: copia de validar_usuario (backend/app/perfil.py), sin la lista de reservados.
// Sin imports, para poder probarlo con node (usuario.check.mjs).
export const USUARIO_MIN = 3;
export const USUARIO_MAX = 20;

// Motivo por el que el formato no vale (los mismos textos que el backend), o null
export function motivoFormato(texto) {
  const usuario = (texto ?? "").trim();
  if (usuario.length < USUARIO_MIN || usuario.length > USUARIO_MAX) {
    return `El nombre de usuario debe tener entre ${USUARIO_MIN} y ${USUARIO_MAX} caracteres`;
  }
  if (!/^[A-Za-z0-9._]+$/.test(usuario)) return "Solo puede tener letras sin tildes, números, punto y guion bajo";
  if (/^[._]|[._]$/.test(usuario)) return "No puede empezar ni acabar en punto o guion bajo";
  if (usuario.includes("..")) return "No puede tener dos puntos seguidos";
  return null;
}
