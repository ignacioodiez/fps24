import Link from "next/link";
import { AtribucionPoster } from "@/components/Avatar";
import { BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import { ListaDiario } from "@/components/Perfil";
import { MarcoPerfil, leerPerfil, metadatos, paginaDe } from "../comun";

export const generateMetadata = ({ params }) => metadatos(params, "Diario");

function Diario({ usuario, diario }) {
  if (!diario) return <p className="mt-10 text-center text-muted">Este diario no es público.</p>;
  if (!diario.total) return <p className="mt-10 text-center text-muted">Todavía no hay películas en este diario.</p>;
  const paginas = Math.ceil(diario.total / diario.por_pagina);
  const enlace = (n) => `/u/${usuario}/diario${n > 1 ? `?pagina=${n}` : ""}`;
  return (
    <>
      {diario.entradas.length ? <ListaDiario entradas={diario.entradas} /> : <p className="mt-6 text-muted">No hay más entradas.</p>}
      <AtribucionPoster className="mt-4" />
      {paginas > 1 && (
        <nav aria-label="Páginas del diario" className="mt-6 flex flex-wrap items-center justify-center gap-3 text-sm">
          {diario.pagina > 1 && <Link href={enlace(diario.pagina - 1)} className={BOTON_SECUNDARIO}>Más recientes</Link>}
          <span className="text-muted">Página {Math.min(diario.pagina, paginas)} de {paginas}</span>
          {diario.pagina < paginas && <Link href={enlace(diario.pagina + 1)} className={BOTON_SECUNDARIO}>Anteriores</Link>}
        </nav>
      )}
    </>
  );
}

// Pestaña Diario: completo, por meses y paginado como el endpoint público
export default async function DiarioPublicoPage({ params, searchParams }) {
  const [{ usuario }, { pagina }] = await Promise.all([params, searchParams]);
  const perfil = await leerPerfil(usuario, paginaDe(pagina));
  return (
    <MarcoPerfil perfil={perfil} pestana="diario">
      <Diario usuario={perfil.usuario} diario={perfil.diario} />
    </MarcoPerfil>
  );
}
