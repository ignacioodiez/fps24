import Link from "next/link";
import { notFound } from "next/navigation";
import TodayHeader from "@/components/TodayHeader";
import { BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import { CabeceraPerfil, ListaDiario, SiSoyYo } from "@/components/Perfil";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Sin caché: si alguien pasa su perfil o su diario a privado, deja de verse al momento
// notFound() con el 404 de la API, que es el mismo para un perfil privado y uno inexistente (not-found.js).
async function leerPerfil(usuario, pagina) {
  const res = await fetch(`${API}/u/${encodeURIComponent(usuario)}?pagina=${pagina}`, { cache: "no-store" });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`/u/${usuario}: HTTP ${res.status}`);
  return res.json();
}

// ?pagina=N; cualquier otra cosa, la primera
const paginaDe = (texto) => Math.min(Math.max(Number.parseInt(texto, 10) || 1, 1), 10000);

// Fuera de buscadores (y del sitemap): un perfil público se comparte con el enlace, no se indexa
const ROBOTS = { index: false, follow: false };

export async function generateMetadata({ params, searchParams }) {
  const [{ usuario }, { pagina }] = await Promise.all([params, searchParams]);
  const perfil = await leerPerfil(usuario, paginaDe(pagina));
  return { title: `@${perfil.usuario} - FPS24`, robots: ROBOTS };
}

function Diario({ usuario, diario }) {
  if (!diario) return <p className="mt-10 text-center text-muted">Este diario no es público.</p>;
  if (!diario.total) return <p className="mt-10 text-center text-muted">Todavía no hay películas en este diario.</p>;
  const paginas = Math.ceil(diario.total / diario.por_pagina);
  const enlace = (n) => `/u/${usuario}${n > 1 ? `?pagina=${n}` : ""}`;
  return (
    <>
      {diario.entradas.length ? <ListaDiario entradas={diario.entradas} /> : <p className="mt-6 text-muted">No hay más entradas.</p>}
      {paginas > 1 && (
        <nav aria-label="Páginas del diario" className="mt-6 flex items-center justify-center gap-3 text-sm">
          {diario.pagina > 1 && <Link href={enlace(diario.pagina - 1)} className={BOTON_SECUNDARIO}>Más recientes</Link>}
          <span className="text-muted">Página {Math.min(diario.pagina, paginas)} de {paginas}</span>
          {diario.pagina < paginas && <Link href={enlace(diario.pagina + 1)} className={BOTON_SECUNDARIO}>Anteriores</Link>}
        </nav>
      )}
    </>
  );
}

export default async function PerfilPublicoPage({ params, searchParams }) {
  const [{ usuario }, { pagina }] = await Promise.all([params, searchParams]);
  const perfil = await leerPerfil(usuario, paginaDe(pagina));

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      {/* Si quien mira es el dueño, SiSoyYo cambia esto por su vista (con sus datos y sus entradas) */}
      <SiSoyYo>
        <div className="max-w-3xl mx-auto px-4 md:px-6 py-8">
          <CabeceraPerfil usuario={perfil.usuario} bio={perfil.bio} />
          <h3 className="mt-8 text-xl font-display font-bold uppercase text-foreground">Diario</h3>
          <Diario usuario={perfil.usuario} diario={perfil.diario} />
        </div>
      </SiSoyYo>
    </main>
  );
}
