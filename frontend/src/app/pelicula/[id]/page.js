import { notFound } from "next/navigation";
import Header from "@/components/Header";
// Mismos bloques que la vista rápida (modal) y la cartelera de la portada
import { ChipDato, ChipsGeneros, LineaDireccion, NotaPelicula, duracionTexto } from "@/components/FichaPelicula";
import BotonDiario from "@/components/BotonDiario";
import { SesionesPelicula, Trailer } from "@/components/PeliculaCliente";
import { hoyMadrid } from "@/lib/fechasMadrid";

// En el servidor para que buscadores vean ficha y sesiones. Lee ?dia=, así que se pinta en cada petición; los datos, caché de 5 min
const REVALIDAR = 300;

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITIO = "https://fps24.es";

// Como /cines/[slug]: notFound() (404 real) solo con un 404 de la API; cualquier otro fallo se lanza
async function leerPelicula(id) {
  const res = await fetch(`${API}/pelicula/${encodeURIComponent(id)}`, { next: { revalidate: REVALIDAR } });
  if (res.status === 404 || res.status === 422) notFound(); // 422: id no numérico
  if (!res.ok) throw new Error(`/pelicula/${id}: HTTP ${res.status}`);
  return res.json();
}

// Sesiones desde hoy (Madrid); fecha_hora viene en hora de Madrid sin zona
const proximos = (movie) => {
  const hoy = hoyMadrid();
  return (movie.pases || []).filter((p) => p.fecha_hora.slice(0, 10) >= hoy);
};

export async function generateMetadata({ params }) {
  const { id } = await params;
  const movie = await leerPelicula(id);
  const pases = proximos(movie);
  const cines = [...new Set(pases.map((p) => p.cine))];
  const vo = pases.some((p) => /^VO/i.test(p.idioma || ""));
  const ficha = [movie.director, movie.anio].filter(Boolean).join(", ");
  const title = `${movie.titulo} en cines de Madrid · horarios${vo ? " y versión original" : ""} | fps24`;
  const description = cines.length
    ? `Horarios de «${movie.titulo}»${ficha ? ` (${ficha})` : ""} en ${cines.length === 1 ? cines[0] : `${cines.length} cines de Madrid: ${cines.slice(0, 3).join(", ")}${cines.length > 3 ? " y otros" : ""}`}.${vo ? " Sesiones en VOSE." : ""} Precios y entradas.`
    : `«${movie.titulo}»${ficha ? ` (${ficha})` : ""}: ahora mismo sin sesiones en los cines de Madrid.`;
  const url = `${SITIO}/pelicula/${movie.id}`;
  return {
    title,
    description,
    alternates: { canonical: url },
    // Sin sesiones la página es fina y no está en el sitemap: fuera del índice, pero se siguen sus enlaces
    ...(pases.length === 0 && { robots: { index: false, follow: true } }),
    openGraph: { title, description, url, type: "video.movie", ...(movie.poster_url && { images: [movie.poster_url] }) },
    twitter: { card: movie.poster_url ? "summary_large_image" : "summary", title, description },
  };
}

// Movie de schema.org solo con los datos que tenemos
const jsonLd = (movie) => ({
  "@context": "https://schema.org",
  "@type": "Movie",
  name: movie.titulo,
  url: `${SITIO}/pelicula/${movie.id}`,
  ...(movie.titulo_original && movie.titulo_original !== movie.titulo && { alternateName: movie.titulo_original }),
  ...(movie.poster_url && { image: movie.poster_url }),
  ...(movie.sinopsis && { description: movie.sinopsis }),
  ...(movie.director && { director: movie.director.split(",").map((nombre) => ({ "@type": "Person", name: nombre.trim() })) }),
  ...(movie.fecha_estreno && { datePublished: movie.fecha_estreno }),
  ...(movie.duracion > 0 && { duration: `PT${movie.duracion}M` }),
  ...(movie.generos && { genre: movie.generos.split(",").map((g) => g.trim()) }),
});

export default async function MovieDetail({ params, searchParams }) {
  const [{ id }, { dia }] = await Promise.all([params, searchParams]); // dia: de una tarjeta con sesión sugerida
  const movie = await leerPelicula(id);

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      {/* "<" escapado: el JSON no puede cerrar el <script> */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd(movie)).replace(/</g, "\\u003c") }} />

      <Header backdrop={movie.backdrop_url} showTitle={false} />

      {/* Ficha bajo el Header */}
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row gap-8 items-end">
            <div className="hidden md:flex w-48 aspect-[2/3] shrink-0 rounded-2xl overflow-hidden border border-line bg-surface items-center justify-center">
                {movie.poster_url ? (
                    <img src={movie.poster_url} alt={`Póster de ${movie.titulo}`} className="w-full h-full object-cover" />
                ) : (
                    <span className="p-3 text-center font-display font-bold text-muted">{movie.titulo}</span>
                )}
            </div>

            <div className="flex-1 mb-2">
                <h1 className="text-4xl md:text-6xl font-bold font-display uppercase leading-none text-foreground">
                    {movie.titulo}
                </h1>
                {movie.titulo_original && <p className="text-xl text-muted mt-2 font-display">{movie.titulo_original}</p>}

                <LineaDireccion director={movie.director} className="mt-2" />

                <div className="flex flex-wrap items-center gap-2 mt-4">
                    {movie.anio && <ChipDato>{movie.anio}</ChipDato>}
                    {movie.duracion > 0 && <ChipDato>{duracionTexto(movie.duracion)}</ChipDato>}
                    <NotaPelicula nota={movie.nota_tmdb} votos={movie.votos} />
                    {movie.tmdb_id && (
                        <a href={`https://letterboxd.com/tmdb/${movie.tmdb_id}`} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold bg-accent-soft text-foreground px-2 py-1 rounded-lg border border-accent hover:bg-accent transition-colors">
                            Letterboxd
                        </a>
                    )}
                </div>

                <BotonDiario pelicula={movie} dia={dia} className="mt-4" />
            </div>
      </div>

      {/* --- CONTENIDO PRINCIPAL --- */}
      <div className="max-w-6xl mx-auto px-6 py-10">

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
            {/* IZQUIERDA: SINOPSIS + TRÁILER */}
            <div className="lg:col-span-1 space-y-8">

                <div>
                    <h2 className="text-xl font-bold font-display text-primary mb-2 uppercase">Sinopsis</h2>
                    <p className="text-foreground leading-relaxed text-lg">
                        {movie.sinopsis || "No hay sinopsis disponible."}
                    </p>
                </div>

                {movie.generos && (
                    <div>
                        <h2 className="text-sm font-bold text-muted mb-2 uppercase">Géneros</h2>
                        <ChipsGeneros generos={movie.generos} />
                    </div>
                )}

                {movie.youtube_id && (
                    <div className="pt-4 border-t border-line">
                        <h2 className="text-xl font-bold font-display text-foreground mb-4 flex items-center gap-2">
                             Tráiler
                        </h2>
                        <div className="rounded-xl overflow-hidden border border-line">
                            <Trailer id={movie.youtube_id} titulo={movie.titulo} />
                        </div>
                    </div>
                )}
            </div>

            {/* DERECHA: SESIONES */}
            <div className="lg:col-span-2">
                <SesionesPelicula movie={movie} dia={dia} />
            </div>
        </div>

        {movie.imagenes_galeria && movie.imagenes_galeria.length > 0 && (
            <div className="mt-16 pt-10 border-t border-line">
                <h2 className="text-2xl font-bold font-display text-foreground mb-6 flex items-center gap-2">
                    Galería de Imágenes
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    {movie.imagenes_galeria.map((imgUrl, index) => (
                        <div key={index} className="relative group rounded-xl overflow-hidden aspect-video border border-line">
                            <img
                                src={imgUrl}
                                alt={`${movie.titulo}: imagen ${index + 1}`}
                                loading="lazy"
                                className="w-full h-full object-cover"
                            />
                        </div>
                    ))}
                </div>
            </div>
        )}

      </div>
    </main>
  );
}
