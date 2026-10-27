import { TarjetasCines } from "@/components/PerfilVistas";
import { MarcoPerfil, leerPerfil, metadatos } from "../comun";

export const generateMetadata = ({ params }) => metadatos(params, "Cines");

// Pestaña Cines: sus favoritos en tarjetas, si los hace públicos
export default async function CinesPublicosPage({ params }) {
  const { usuario } = await params;
  const perfil = await leerPerfil(usuario);
  return (
    <MarcoPerfil perfil={perfil} pestana="cines">
      {perfil.cines?.length
        ? <TarjetasCines cines={perfil.cines} />
        : <p className="mt-10 text-center text-muted">Sus cines favoritos no son públicos.</p>}
    </MarcoPerfil>
  );
}
