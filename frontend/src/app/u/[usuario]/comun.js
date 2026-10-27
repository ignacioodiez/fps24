import { notFound } from "next/navigation";
import TodayHeader from "@/components/TodayHeader";
import { SiSoyYo } from "@/components/Perfil";
import { CabeceraPerfil, PestanasPerfil } from "@/components/PerfilVistas";

// Lo común a /u/<usuario>, /u/<usuario>/diario y /u/<usuario>/cines (vista pública, en el servidor)

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Sin caché: si alguien pasa su perfil o su diario a privado, deja de verse al momento
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

// Pestañas con contenido para un visitante (Perfil siempre)
const visibles = (perfil) => [
  "perfil",
  ...(perfil.diario?.total > 0 ? ["diario"] : []),
  ...(perfil.cines?.length > 0 ? ["cines"] : []),
];

// Cabecera, cifras que el visitante puede ver y pestañas; debajo, la pestaña. Si quien mira es el dueño, SiSoyYo
// cambia todo por su vista (con sus datos, aunque sean privados).
export function MarcoPerfil({ perfil, pestana, children }) {
  const cifras = {
    entradas: perfil.cifras?.entradas,
    este_anio: perfil.cifras?.este_anio,
    cines: perfil.cines ? perfil.cines.length : undefined,
  };
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <SiSoyYo>
        <div className="max-w-5xl mx-auto px-4 md:px-6 py-8">
          <CabeceraPerfil perfil={perfil} cifras={cifras} />
          <PestanasPerfil usuario={perfil.usuario} actual={pestana} visibles={visibles(perfil)} />
          {children}
        </div>
      </SiSoyYo>
    </main>
  );
}
