"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import { fetchConAuth } from "@/lib/api";

// Cines favoritos del usuario con sesión (backend/app/favoritos.py): se cargan una vez al haber sesión y se
// vacían al cerrarla. Mientras no se conocen (o sin sesión), un Set vacío: el primer render es igual en el servidor
// y en el cliente, y el orden por favoritos llega después, sin desajustes al hidratar.
const VACIO = new Set();
const FavoritosContext = createContext({ favoritos: VACIO, cargados: false, alternar: () => {} });

export function useFavoritos() {
  return useContext(FavoritosContext);
}

async function pedir(ruta, opciones) {
  const res = await fetchConAuth(ruta, opciones);
  if (!res.ok) throw new Error(res.status === 401 ? "Tu sesión ha caducado. Vuelve a iniciar sesión." : "No se ha podido guardar tu cine favorito. Inténtalo de nuevo.");
  return res.status === 204 ? null : res.json();
}

export default function FavoritosProvider({ children }) {
  const { usuario, abrirLogin } = useAuth();
  const uid = usuario?.id;
  // Guardados con el usuario al que pertenecen: los de otra cuenta nunca se usan
  const [estado, setEstado] = useState({ uid: null, slugs: null });
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    if (!uid) return;
    let vigente = true;
    pedir("/me/cines-favoritos")
      .then((lista) => vigente && setEstado({ uid, slugs: new Set(lista) }))
      .catch(() => vigente && setEstado({ uid, slugs: new Set() })); // sin poder leerlos, como si no hubiera
    return () => {
      vigente = false;
      setEstado({ uid: null, slugs: null }); // al cerrar sesión (o cambiar de cuenta) no queda nada en memoria
    };
  }, [uid]);

  useEffect(() => {
    if (!aviso) return;
    const t = setTimeout(() => setAviso(""), 4000);
    return () => clearTimeout(t);
  }, [aviso]);

  const cargados = Boolean(uid) && estado.uid === uid && estado.slugs !== null;
  const favoritos = cargados ? estado.slugs : VACIO;

  // Optimista: se marca ya y, si el servidor falla, se deshace solo ese cine
  const cambiar = (slug, favorito) =>
    setEstado((e) => {
      if (e.uid !== uid || !e.slugs) return e;
      const slugs = new Set(e.slugs);
      if (favorito) slugs.add(slug);
      else slugs.delete(slug);
      return { ...e, slugs };
    });

  const alternar = async (slug, nombre) => {
    if (!uid) return abrirLogin("Inicia sesión para guardar tus cines favoritos");
    if (!cargados) return;
    const favorito = !favoritos.has(slug);
    cambiar(slug, favorito);
    setAviso("");
    try {
      await pedir(`/me/cines-favoritos/${encodeURIComponent(slug)}`, { method: favorito ? "PUT" : "DELETE" });
    } catch (err) {
      cambiar(slug, !favorito);
      setAviso(`${nombre}: ${err.message}`);
    }
  };

  return (
    <FavoritosContext.Provider value={{ favoritos, cargados, alternar }}>
      {children}
      {AUTH_DISPONIBLE && (
        <p role="status" aria-live="polite" className={aviso ? "fixed z-50 bottom-4 left-1/2 -translate-x-1/2 w-max max-w-[calc(100%-2rem)] bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-lg" : "sr-only"}>
          {aviso}
        </p>
      )}
    </FavoritosContext.Provider>
  );
}
