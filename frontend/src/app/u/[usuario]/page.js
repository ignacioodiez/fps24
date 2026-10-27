import { PestanaPerfil } from "@/components/PerfilVistas";
import { MarcoPerfil, leerPerfil, metadatos } from "./comun";

export const generateMetadata = ({ params }) => metadatos(params);

// Pestaña Perfil: actividad reciente y, al lado, cines y diario (solo lo que el dueño hace público)
export default async function PerfilPublicoPage({ params }) {
  const { usuario } = await params;
  const perfil = await leerPerfil(usuario);
  return (
    <MarcoPerfil perfil={perfil} pestana="perfil">
      <PestanaPerfil usuario={perfil.usuario} entradas={perfil.diario?.entradas} total={perfil.diario?.total} cines={perfil.cines} />
    </MarcoPerfil>
  );
}
