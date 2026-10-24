// Orden por cines favoritos. Las páginas públicas no dependen del usuario: esto se aplica en el cliente, con el
// cine_slug de cada pase, cuando FavoritosProvider ya conoce los favoritos (un Set de slugs).

// Favoritos primero, conservando el orden de cada grupo (sort es estable). slugDe(elemento) -> cine_slug.
export const favoritosPrimero = (lista, slugDe, favoritos) =>
  favoritos.size ? [...lista].sort((a, b) => favoritos.has(slugDe(b)) - favoritos.has(slugDe(a))) : lista;

// Sesión sugerida: la de siempre si es de un favorito; si no, la primera de un favorito ese mismo día
// (alternativas, del backend); si tampoco, la de siempre.
export const sesionSugerida = (sesion, alternativas = [], favoritos) =>
  favoritos.has(sesion.cine_slug) ? sesion : alternativas.find((p) => favoritos.has(p.cine_slug)) ?? sesion;
