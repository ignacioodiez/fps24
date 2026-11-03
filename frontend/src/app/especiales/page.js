import PaginaSemana from "@/components/PaginaSemana";

export const metadata = {
  title: "Pases especiales y ciclos de la semana en Madrid | fps24",
  alternates: { canonical: "/especiales" }, // ?semana=N es la misma página en otra semana
  description: "Clásicos, ciclos y sesiones especiales de los cines independientes de Madrid, con la mejor sesión de cada película.",
};

export default function EspecialesPage({ searchParams }) {
  return (
    <PaginaSemana tipo="especiales" titulo="Especiales" acento="text-primary" searchParams={searchParams}
                  intro="Clásicos, ciclos y pases especiales en los cines de autor de Madrid, ordenados por nota."
                  vacio="Esta semana no hay pases especiales. Prueba con la semana siguiente." />
  );
}
