import { notFound } from "next/navigation";

// "Mis sesiones" es privada y el servidor no sabe quién mira: siempre el 404 neutro de /u/<usuario> (not-found.js),
// donde SiSoyYo le enseña al dueño, con su sesión, su pestaña Sesiones.
export default function SesionesPage() {
  notFound();
}
