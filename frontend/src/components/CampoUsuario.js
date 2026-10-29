"use client";

import { CAMPO, ETIQUETA } from "@/components/DialogoDiario";
import { USUARIO_MAX, USUARIO_MIN } from "@/lib/usuario";

const COLOR = { libre: "text-green-700", no: "text-red-600", error: "text-red-600" };

// Nombre de usuario con su comprobación al instante (useDisponibilidad de lib/perfil.js, la pide el padre para poder
// bloquear el envío). El resultado se anuncia con aria-live. Lo usan el editor, "Crear cuenta" y "Elige tu nombre".
export default function CampoUsuario({ id, valor, onCambiar, comprobacion, campoRef, required = false }) {
  return (
    <div>
      <label htmlFor={`${id}-usuario`} className={ETIQUETA}>Nombre de usuario</label>
      <input
        ref={campoRef} id={`${id}-usuario`} type="text" required={required} minLength={USUARIO_MIN} maxLength={USUARIO_MAX} value={valor}
        onChange={(e) => onCambiar(e.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false}
        aria-describedby={`${id}-reglas ${id}-disponible`} aria-invalid={comprobacion.estado === "no"}
        className={CAMPO}
      />
      <p id={`${id}-reglas`} className="mt-1 text-xs text-muted">
        De {USUARIO_MIN} a {USUARIO_MAX} caracteres: letras sin tildes, números, punto y guion bajo.
      </p>
      <p id={`${id}-disponible`} aria-live="polite" className={`mt-1 text-sm font-semibold min-h-5 ${COLOR[comprobacion.estado] ?? "text-muted"}`}>
        {comprobacion.estado === "comprobando" ? "Comprobando…" : comprobacion.motivo}
      </p>
    </div>
  );
}
