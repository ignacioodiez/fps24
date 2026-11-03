import Cartelera from "@/components/Cartelera";
import AtajosPortada from "@/components/AtajosPortada";

// Título y descripción, los del layout. shortcut: la cartelera se pinta en el cliente (1,2 MB de /pases); pasarla a ISR es tarea aparte
export const metadata = { alternates: { canonical: "/" } };

export default function Home() {
  return <Cartelera atajos={<AtajosPortada />} />;
}
