"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { fetchConAuth } from "@/lib/api";
import { leerPerfil } from "@/lib/perfil";

// Se resuelve al compilar (NEXT_PUBLIC_*): igual en servidor y navegador, sin desajustes de hidratación
export const AUTH_DISPONIBLE = Boolean(
  process.env.NEXT_PUBLIC_SUPABASE_URL && process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
);

const AuthContext = createContext({ usuario: null, cargando: false, entrar: async () => {}, entrarConGoogle: async () => {}, entrarConTokenGoogle: async () => {}, salir: async () => {}, cerrarSesion: () => {}, abrirLogin: () => {}, peticionLogin: null, miPerfil: null, setMiPerfil: () => {}, esAdmin: false });

export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(AUTH_DISPONIBLE);
  // Petición de abrir el panel de inicio de sesión desde cualquier sitio (p. ej. "Añadir al diario"); la atiende PanelLogin
  const [peticionLogin, setPeticionLogin] = useState(null);
  // "Has cerrado sesión": aquí y no en la barra porque al salir la página cambia (a la portada)
  const [aviso, setAviso] = useState("");
  // Cerrar sesión desde la barra: primero a la portada y, ya en ella, se cierra (ver cerrarSesion)
  const [saliendo, setSaliendo] = useState(false);
  const ruta = usePathname();
  const router = useRouter();
  // GET /me/perfil del usuario con sesión, guardado con su id (al cambiar de cuenta deja de valer)
  const [perfil, setPerfil] = useState({ uid: null, datos: null });
  const uid = usuario?.id;

  useEffect(() => {
    const sb = supabase();
    if (!sb) return;
    // Emite INITIAL_SESSION al suscribirse, y SIGNED_IN al volver del magic link
    const { data } = sb.auth.onAuthStateChange((evento, sesion) => {
      setUsuario(sesion?.user ?? null);
      setCargando(false);
      if (evento === "SIGNED_OUT") {
        setAviso("Has cerrado sesión");
        setPerfil({ uid: null, datos: null }); // que no quede nada del usuario anterior en memoria
      }
      if (evento === "SIGNED_IN") setAviso("");
    });
    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!uid) return;
    let vigente = true;
    leerPerfil()
      .then((datos) => vigente && setPerfil({ uid, datos }))
      .catch(() => vigente && setPerfil({ uid, datos: { usuario: null } })); // sin poder leerlo, como si no tuviera
    return () => { vigente = false; };
  }, [uid]);
  // undefined: aún no se sabe; null: sin sesión; si no, el perfil (usuario null = aún no lo ha creado)
  const miPerfil = !uid ? null : perfil.uid === uid ? perfil.datos : undefined;
  const setMiPerfil = (datos) => setPerfil({ uid, datos });

  // es_admin de GET /me (lo decide el servidor con ADMIN_EMAILS). Solo enseña el enlace: /admin/* ya da 404 a los demás.
  const [admin, setAdmin] = useState({ uid: null, es: false });
  useEffect(() => {
    if (!uid) return;
    let vigente = true;
    fetchConAuth("/me")
      .then((res) => (res.ok ? res.json() : {}))
      .then((me) => vigente && setAdmin({ uid, es: me.es_admin === true }))
      .catch(() => vigente && setAdmin({ uid, es: false }));
    return () => { vigente = false; };
  }, [uid]);
  // Como miPerfil: undefined mientras no se sabe
  const esAdmin = !uid ? false : admin.uid === uid ? admin.es : undefined;

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

  // Botón oficial de Google (GIS): el ID token llega por callback, sin salir de la página. nonce va en claro
  // (a Google se le pasó su SHA-256); si el email ya tenía cuenta, Supabase enlaza la identidad al mismo usuario.
  const entrarConTokenGoogle = async (token, nonce) => {
    const { error } = await supabase().auth.signInWithIdToken({ provider: "google", token, nonce });
    if (error) throw error;
  };

  // Objeto nuevo en cada llamada: dos peticiones seguidas con el mismo mensaje vuelven a abrir el panel
  const abrirLogin = (mensaje = "") => setPeticionLogin({ mensaje });

  const salir = async () => {
    await supabase()?.auth.signOut();
  };

  // replace y no push: "atrás" no vuelve a la página privada. La sesión se cierra ya en "/", así la página
  // anterior nunca se repinta sin sesión (ni con datos a medias) antes de irse.
  const cerrarSesion = () => {
    setSaliendo(true);
    router.replace("/");
  };
  useEffect(() => {
    if (!saliendo || ruta !== "/") return;
    supabase()?.auth.signOut().finally(() => setSaliendo(false));
  }, [saliendo, ruta]);

  // El aviso se ve unos segundos en la portada; para lectores de pantalla basta con que se anuncie
  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(""), 4000);
    return () => clearTimeout(t);
  }, [aviso]);

  return (
    <AuthContext.Provider value={{ usuario, cargando, entrar, entrarConGoogle, entrarConTokenGoogle, salir, cerrarSesion, abrirLogin, peticionLogin, miPerfil, setMiPerfil, esAdmin }}>
      {children}
      <p role="status" aria-live="polite" className={aviso ? "fixed z-50 bottom-4 left-1/2 -translate-x-1/2 w-max max-w-[calc(100%-2rem)] bg-primary px-4 py-2 text-sm font-bold text-white shadow-lg" : "sr-only"}>
        {aviso}
      </p>
    </AuthContext.Provider>
  );
}
