import { MarcoPerfil, leerPerfil, metadatos, paginaDe } from "../comun";

export const generateMetadata = ({ params }) => metadatos(params, "Diario");

// Pestaña Diario: completo, por meses y paginado como el endpoint
export default async function DiarioPublicoPage({ params, searchParams }) {
  const [{ usuario }, { pagina }] = await Promise.all([params, searchParams]);
  const n = paginaDe(pagina);
  return <MarcoPerfil perfil={await leerPerfil(usuario, n)} pestana="diario" pagina={n} />;
}
