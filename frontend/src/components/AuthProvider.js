"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { fetchConAuth } from "@/lib/api";

// Se resuelve al compilar (NEXT_PUBLIC_*): igual en servidor y navegador, sin desajustes de hidratación
export const AUTH_DISPONIBLE = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
);

const AuthContext = createContext({ usuario: null, cargando: false, entrar: async () => {}, salir: async () => {} });

export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(AUTH_DISPONIBLE);

  useEffect(() => {
    const sb = supabase();
    if (!sb) return;
    // Emite INITIAL_SESSION al suscribirse, y SIGNED_IN al volver del magic link
    const { data } = sb.auth.onAuthStateChange((_evento, sesion) => {
      setUsuario(sesion?.user ?? null);
      setCargando(false);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  // Comprobación manual desde la consola del navegador: await comprobarMe()
  useEffect(() => {
    if (!usuario) return;
    window.comprobarMe = () => fetchConAuth("/me").then((res) => res.json());
    return () => delete window.comprobarMe;
  }, [usuario]);

  const entrar = async (email) => {
    const { error } = await supabase().auth.signInWithOtp({
      email,
      options: { emailRedirectTo: window.location.origin },
    });
    if (error) throw error;
  };

  const salir = async () => {
    await supabase()?.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ usuario, cargando, entrar, salir }}>
      {children}
    </AuthContext.Provider>
  );
}
