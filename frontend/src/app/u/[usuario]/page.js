import { MarcoPerfil, leerPerfil, metadatos } from "./comun";

export const generateMetadata = ({ params }) => metadatos(params);

// Pestaña Perfil: actividad reciente y, al lado, cines y diario (solo lo que quien mira puede ver)
export default async function PerfilPublicoPage({ params }) {
  const { usuario } = await params;
  return <MarcoPerfil perfil={await leerPerfil(usuario)} pestana="perfil" />;
}
