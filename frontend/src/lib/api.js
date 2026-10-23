import { supabase } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// fetch a la API con el token de la sesión de Supabase (si la hay) en Authorization
export async function fetchConAuth(ruta, opciones = {}) {
  const { data } = (await supabase()?.auth.getSession()) ?? {};
  const token = data?.session?.access_token;
  const headers = { ...opciones.headers, ...(token && { Authorization: `Bearer ${token}` }) };
  return fetch(`${API_URL}${ruta}`, { ...opciones, headers });
}
