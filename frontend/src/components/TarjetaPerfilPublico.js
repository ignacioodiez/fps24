"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import Avatar, { AtribucionPoster } from "@/components/Avatar";
import BuscadorPeliculas from "@/components/BuscadorPeliculas";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO, CAMPO, ETIQUETA } from "@/components/DialogoDiario";
import { leerLetterboxd } from "@/lib/letterboxd";
import { BIO_MAX, comprobarUsuario, guardarPerfil, leerPerfil } from "@/lib/perfil";

const ESPERA_MS = 400; // debounce de la comprobación de disponibilidad

// Interruptor (role="switch") con su título y su explicación
function Interruptor({ id, activo, onCambiar, disabled = false, titulo, children }) {
  return (
    <div className="flex items-start gap-3">
      <button
        type="button" role="switch" aria-checked={activo} onClick={onCambiar} disabled={disabled}
        aria-labelledby={`${id}-titulo`} aria-describedby={`${id}-explicacion`}
        className={`relative mt-0.5 h-6 w-11 shrink-0 border transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50 disabled:cursor-not-allowed ${activo ? "bg-primary border-primary" : "bg-background border-line"}`}
      >
        <span aria-hidden="true" className={`absolute top-0.5 h-4 w-4 transition-all ${activo ? "left-6 bg-white" : "left-0.5 bg-muted"}`} />
      </button>
      <div>
        <p id={`${id}-titulo`} className={`text-sm font-bold ${disabled ? "text-muted" : "text-foreground"}`}>{titulo}</p>
        <div id={`${id}-explicacion`} className="text-sm text-muted">{children}</div>
      </div>
    </div>
  );
}

// Muestra circular de un color del avatar: el radio nativo, oculto, da el teclado y el lector de pantalla
function Muestra({ nombre, valor, elegido, onElegir, etiqueta, children, style }) {
  return (
    <label className="cursor-pointer">
      <input type="radio" name={nombre} checked={elegido} onChange={() => onElegir(valor)} className="peer sr-only" />
      <span aria-hidden="true" style={style}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-[10px] font-bold uppercase text-muted ring-offset-2 ring-offset-surface peer-checked:ring-2 peer-checked:ring-foreground peer-focus-visible:outline-2 peer-focus-visible:outline-offset-4 peer-focus-visible:outline-primary">
        {children}
      </span>
      <span className="sr-only">{etiqueta}</span>
    </label>
  );
}

// Nombre de usuario, bio, avatar, Letterboxd, visibilidad (privado por defecto) y diario y cines en el perfil (apagados).
// Se guarda todo junto con "Guardar perfil".
export default function TarjetaPerfilPublico() {
  const { setMiPerfil } = useAuth();
  const [guardado, setGuardado] = useState(null); // el de GET /me/perfil; null mientras carga
  const [usuario, setUsuario] = useState("");
  const [bio, setBio] = useState("");
  const [publico, setPublico] = useState(false);
  const [diario, setDiario] = useState(false);
  const [cines, setCines] = useState(false);
  const [avatarTipo, setAvatarTipo] = useState("iniciales");
  const [avatarColor, setAvatarColor] = useState(null); // null: el que sale del nombre
  const [peliAvatar, setPeliAvatar] = useState(null); // { id, poster_url, titulo? }
  const [errorPeli, setErrorPeli] = useState("");
  const [letterboxd, setLetterboxd] = useState("");
  const [comprobacion, setComprobacion] = useState({ estado: "nada", motivo: "" }); // nada | comprobando | libre | no | error
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const id = useId();
  const campoUsuario = useRef(null);

  // El formulario con lo guardado (al cargar y tras guardar)
  const rellenar = (p) => {
    setGuardado(p);
    setUsuario(p.usuario ?? "");
    setBio(p.bio ?? "");
    setPublico(p.visibilidad === "publico");
    setDiario(p.diario_publico);
    setCines(p.cines_publicos);
    setAvatarTipo(p.avatar_tipo ?? "iniciales");
    setAvatarColor(p.avatar_color ?? null);
    setPeliAvatar(p.avatar?.tipo === "pelicula" ? { id: p.avatar_pelicula_id, poster_url: p.avatar.poster_url } : null);
    setLetterboxd(p.letterboxd_usuario ?? "");
  };

  useEffect(() => {
    leerPerfil()
      .then(rellenar)
      .catch((err) => {
        setGuardado({ usuario: null });
        setError(err.message);
      });
  }, []);

  // Sin nombre de usuario (llega desde /perfil): el foco, en el campo
  const sinUsuario = guardado && !guardado.usuario;
  useEffect(() => {
    if (sinUsuario) campoUsuario.current?.focus();
  }, [sinUsuario]);

  // Disponibilidad con debounce; la petición anterior se cancela al seguir escribiendo
  useEffect(() => {
    if (!guardado || !usuario || usuario === guardado.usuario) {
      setComprobacion({ estado: "nada", motivo: "" });
      return;
    }
    const control = new AbortController();
    const t = setTimeout(() => {
      setComprobacion({ estado: "comprobando", motivo: "" });
      comprobarUsuario(usuario, control.signal)
        .then((r) => setComprobacion(r.disponible ? { estado: "libre", motivo: "Disponible" } : { estado: "no", motivo: r.motivo }))
        .catch((err) => err.name !== "AbortError" && setComprobacion({ estado: "error", motivo: err.message }));
    }, ESPERA_MS);
    return () => {
      clearTimeout(t);
      control.abort();
    };
  }, [usuario, guardado]);

  const guardar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError("");
    setAviso("");
    try {
      // Con el perfil privado se guardan apagados: al volver a hacerlo público, el diario y los cines no reaparecen sin pedirlo
      const p = await guardarPerfil({
        usuario, bio, visibilidad: publico ? "publico" : "privado", diario_publico: publico && diario, cines_publicos: publico && cines,
        avatar_tipo: avatarTipo, avatar_color: avatarColor, avatar_pelicula_id: avatarTipo === "pelicula" ? peliAvatar?.id ?? null : null,
        letterboxd_usuario: letterboxd,
      });
      rellenar(p);
      setMiPerfil(p);
      setAviso("Perfil guardado");
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  };

  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/u/${guardado.usuario}`);
      setAviso("Enlace copiado");
    } catch {
      setAviso("No se ha podido copiar el enlace");
    }
  };

  if (!guardado) {
    return <div aria-busy="true" aria-label="Cargando tu perfil público" className="h-48 mb-6 bg-surface animate-pulse" />;
  }

  const paleta = guardado.paleta_avatar ?? {};
  const vistaPrevia = avatarTipo === "pelicula" && peliAvatar
    ? { tipo: "pelicula", poster_url: peliAvatar.poster_url }
    : { tipo: "iniciales", fondo: paleta[avatarColor] ?? guardado.avatar?.fondo };
  const lbx = leerLetterboxd(letterboxd);
  const elegirPeli = (p) => {
    if (p.poster_url) {
      setPeliAvatar(p);
      setErrorPeli("");
    } else setErrorPeli(`«${p.titulo}» no tiene póster: elige otra película.`);
  };

  const colorComprobacion = { libre: "text-green-700", no: "text-red-600", error: "text-red-600" }[comprobacion.estado] ?? "text-muted";

  return (
    <section aria-labelledby={`${id}-titulo`} className="mb-6 border border-line bg-surface p-4 md:p-5">
      <h3 id={`${id}-titulo`} className="text-xl font-display font-bold uppercase text-foreground">Tu perfil</h3>
      <p className="mt-1 text-sm text-muted">Elige un nombre de usuario y decide quién puede verlo.</p>

      <form onSubmit={guardar} className="mt-4 space-y-4">
        <div>
          <label htmlFor={`${id}-usuario`} className={ETIQUETA}>Nombre de usuario</label>
          <input
            ref={campoUsuario} id={`${id}-usuario`} type="text" required minLength={3} maxLength={20} value={usuario}
            onChange={(e) => setUsuario(e.target.value.toLowerCase())}
            autoComplete="off" autoCapitalize="none" spellCheck={false}
            aria-describedby={`${id}-reglas ${id}-disponible`} aria-invalid={comprobacion.estado === "no"}
            className={CAMPO}
          />
          <p id={`${id}-reglas`} className="mt-1 text-xs text-muted">
            De 3 a 20 caracteres: letras sin tildes, números, punto y guion bajo.
          </p>
          <p id={`${id}-disponible`} aria-live="polite" className={`mt-1 text-sm font-semibold min-h-5 ${colorComprobacion}`}>
            {comprobacion.estado === "comprobando" ? "Comprobando…" : comprobacion.motivo}
          </p>
        </div>

        <div>
          <label htmlFor={`${id}-bio`} className={ETIQUETA}>Bio</label>
          <textarea
            id={`${id}-bio`} rows={2} maxLength={BIO_MAX} value={bio} onChange={(e) => setBio(e.target.value)}
            aria-describedby={`${id}-contador`} className={`${CAMPO} resize-y`}
          />
          <p id={`${id}-contador`} className="mt-1 text-xs text-muted text-right">{bio.length}/{BIO_MAX}</p>
        </div>

        <fieldset>
          <legend className={ETIQUETA}>Avatar</legend>
          <div className="flex flex-col sm:flex-row sm:items-start gap-4">
            <div className="flex flex-col items-center gap-1 shrink-0">
              <Avatar usuario={usuario || "?"} avatar={vistaPrevia} className="w-20 h-20 text-3xl" etiqueta="Vista previa de tu avatar" />
              {vistaPrevia.tipo === "pelicula" && <AtribucionPoster />}
            </div>
            <div className="min-w-0 flex-1 space-y-3">
              <div className="flex flex-wrap gap-x-5 text-sm text-foreground">
                {[["iniciales", "Iniciales"], ["pelicula", "Póster de una película"]].map(([valor, texto]) => (
                  <label key={valor} className="flex items-center gap-2 min-h-11 cursor-pointer">
                    <input type="radio" name={`${id}-avatar-tipo`} checked={avatarTipo === valor} onChange={() => setAvatarTipo(valor)} className="h-4 w-4 accent-[var(--primary)]" />
                    {texto}
                  </label>
                ))}
              </div>
              {avatarTipo === "iniciales" ? (
                <fieldset>
                  <legend className="mb-2 text-sm text-muted">Color de fondo</legend>
                  <div className="flex flex-wrap gap-3">
                    <Muestra nombre={`${id}-color`} valor={null} elegido={avatarColor === null} onElegir={setAvatarColor} etiqueta="Automático">auto</Muestra>
                    {Object.entries(paleta).map(([nombre, fondo]) => (
                      <Muestra key={nombre} nombre={`${id}-color`} valor={nombre} elegido={avatarColor === nombre} onElegir={setAvatarColor}
                               etiqueta={nombre} style={{ backgroundColor: fondo, borderColor: fondo }} />
                    ))}
                  </div>
                </fieldset>
              ) : (
                // Enter en el buscador nunca envía el formulario del perfil
                <div onKeyDown={(e) => e.key === "Enter" && e.target.type === "search" && e.preventDefault()}>
                  <BuscadorPeliculas etiqueta="Busca la película de tu avatar" onElegir={elegirPeli} />
                  <p aria-live="polite" className={`mt-1 text-sm min-h-5 ${errorPeli ? "font-semibold text-red-600" : "text-muted"}`}>
                    {errorPeli || (peliAvatar ? (peliAvatar.titulo ? `Póster de «${peliAvatar.titulo}»` : "Póster elegido") : "Elige una película con póster.")}
                  </p>
                </div>
              )}
            </div>
          </div>
        </fieldset>

        <div>
          <label htmlFor={`${id}-letterboxd`} className={ETIQUETA}>Letterboxd (opcional)</label>
          <input
            id={`${id}-letterboxd`} type="text" maxLength={200} value={letterboxd} onChange={(e) => setLetterboxd(e.target.value)}
            placeholder="tu_usuario o letterboxd.com/tu_usuario" autoComplete="off" autoCapitalize="none" spellCheck={false}
            aria-describedby={`${id}-letterboxd-estado`} aria-invalid={Boolean(lbx.motivo)} className={CAMPO}
          />
          <p id={`${id}-letterboxd-estado`} aria-live="polite" className={`mt-1 text-sm min-h-5 ${lbx.motivo ? "font-semibold text-red-600" : "text-muted"}`}>
            {lbx.motivo ?? (lbx.usuario ? `En tu perfil público: «Letterboxd: @${lbx.usuario}»` : "Tu usuario o el enlace a tu perfil de Letterboxd.")}
          </p>
        </div>

        <Interruptor id={`${id}-visibilidad`} activo={publico} onCambiar={() => setPublico((v) => !v)} titulo={`Perfil ${publico ? "público" : "privado"}`}>
          Privado: solo tú lo ves. Público: cualquiera con tu enlace puede ver tu nombre de usuario, tu avatar, tu bio y tu Letterboxd.
        </Interruptor>

        <div className="border border-line bg-background p-3">
          <Interruptor
            id={`${id}-diario`} activo={publico && diario} onCambiar={() => setDiario((v) => !v)} disabled={!publico}
            titulo="Mostrar mi diario en mi perfil"
          >
            <p>
              Si lo activas, cualquiera con tu enlace podrá ver todas tus entradas, incluidas tus notas. Solo se muestra
              si tu perfil también es público.
            </p>
            {!publico && <p className="mt-1 font-semibold text-foreground">Tu perfil es privado: hazlo público para poder activarlo.</p>}
          </Interruptor>
        </div>

        <div className="border border-line bg-background p-3">
          <Interruptor
            id={`${id}-cines`} activo={publico && cines} onCambiar={() => setCines((v) => !v)} disabled={!publico}
            titulo="Mostrar mis cines favoritos en mi perfil público"
          >
            <p>Si lo activas, cualquiera con tu enlace verá la lista de los cines que has marcado con la ★.</p>
            {!publico && <p className="mt-1 font-semibold text-foreground">Tu perfil es privado: hazlo público para poder activarlo.</p>}
          </Interruptor>
        </div>

        {guardado.usuario && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Tu enlace:</span>
            <a href={`/u/${guardado.usuario}`} className="font-bold text-primary hover:underline break-all">fps24.es/u/{guardado.usuario}</a>
            <button type="button" onClick={copiar} className={BOTON_SECUNDARIO}>Copiar enlace</button>
            {guardado.visibilidad !== "publico" && (
              <p className="w-full text-xs text-muted">Mientras sea privado, quien abra el enlace verá «Este perfil no existe o es privado».</p>
            )}
          </div>
        )}

        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-wrap items-center gap-3">
          <button type="submit" disabled={guardando || comprobacion.estado === "no" || Boolean(lbx.motivo)} className={BOTON_PRIMARIO}>
            {guardando ? "Guardando…" : "Guardar perfil"}
          </button>
          <p role="status" aria-live="polite" className="text-sm font-semibold text-primary">{aviso}</p>
        </div>
      </form>
    </section>
  );
}
