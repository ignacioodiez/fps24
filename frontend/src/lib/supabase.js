import { createClient } from "@supabase/supabase-js";

let cliente;

// Cliente perezoso y solo en el navegador; null si faltan las variables (la UI de login se oculta)
export function supabase() {
  if (typeof window === "undefined") return null;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const clave = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !clave) return null;
  cliente ??= createClient(url, clave);
  return cliente;
}
