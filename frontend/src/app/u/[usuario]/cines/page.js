import { MarcoPerfil, leerPerfil, metadatos } from "../comun";

export const generateMetadata = ({ params }) => metadatos(params, "Cines");

// Pestaña Cines: sus favoritos en tarjetas, si quien mira puede verlos
export default async function CinesPublicosPage({ params }) {
  const { usuario } = await params;
  return <MarcoPerfil perfil={await leerPerfil(usuario)} pestana="cines" />;
}
