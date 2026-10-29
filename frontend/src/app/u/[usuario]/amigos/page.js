import { notFound } from "next/navigation";

// "Amigos" es del dueño y el servidor no sabe quién mira: siempre el 404 neutro de /u/<usuario> (not-found.js),
// donde SiSoyYo le enseña al dueño, con su sesión, su pestaña Amigos (como Sesiones).
export default function AmigosPage() {
  notFound();
}
