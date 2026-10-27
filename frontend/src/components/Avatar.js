// Avatar del perfil: el recorte circular del póster elegido o las iniciales sobre su color.
// `avatar` es el que ya resuelve la API ({ tipo, color, fondo, poster_url }); sin él, el color primario.
// Sin `etiqueta` es decorativo (aria-hidden), para cuando el nombre ya está escrito al lado.

// 1-2 letras: la inicial de las dos primeras partes (ana.diez -> AD) o, si es una sola, la primera
export const iniciales = (usuario = "") => {
  const partes = usuario.split(/[._]+/).filter(Boolean);
  return (partes.length > 1 ? partes[0][0] + partes[1][0] : usuario.slice(0, 1)).toUpperCase();
};

export default function Avatar({ usuario, avatar, className = "w-10 h-10 text-base", etiqueta = `Avatar de @${usuario}` }) {
  const accesible = etiqueta ? { role: "img", "aria-label": etiqueta } : { "aria-hidden": true };
  const forma = `inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full ${className}`;
  if (avatar?.tipo === "pelicula" && avatar.poster_url) {
    return (
      <span {...accesible} className={`${forma} bg-surface border border-line`}>
        <img src={avatar.poster_url} alt="" className="w-full h-full object-cover" />
      </span>
    );
  }
  return (
    <span {...accesible} style={avatar?.fondo ? { backgroundColor: avatar.fondo } : undefined}
          className={`${forma} bg-primary font-display font-bold text-white select-none`}>
      {iniciales(usuario)}
    </span>
  );
}

// TMDB pide atribución donde salga una imagen suya
export function AtribucionPoster({ className = "" }) {
  return (
    <p className={`text-xs text-muted ${className}`}>
      Póster: <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">TMDB</a>
    </p>
  );
}
