const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Newsletter semanal (backend/app/newsletter/rutas.py). La API responde lo mismo exista o no el email.
// web: campo trampa, vacío salvo en bots.
export async function suscribir(email, web = "") {
  const res = await fetch(`${API_URL}/newsletter/suscribir`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, web }),
  });
  if (res.status === 429) throw new Error("Demasiados intentos. Prueba de nuevo dentro de un rato.");
  if (res.status === 422) throw new Error("Escribe un email válido.");
  if (!res.ok) throw new Error("No hemos podido apuntarte. Inténtalo de nuevo.");
  return (await res.json()).mensaje;
}
