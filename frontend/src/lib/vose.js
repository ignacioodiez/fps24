// Página /cine-vose-madrid: lo comparten la página y el sitemap

export const DIAS_VOSE = 7; // hoy y los 6 siguientes (GET /pases/vose?dias=7)
// Por debajo, la página es fina: noindex y fuera del sitemap. ~3 sesiones al día en toda la semana
export const MINIMO_SESIONES_VOSE = 20;

// datos de /pases/vose -> [{ fecha, sesiones, peliculas: [{ pelicula, cines: [[nombre, pases]] }] }] por día;
// las películas, por número de sesiones ese día (y título); los cines, por su primera sesión. Cada pase lleva lo que
// usan el chip y el modal de la sesión, con una ficha mínima de la película: van serializados al navegador.
export function agruparVose({ peliculas, pases }) {
  const porId = new Map(peliculas.map((p) => [p.id, p]));
  const minimas = new Map(peliculas.map(({ id, titulo, poster_url }) => [id, { id, titulo, poster_url }]));
  const dias = new Map();
  for (const pase of pases) {
    const pelicula = porId.get(pase.pelicula_id);
    if (!pelicula) continue;
    const fecha = pase.fecha_hora.slice(0, 10);
    if (!dias.has(fecha)) dias.set(fecha, new Map());
    const pelis = dias.get(fecha);
    if (!pelis.has(pelicula.id)) pelis.set(pelicula.id, { pelicula, cines: new Map(), sesiones: 0 });
    const item = pelis.get(pelicula.id);
    item.sesiones += 1;
    if (!item.cines.has(pase.cine)) item.cines.set(pase.cine, []);
    const { id, fecha_hora, idioma, precio, link_compra, cine_slug } = pase;
    item.cines.get(pase.cine).push({ id, fecha_hora, idioma, precio, link_compra, cine_slug, pelicula: minimas.get(pelicula.id) });
  }
  return [...dias.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([fecha, pelis]) => ({
    fecha,
    sesiones: [...pelis.values()].reduce((n, p) => n + p.sesiones, 0),
    peliculas: [...pelis.values()]
      .sort((a, b) => b.sesiones - a.sesiones || a.pelicula.titulo.localeCompare(b.pelicula.titulo, "es"))
      .map(({ pelicula, cines }) => ({
        pelicula,
        cines: [...cines.entries()]
          .map(([cine, ps]) => [cine, ps.sort((a, b) => a.fecha_hora.localeCompare(b.fecha_hora))])
          .sort(([, a], [, b]) => a[0].fecha_hora.localeCompare(b[0].fecha_hora)),
      })),
  }));
}

// Los n cines con más sesiones en VO: [{ nombre, slug, sesiones }]
export function cinesConMasVose(pases, n = 3) {
  const cuenta = new Map();
  for (const { cine, cine_slug } of pases) {
    const c = cuenta.get(cine_slug) ?? { nombre: cine, slug: cine_slug, sesiones: 0 };
    c.sesiones += 1;
    cuenta.set(cine_slug, c);
  }
  return [...cuenta.values()].sort((a, b) => b.sesiones - a.sesiones || a.nombre.localeCompare(b.nombre, "es")).slice(0, n);
}
