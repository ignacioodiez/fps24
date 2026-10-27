import { notFound } from "next/navigation";
import TodayHeader from "@/components/TodayHeader";
import { SiSoyYo } from "@/components/Perfil";
import PerfilAjeno from "@/components/PerfilAjeno";

// Lo común a /u/<usuario>, /u/<usuario>/diario y /u/<usuario>/cines (vista pública, en el servidor)

// Solo en el servidor: API_URL_INTERNA (Docker) si existe; si no, la pública
const API = process.env.API_URL_INTERNA || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Sin caché y SIN token: el HTML del servidor solo lleva lo público (de un perfil "solo amigos", la tarjeta mínima).
// Lo que se ve por ser amigo lo pide el navegador con su sesión (PerfilAjeno), con la respuesta marcada private, no-store.
// notFound() con el 404 de la API, que es el mismo para un perfil privado y uno inexistente (not-found.js).
export async function leerPerfil(usuario, pagina = 1) {
  const res = await fetch(`${API}/u/${encodeURIComponent(usuario)}?pagina=${pagina}`, { cache: "no-store" });
  if (res.status === 404) notFound();
  if (!res.ok) throw new Error(`/u/${usuario}: HTTP ${res.status}`);
  return res.json();
}

// ?pagina=N; cualquier otra cosa, la primera
export const paginaDe = (texto) => Math.min(Math.max(Number.parseInt(texto, 10) || 1, 1), 10000);

// Fuera de buscadores (y del sitemap): un perfil público se comparte con el enlace, no se indexa
export async function metadatos(params, seccion) {
  const { usuario } = await params;
  const perfil = await leerPerfil(usuario);
  return { title: `@${perfil.usuario}${seccion ? ` · ${seccion}` : ""} - FPS24`, robots: { index: false, follow: false } };
}

// Si quien mira es el dueño, SiSoyYo cambia todo por su vista (con sus datos, aunque sean privados); si no, PerfilAjeno.
export function MarcoPerfil({ perfil, pestana, pagina }) {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <SiSoyYo>
        <PerfilAjeno inicial={perfil} pestana={pestana} pagina={pagina} />
      </SiSoyYo>
    </main>
  );
}
