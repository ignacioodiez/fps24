"use client";

import { useCallback, useEffect, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import DialogoDiario from "@/components/DialogoDiario";
import { entradasDePelicula, fechaPorDefecto } from "@/lib/diario";

const AVISOS = { creada: "Añadido a tu diario", editada: "Entrada actualizada", borrada: "Entrada eliminada del diario" };

// "Añadir al diario" de la vista rápida y la ficha completa. dia: el día elegido (fecha por defecto si no es futuro).
export default function BotonDiario({ pelicula, dia = null, className = "" }) {
  const { usuario, cargando, abrirLogin } = useAuth();
  // Entradas de esta película, guardadas con el usuario al que pertenecen (al cerrar sesión dejan de valer)
  const [datos, setDatos] = useState({ uid: null, lista: null });
  const [dialogo, setDialogo] = useState(null); // null | { entrada, repeticion }
  const [aviso, setAviso] = useState("");
  const entradas = usuario && datos.uid === usuario.id ? datos.lista : null;

  const recargar = useCallback(() => {
    if (!usuario) return;
    entradasDePelicula(pelicula.id)
      .then((lista) => setDatos({ uid: usuario.id, lista }))
      .catch(() => setDatos({ uid: usuario.id, lista: [] })); // sin poder consultar, se ofrece añadir
  }, [usuario, pelicula.id]);

  useEffect(recargar, [recargar]);

  if (!AUTH_DISPONIBLE) return null;

  const pulsar = () => {
    if (!usuario) return abrirLogin("Inicia sesión para guardar tu diario");
    setAviso("");
    setDialogo({ entrada: entradas?.[0] ?? null, repeticion: false });
  };

  const tras = (tipo) => {
    setAviso(AVISOS[tipo]);
    recargar();
  };

  const enDiario = entradas?.length > 0;

  return (
    <div className={`flex flex-wrap items-center gap-x-3 gap-y-1 ${className}`}>
      <button
        type="button" onClick={pulsar} aria-haspopup="dialog" disabled={cargando || (usuario && !entradas)}
        className={`px-4 py-2 border text-sm font-bold transition-colors disabled:opacity-60 ${enDiario
          ? "border-primary bg-primary-soft text-primary hover:bg-primary hover:text-white"
          : "border-line bg-background text-foreground hover:border-primary hover:text-primary"}`}
      >
        {enDiario ? "En tu diario ✓" : "Añadir al diario"}
      </button>
      {enDiario && (
        <button
          type="button" aria-haspopup="dialog" onClick={() => { setAviso(""); setDialogo({ entrada: null, repeticion: true }); }}
          className="text-sm font-semibold text-primary underline-offset-2 hover:underline"
        >
          Añadir otra vez vista
        </button>
      )}
      <p role="status" aria-live="polite" className="text-sm font-semibold text-primary">{aviso}</p>

      {dialogo && (
        <DialogoDiario
          pelicula={pelicula} entrada={dialogo.entrada} repeticionInicial={dialogo.repeticion}
          fechaInicial={fechaPorDefecto(dia)}
          onCerrar={() => setDialogo(null)}
          onGuardado={(_, editada) => tras(editada ? "editada" : "creada")}
          onBorrado={() => tras("borrada")}
        />
      )}
    </div>
  );
}
