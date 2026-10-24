"use client";

import Link from "next/link";
import { useId, useState } from "react";
import { BOTON_PRIMARIO } from "@/components/DialogoDiario";
import { suscribir } from "@/lib/newsletter";

// Suscripción a la newsletter (pie y /newsletter). compacto: la versión del pie, sin título grande.
export default function FormNewsletter({ compacto = false }) {
  const id = useId();
  const [email, setEmail] = useState("");
  const [web, setWeb] = useState(""); // campo trampa
  const [estado, setEstado] = useState({ tipo: "", texto: "" });

  const enviar = async (e) => {
    e.preventDefault();
    setEstado({ tipo: "enviando", texto: "Enviando…" });
    try {
      setEstado({ tipo: "ok", texto: `${await suscribir(email.trim(), web)} Revisa también la carpeta de spam.` });
      setEmail("");
    } catch (err) {
      setEstado({ tipo: "error", texto: err.message });
    }
  };

  return (
    <form onSubmit={enviar} className="space-y-3" aria-labelledby={`${id}-titulo`}>
      <h4 id={`${id}-titulo`} className={compacto ? "font-bold text-foreground uppercase tracking-wider text-xs" : "text-xl font-display font-bold uppercase text-foreground"}>
        Esta semana en Madrid
      </h4>
      <p className="text-muted text-sm leading-relaxed">
        Cada lunes, los estrenos y las sesiones especiales de la semana en tu correo.
      </p>
      <div className="flex gap-2">
        <label htmlFor={`${id}-email`} className="sr-only">Tu email</label>
        <input id={`${id}-email`} type="email" required autoComplete="email" value={email} maxLength={254}
               onChange={(e) => setEmail(e.target.value)} placeholder="tu@email.com"
               aria-describedby={`${id}-aviso ${id}-estado`}
               className="min-w-0 flex-1 min-h-11 border border-line bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none" />
        <button type="submit" disabled={estado.tipo === "enviando"} className={`${BOTON_PRIMARIO} min-h-11 shrink-0`}>
          Suscribirme
        </button>
      </div>
      {/* Campo trampa: fuera de la pantalla y del orden de tabulación; solo lo rellenan bots */}
      <div aria-hidden="true" className="absolute -left-[9999px] w-px h-px overflow-hidden">
        <label htmlFor={`${id}-web`}>No rellenes este campo</label>
        <input id={`${id}-web`} type="text" name="web" tabIndex={-1} autoComplete="off" value={web} onChange={(e) => setWeb(e.target.value)} />
      </div>
      <p id={`${id}-aviso`} className="text-xs text-muted leading-relaxed">
        Solo guardamos tu email. Te pediremos confirmarlo y puedes darte de baja con un clic en cada correo.{" "}
        <Link href="/privacidad" className="underline hover:text-primary">Privacidad</Link>.
      </p>
      <p id={`${id}-estado`} role="status" aria-live="polite"
         className={`text-sm ${estado.tipo === "error" ? "text-red-600" : estado.tipo === "ok" ? "text-foreground font-bold" : "text-muted"}`}>
        {estado.texto}
      </p>
    </form>
  );
}
