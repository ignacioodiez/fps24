"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { fetchConAuth } from "@/lib/api";

// Se resuelve al compilar (NEXT_PUBLIC_*): igual en servidor y navegador, sin desajustes de hidratación
export const AUTH_DISPONIBLE = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
);

const AuthContext = createContext({ usuario: null, cargando: false, entrar: async () => {}, entrarConGoogle: async () => {}, salir: async () => {}, abrirLogin: () => {}, peticionLogin: null });

export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(AUTH_DISPONIBLE);
  // Petición de abrir el panel de inicio de sesión desde cualquier sitio (p. ej. "Añadir al diario"); la atiende PanelLogin
  const [peticionLogin, setPeticionLogin] = useState(null);
  // Aviso para lectores de pantalla; aquí y no en la barra porque al salir desde /perfil la página cambia
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    const sb = supabase();
    if (!sb) return;
    // Emite INITIAL_SESSION al suscribirse, y SIGNED_IN al volver del magic link
    const { data } = sb.auth.onAuthStateChange((evento, sesion) => {
      setUsuario(sesion?.user ?? null);
      setCargando(false);
      if (evento === "SIGNED_OUT") setAviso("Has cerrado sesión");
      if (evento === "SIGNED_IN") setAviso("");
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

  // Redirige a Google; vuelve a la misma página y onAuthStateChange recoge la sesión
  const entrarConGoogle = async () => {
    const sb = supabase();
    if (!sb) return;
    const { error } = await sb.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin + window.location.pathname },
    });
    if (error) throw error;
  };

  // Objeto nuevo en cada llamada: dos peticiones seguidas con el mismo mensaje vuelven a abrir el panel
  const abrirLogin = (mensaje = "") => setPeticionLogin({ mensaje });

  const salir = async () => {
    await supabase()?.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ usuario, cargando, entrar, entrarConGoogle, salir, abrirLogin, peticionLogin }}>
      {children}
      <p role="status" aria-live="polite" className="sr-only">{aviso}</p>
    </AuthContext.Provider>
  );
}
