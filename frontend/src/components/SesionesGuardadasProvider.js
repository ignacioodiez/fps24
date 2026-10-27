"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import ModalSesion from "@/components/ModalSesion";
import { guardarSesion, marcasSesiones, quitarSesion } from "@/lib/sesiones";

// Sesiones guardadas del usuario con sesión (backend/app/sesiones.py), como FavoritosProvider: las marcas
// (id del pase -> id de la guardada) se cargan una vez al haber sesión y se vacían al cerrarla. Mientras no se conocen,
// un Map vacío: el primer render es igual en el servidor y en el cliente. También abre el modal de una sesión.
const VACIO = new Map();
const SesionesContext = createContext({ guardadas: VACIO, abrir: () => {}, alternar: async () => {}, olvidar: () => {} });

export function useSesionesGuardadas() {
  return useContext(SesionesContext);
}

export default function SesionesGuardadasProvider({ children }) {
  const { usuario } = useAuth();
  const uid = usuario?.id;
  const [estado, setEstado] = useState({ uid: null, marcas: null });
  const [abierta, setAbierta] = useState(null); // { sesion, origen }

  useEffect(() => {
    if (!uid) return;
    let vigente = true;
    marcasSesiones()
      .then((lista) => vigente && setEstado({ uid, marcas: new Map(lista.map((m) => [m.sesion_id, m.id])) }))
      .catch(() => vigente && setEstado({ uid, marcas: new Map() })); // sin poder leerlas, como si no hubiera
    return () => {
      vigente = false;
      setEstado({ uid: null, marcas: null });
    };
  }, [uid]);

  const cargadas = Boolean(uid) && estado.uid === uid && estado.marcas !== null;
  const guardadas = cargadas ? estado.marcas : VACIO;

  const cambiar = (editar) =>
    setEstado((e) => {
      if (e.uid !== uid || !e.marcas) return e;
      const marcas = new Map(e.marcas);
      editar(marcas);
      return { ...e, marcas };
    });

  // Guarda o quita la sesión de ese pase; si falla, lanza el Error con el mensaje para el usuario
  const alternar = async (sesionId) => {
    const id = guardadas.get(sesionId);
    if (id) {
      await quitarSesion(id);
      cambiar((m) => m.delete(sesionId));
    } else {
      const guardada = await guardarSesion(sesionId);
      cambiar((m) => m.set(sesionId, guardada.id));
    }
  };

  // Quitada desde "Mis sesiones": deja de marcarse en la cartelera
  const olvidar = (id) => cambiar((m) => m.forEach((g, sesionId) => g === id && m.delete(sesionId)));

  // sesion: el pase con cine (nombre), cine_slug y pelicula { id, titulo, poster_url }; origen: la hora que lo abre
  const abrir = (sesion, origen) => setAbierta({ sesion, origen });

  return (
    <SesionesContext.Provider value={{ guardadas, abrir, alternar, olvidar }}>
      {children}
      {abierta && (
        <ModalSesion sesion={abierta.sesion} origen={abierta.origen} guardada={guardadas.has(abierta.sesion.id)}
                     onAlternar={alternar} onCerrar={() => setAbierta(null)} />
      )}
    </SesionesContext.Provider>
  );
}
