// Usuario de Letterboxd para la validación en vivo de /perfil/editar: la misma regla que validar_letterboxd
// (backend/app/perfil.py), que es quien decide al guardar. Vacío -> {}; si no, { usuario } o { motivo }.
const NO_USUARIO = new Set("film films list lists members search journal tag director actor settings activity".split(" "));

export function leerLetterboxd(texto) {
  let valor = texto.trim();
  if (!valor) return {};
  valor = (valor.match(/^(?:https?:\/\/)?(?:www\.)?letterboxd\.com\/([^/?#]*)/i)?.[1] ?? valor).replace(/^@/, "");
  if (!/^[A-Za-z0-9_]{2,20}$/.test(valor) || NO_USUARIO.has(valor.toLowerCase())) {
    return { motivo: "Escribe tu usuario de Letterboxd (de 2 a 20 letras, números o _) o pega el enlace a tu perfil" };
  }
  return { usuario: valor };
}
