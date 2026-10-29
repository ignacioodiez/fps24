"use client";

import { useEffect, useId, useRef, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import Avatar, { AtribucionPoster } from "@/components/Avatar";
import BuscadorPeliculas from "@/components/BuscadorPeliculas";
import CampoUsuario from "@/components/CampoUsuario";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO, CAMPO, ETIQUETA } from "@/components/DialogoDiario";
import { leerLetterboxd } from "@/lib/letterboxd";
import { BIO_MAX, guardarPerfil, leerPerfil, useDisponibilidad } from "@/lib/perfil";

const NIVELES = [["privado", "Privado"], ["amigos", "Solo amigos"], ["publico", "Público"]]; // de más cerrado a más abierto
const orden = (nivel) => NIVELES.findIndex(([n]) => n === nivel);
// Una sección nunca más abierta que el perfil (la misma regla que el backend)
const sinPasar = (nivel, tope) => (orden(nivel) > orden(tope) ? tope : nivel);

// Privado / Solo amigos / Público: radios nativos (teclado y lector de pantalla) con aspecto de botones.
// tope: las opciones más abiertas se deshabilitan. explicaciones: una línea por nivel, se ve la del elegido.
function SelectorNivel({ id, titulo, valor, onCambiar, tope = "publico", explicaciones }) {
  const limitado = orden(tope) < NIVELES.length - 1;
  return (
    <fieldset aria-describedby={`${id}-explicacion`} className="border border-line bg-background p-3">
      <legend className="px-1 text-sm font-bold text-foreground">{titulo}</legend>
      <div className="flex flex-wrap gap-2">
        {NIVELES.map(([nivel, etiqueta], i) => (
          <label key={nivel} className={i > orden(tope) ? "cursor-not-allowed" : "cursor-pointer"}>
            <input type="radio" name={id} value={nivel} checked={valor === nivel} disabled={i > orden(tope)}
                   onChange={() => onCambiar(nivel)} className="peer sr-only" />
            <span className="flex items-center min-h-11 px-3 border border-line text-sm font-bold text-foreground peer-checked:border-primary peer-checked:bg-primary peer-checked:text-white peer-disabled:opacity-40 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-primary">
              {etiqueta}
            </span>
          </label>
        ))}
      </div>
      <p id={`${id}-explicacion`} className="mt-2 text-sm text-muted">
        {explicaciones[valor]}
        {limitado && <span className="block mt-1 font-semibold text-foreground">No puede ser más abierto que tu perfil.</span>}
      </p>
    </fieldset>
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

// Avatar, nombre de usuario, bio y Letterboxd; al pie, en "Privacidad", quién ve el perfil, el diario y los cines (todo
// privado por defecto). Se guarda todo junto con "Guardar perfil".
export default function TarjetaPerfilPublico() {
  const { setMiPerfil } = useAuth();
  const [guardado, setGuardado] = useState(null); // el de GET /me/perfil; null mientras carga
  const [usuario, setUsuario] = useState("");
  const [bio, setBio] = useState("");
  const [visibilidad, setVisibilidad] = useState("privado");
  const [diarioElegido, setDiario] = useState("privado");
  const [cinesElegido, setCines] = useState("privado");
  const [avatarTipo, setAvatarTipo] = useState("iniciales");
  const [avatarColor, setAvatarColor] = useState(null); // null: el que sale del nombre
  const [peliAvatar, setPeliAvatar] = useState(null); // { id, poster_url, titulo? }
  const [errorPeli, setErrorPeli] = useState("");
  const [letterboxd, setLetterboxd] = useState("");
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
    setVisibilidad(p.visibilidad ?? "privado");
    setDiario(p.diario_visibilidad ?? "privado");
    setCines(p.cines_visibilidad ?? "privado");
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

  // Disponibilidad al instante; su nombre actual no se comprueba
  const comprobacion = useDisponibilidad(guardado ? usuario : "", guardado?.usuario);

  const guardar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError("");
    setAviso("");
    try {
      // Se guardan bajadas al nivel del perfil: al volver a abrirlo, el diario y los cines no se abren sin pedirlo
      const p = await guardarPerfil({
        usuario, bio, visibilidad,
        diario_visibilidad: sinPasar(diarioElegido, visibilidad), cines_visibilidad: sinPasar(cinesElegido, visibilidad),
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

  const diario = sinPasar(diarioElegido, visibilidad);
  const cines = sinPasar(cinesElegido, visibilidad);
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

  return (
    <section aria-labelledby={`${id}-titulo`} className="mb-6 border border-line bg-surface p-4 md:p-5">
      <h3 id={`${id}-titulo`} className="text-xl font-display font-bold uppercase text-foreground">Tu perfil</h3>
      <p className="mt-1 text-sm text-muted">Tu avatar, tu nombre de usuario y lo que cuentas de ti. Quién lo ve, al final.</p>

      <form onSubmit={guardar} className="mt-4 space-y-4">
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

        <CampoUsuario id={id} valor={usuario} onCambiar={setUsuario} comprobacion={comprobacion} campoRef={campoUsuario} required />

        <div>
          <label htmlFor={`${id}-bio`} className={ETIQUETA}>Bio</label>
          <textarea
            id={`${id}-bio`} rows={2} maxLength={BIO_MAX} value={bio} onChange={(e) => setBio(e.target.value)}
            aria-describedby={`${id}-contador`} className={`${CAMPO} resize-y`}
          />
          <p id={`${id}-contador`} className="mt-1 text-xs text-muted text-right">{bio.length}/{BIO_MAX}</p>
        </div>

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

        {guardado.usuario && (
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Tu enlace:</span>
            <a href={`/u/${guardado.usuario}`} className="font-bold text-primary hover:underline break-all">fps24.es/u/{guardado.usuario}</a>
            <button type="button" onClick={copiar} className={BOTON_SECUNDARIO}>Copiar enlace</button>
          </div>
        )}

        <section aria-labelledby={`${id}-privacidad`} className="space-y-4 border-t border-line pt-4">
          <div>
            <h4 id={`${id}-privacidad`} className="text-lg font-display font-bold uppercase text-foreground">Privacidad</h4>
            <p className="mt-1 text-sm text-muted">
              Todo es privado hasta que tú lo cambies. Tu nombre de usuario no es secreto; lo que proteges aquí es lo que hay en tu perfil.
            </p>
            {guardado.visibilidad === "privado" && (
              <p className="mt-1 text-xs text-muted">Mientras sea privado, quien abra tu enlace verá «Este perfil no existe o es privado».</p>
            )}
          </div>
          <SelectorNivel id={`${id}-visibilidad`} titulo="¿Quién ve tu perfil?" valor={visibilidad} onCambiar={setVisibilidad} explicaciones={{
            privado: "Solo tú. Los demás, también tus amigos, verán «Este perfil no existe o es privado».",
            amigos: "Tus amigos ven tu nombre de usuario, tu avatar, tu bio y tu Letterboxd; los demás, solo tu nombre y tu avatar, para poder añadirte.",
            publico: "Cualquiera con tu enlace ve tu nombre de usuario, tu avatar, tu bio y tu Letterboxd.",
          }} />

          <SelectorNivel id={`${id}-diario`} titulo="¿Quién ve tu diario?" valor={diario} onCambiar={setDiario} tope={visibilidad} explicaciones={{
            privado: "Solo tú.",
            amigos: "Tus amigos ven todas tus entradas, incluidas tus notas.",
            publico: "Cualquiera con tu enlace ve todas tus entradas, incluidas tus notas.",
          }} />

          <SelectorNivel id={`${id}-cines`} titulo="¿Quién ve tus cines favoritos?" valor={cines} onCambiar={setCines} tope={visibilidad} explicaciones={{
            privado: "Solo tú.",
            amigos: "Tus amigos ven la lista de los cines que has marcado con la ★.",
            publico: "Cualquiera con tu enlace ve la lista de los cines que has marcado con la ★.",
          }} />
        </section>

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
