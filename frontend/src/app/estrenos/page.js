import PaginaSemana from "@/components/PaginaSemana";

export const metadata = {
  title: "Estrenos de la semana - FPS24",
  description: "Todas las películas que se estrenan esta semana en los cines de Madrid, con nota, cines y primera sesión.",
};

export default function EstrenosPage({ searchParams }) {
  return (
    <PaginaSemana tipo="estrenos" titulo="Estrenos" acento="text-muted" searchParams={searchParams}
                  intro="Las películas que llegan a los cines de Madrid esta semana, ordenadas por nota; las que aún no tienen valoraciones, por número de cines. Detrás, los estrenos anunciados en España que aún no tienen sesiones."
                  vacio="Esta semana no hay estrenos en cartelera. Prueba con la semana siguiente." />
  );
}
