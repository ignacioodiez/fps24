"use client";

import { notFound } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import { BOTON_PRIMARIO, BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import { Esqueleto } from "@/components/Perfil";
import { buscarAdmin, claveAdmin, enviarPruebaNewsletter, leerOcultas, leerResumen, leerUsuarios, mostrar, ocultar, vistaPreviaNewsletter } from "@/lib/admin";

const TITULO_SECCION = "text-xl font-display font-bold uppercase text-foreground";
const ERROR = "No hemos podido cargarlo. Recarga la página.";

const CIFRAS = [
  ["usuarios_totales", "Usuarios"],
  ["altas_7_dias", "Altas en 7 días"],
  ["altas_30_dias", "Altas en 30 días"],
  ["perfiles_con_usuario", "Perfiles con usuario"],
  ["perfiles_publicos", "Perfiles públicos"],
  ["diarios_publicos", "Diarios públicos"],
  ["entradas_diario", "Entradas de diario"],
  ["favoritos", "Cines favoritos"],
  ["suscriptores_activos", "Suscriptores newsletter"],
];

const fecha = (iso) => new Date(iso).toLocaleDateString("es-ES", { timeZone: "Europe/Madrid", day: "numeric", month: "short", year: "numeric" });

function Resumen() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => { leerResumen().then(setDatos, () => setError(true)); }, []);

  return (
    <section aria-labelledby="admin-resumen" className="space-y-4">
      <h3 id="admin-resumen" className={TITULO_SECCION}>Resumen</h3>
      {error ? <p role="alert" className="text-red-600">{ERROR}</p> : !datos ? <Esqueleto /> : (
        <>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {CIFRAS.map(([clave, etiqueta]) => (
              <div key={clave} className="border border-line bg-surface p-4">
                <dt className="text-xs font-semibold uppercase tracking-wider text-muted">{etiqueta}</dt>
                <dd className="text-3xl font-black font-display text-foreground mt-1">{datos[clave].toLocaleString("es-ES")}</dd>
              </div>
            ))}
          </dl>
          {datos.fuente_usuarios === "perfil" && (
            <p className="text-sm text-muted">Usuarios y altas cuentan perfiles: la API no puede leer las cuentas de Supabase (auth.users).</p>
          )}
        </>
      )}
    </section>
  );
}

function Usuarios() {
  const [pagina, setPagina] = useState(1);
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let vigente = true;
    leerUsuarios(pagina).then((d) => vigente && setDatos(d), () => vigente && setError(true));
    return () => { vigente = false; };
  }, [pagina]);
  const paginas = datos ? Math.max(1, Math.ceil(datos.total / datos.por_pagina)) : 1;

  return (
    <section aria-labelledby="admin-usuarios" className="space-y-4">
      <h3 id="admin-usuarios" className={TITULO_SECCION}>Usuarios con perfil {datos && <span className="text-muted">({datos.total})</span>}</h3>
      {error ? <p role="alert" className="text-red-600">{ERROR}</p> : !datos ? <Esqueleto /> : (
        <>
          {/* La tabla se desliza dentro de su caja en móvil; la página no */}
          <div className="overflow-x-auto border border-line" tabIndex={0} role="region" aria-label="Tabla de usuarios">
            <table className="w-full text-sm">
              <thead className="bg-surface text-left text-xs uppercase tracking-wider text-muted">
                <tr>
                  <th scope="col" className="px-3 py-2">Usuario</th>
                  <th scope="col" className="px-3 py-2">Perfil</th>
                  <th scope="col" className="px-3 py-2">Diario</th>
                  <th scope="col" className="px-3 py-2">Alta</th>
                  <th scope="col" className="px-3 py-2 text-right">Entradas</th>
                  <th scope="col" className="px-3 py-2 text-right">Favoritos</th>
                </tr>
              </thead>
              <tbody>
                {datos.usuarios.map((u) => (
                  <tr key={u.usuario} className="border-t border-line">
                    <th scope="row" className="px-3 py-2 text-left font-bold text-foreground break-all">@{u.usuario}</th>
                    <td className="px-3 py-2">{u.visibilidad === "publico" ? "Público" : "Privado"}</td>
                    <td className="px-3 py-2">{u.diario_publico ? "Visible" : "Oculto"}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{fecha(u.alta)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{u.entradas}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{u.favoritos}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!datos.usuarios.length && <p className="px-3 py-4 text-muted">Aún no hay perfiles.</p>}
          </div>
          {paginas > 1 && (
            <nav aria-label="Páginas de usuarios" className="flex items-center justify-between gap-3">
              <button type="button" className={BOTON_SECUNDARIO} disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>Anterior</button>
              <span className="text-sm text-muted" aria-live="polite">Página {pagina} de {paginas}</span>
              <button type="button" className={BOTON_SECUNDARIO} disabled={!datos.hay_siguiente} onClick={() => setPagina(pagina + 1)}>Siguiente</button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}

// sin_ficha: próximo estreno sin sesiones; solo sale en Estrenos, así que se oculta de ahí
function FilaPelicula({ pelicula, oculta, ocupada, onCambiar }) {
  const donde = pelicula.sin_ficha ? "estrenos" : "destacadas";
  return (
    <li className="flex items-center gap-3 border border-line bg-surface p-2">
      <div className="w-10 aspect-[2/3] shrink-0 overflow-hidden border border-line bg-background">
        {pelicula.poster_url && <img src={pelicula.poster_url} alt="" className="w-full h-full object-cover" loading="lazy" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="font-bold text-foreground break-words">{pelicula.titulo}</p>
        <p className="text-sm text-muted">
          {[pelicula.anio, pelicula.sin_ficha && "Próximo estreno, sin ficha", oculta && `Oculta de ${donde}`].filter(Boolean).join(" · ")}
        </p>
      </div>
      <button type="button" disabled={ocupada} onClick={onCambiar}
              aria-label={`${oculta ? `Mostrar en ${donde}` : `Ocultar de ${donde}`}: ${pelicula.titulo}`}
              className={`${oculta ? BOTON_PRIMARIO : BOTON_SECUNDARIO} shrink-0 min-h-11`}>
        {oculta ? "Mostrar" : `Ocultar de ${donde}`}
      </button>
    </li>
  );
}

function Peliculas() {
  const id = useId();
  const [texto, setTexto] = useState("");
  const [resultados, setResultados] = useState(null);
  const [ocultas, setOcultas] = useState(null);
  const [ocupada, setOcupada] = useState(null); // claveAdmin de la película que se está cambiando
  const [aviso, setAviso] = useState("");

  const recargarOcultas = () => leerOcultas().then(setOcultas, () => setAviso(ERROR));
  useEffect(() => { recargarOcultas(); }, []);
  const idsOcultas = new Set((ocultas ?? []).map(claveAdmin));

  const buscar = (e) => {
    e.preventDefault();
    if (texto.trim().length < 2) return setAviso("Escribe al menos 2 letras.");
    setAviso("Buscando…");
    buscarAdmin(texto.trim()).then(
      (lista) => { setResultados(lista); setAviso(`${lista.length} ${lista.length === 1 ? "resultado" : "resultados"}`); },
      () => setAviso("No hemos podido buscar. Inténtalo de nuevo."),
    );
  };

  const cambiar = async (pelicula, oculta) => {
    setOcupada(claveAdmin(pelicula));
    try {
      await (oculta ? mostrar : ocultar)(pelicula);
      await recargarOcultas();
      setAviso(`«${pelicula.titulo}» ${oculta ? `vuelve a ${pelicula.sin_ficha ? "estrenos" : "las destacadas"}`
        : pelicula.sin_ficha ? "ya no sale en estrenos" : "ya no sale en destacadas, estrenos ni especiales"}.`);
    } catch {
      setAviso("No se ha podido guardar. Inténtalo de nuevo.");
    } finally {
      setOcupada(null);
    }
  };

  return (
    <section aria-labelledby="admin-peliculas" className="space-y-4">
      <h3 id="admin-peliculas" className={TITULO_SECCION}>Películas ocultas</h3>
      <p className="text-sm text-muted">Una película oculta no sale en las destacadas de la portada, en Estrenos ni en Especiales. Sigue en la cartelera, en su ficha y en la búsqueda. Los próximos estrenos aún sin ficha solo salen en Estrenos: ocultarlos los quita de ahí.</p>
      <form onSubmit={buscar} role="search" className="flex gap-2">
        <label htmlFor={`${id}-q`} className="sr-only">Buscar película</label>
        <input id={`${id}-q`} type="search" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Buscar película…"
               className="min-w-0 flex-1 min-h-11 border border-line bg-background px-4 py-2 text-foreground focus:border-primary focus:outline-none" />
        <button type="submit" className={`${BOTON_PRIMARIO} min-h-11`}>Buscar</button>
      </form>
      <p role="status" aria-live="polite" className="text-sm text-muted">{aviso}</p>
      {resultados?.length > 0 && (
        <ul aria-label="Resultados de la búsqueda" className="space-y-2">
          {resultados.map((p) => (
            <FilaPelicula key={claveAdmin(p)} pelicula={p} oculta={idsOcultas.has(claveAdmin(p))} ocupada={ocupada === claveAdmin(p)}
                          onCambiar={() => cambiar(p, idsOcultas.has(claveAdmin(p)))} />
          ))}
        </ul>
      )}
      <h4 className="text-xs font-bold uppercase tracking-wider text-muted border-b border-line pb-2">
        Ocultas ahora {ocultas && `(${ocultas.length})`}
      </h4>
      {!ocultas ? <Esqueleto /> : ocultas.length ? (
        <ul aria-label="Películas ocultas" className="space-y-2">
          {ocultas.map((p) => (
            <FilaPelicula key={claveAdmin(p)} pelicula={p} oculta ocupada={ocupada === claveAdmin(p)} onCambiar={() => cambiar(p, true)} />
          ))}
        </ul>
      ) : <p className="text-muted">Ninguna.</p>}
    </section>
  );
}

function Newsletter() {
  const [html, setHtml] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState("");

  const verVistaPrevia = async () => {
    setOcupado(true);
    setAviso("Cargando la vista previa…");
    try {
      setHtml(await vistaPreviaNewsletter());
      setAviso("Vista previa de la newsletter de esta semana.");
    } catch {
      setAviso("No hemos podido cargar la vista previa.");
    } finally {
      setOcupado(false);
    }
  };

  const enviarPrueba = async () => {
    setOcupado(true);
    setAviso("Enviando la prueba…");
    try {
      const { enviado_a } = await enviarPruebaNewsletter();
      setAviso(`Prueba enviada a ${enviado_a}.`);
    } catch {
      setAviso("No se ha podido enviar la prueba. ¿Está configurada RESEND_API_KEY?");
    } finally {
      setOcupado(false);
    }
  };

  return (
    <section aria-labelledby="admin-newsletter" className="space-y-4">
      <h3 id="admin-newsletter" className={TITULO_SECCION}>Newsletter</h3>
      <p className="text-sm text-muted">Sale sola los lunes a las 16:00. La prueba llega solo a tu email de admin.</p>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={ocupado} onClick={verVistaPrevia} className={`${BOTON_SECUNDARIO} min-h-11`}>Ver vista previa</button>
        <button type="button" disabled={ocupado} onClick={enviarPrueba} className={`${BOTON_PRIMARIO} min-h-11`}>Enviarme una prueba</button>
      </div>
      <p role="status" aria-live="polite" className="text-sm text-muted">{aviso}</p>
      {html && (
        <iframe title="Vista previa de la newsletter" srcDoc={html} sandbox=""
                className="w-full max-w-[640px] h-[80vh] border border-line bg-white" />
      )}
    </section>
  );
}

// El enlace solo sale con es_admin, pero /admin se puede abrir a mano: sin ser admin, el 404 normal
export default function PanelAdmin() {
  const { cargando, esAdmin } = useAuth();
  if (!AUTH_DISPONIBLE || (!cargando && esAdmin === false)) notFound();
  if (cargando || !esAdmin) return <div className="max-w-5xl mx-auto px-4 md:px-6"><Esqueleto /></div>;

  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 space-y-12">
      <h2 className="text-3xl md:text-5xl font-black font-display uppercase text-primary">Admin</h2>
      <Resumen />
      <Usuarios />
      <Peliculas />
      <Newsletter />
    </div>
  );
}
