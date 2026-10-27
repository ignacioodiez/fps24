"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useState } from "react";
import { AUTH_DISPONIBLE, useAuth } from "@/components/AuthProvider";
import DialogoDiario, { BOTON_PRIMARIO, BOTON_SECUNDARIO } from "@/components/DialogoDiario";
import NotaEstrellas from "@/components/NotaEstrellas";
import {
  Ayuda, CabeceraPerfil, PestanaPerfil, PestanasPerfil, SoloTu, TarjetasCines, TITULO_SECCION, formato, nombreMes, porMes,
} from "@/components/PerfilVistas";
import TarjetaPerfilPublico from "@/components/TarjetaPerfilPublico";
import { useFavoritos } from "@/components/FavoritosProvider";
import { DIARIO_GUARDADO, borrar, listar, todosLosCines } from "@/lib/diario";

const POR_PAGINA = 20;
const COMENTARIO_CORTO = 240; // más largo (o con más de 3 líneas) se recorta con "ver más"

// Mismo orden que el backend: fecha vista y, a igual fecha, la última apuntada primero
const ordenar = (lista) => [...lista].sort((a, b) => b.fecha_vista.localeCompare(a.fecha_vista) || b.creado_en.localeCompare(a.creado_en) || b.id - a.id);

function Comentario({ texto }) {
  const [abierto, setAbierto] = useState(false);
  const largo = texto.length > COMENTARIO_CORTO || texto.split("\n").length > 3;
  return (
    <div className="mt-2 text-sm text-foreground">
      {/* Texto plano con sus saltos de línea: nunca HTML */}
      <p className={`whitespace-pre-wrap break-words ${largo && !abierto ? "line-clamp-3" : ""}`}>{texto}</p>
      {largo && (
        <button type="button" onClick={() => setAbierto((v) => !v)} aria-expanded={abierto} className="mt-1 text-xs font-bold text-primary hover:underline">
          {abierto ? "ver menos" : "ver más"}
        </button>
      )}
    </div>
  );
}

// Sin onEditar/onBorrar (perfil de otra persona) es solo lectura
function Entrada({ entrada, marcada, onEditar, onBorrar }) {
  const [confirmar, setConfirmar] = useState(false);
  const [borrando, setBorrando] = useState(false);
  const { pelicula, cine } = entrada;

  const eliminar = async () => {
    setBorrando(true);
    if (!(await onBorrar(entrada))) setBorrando(false);
  };

  return (
    <li id={entrada.id ? `entrada-${entrada.id}` : undefined} className={`flex gap-3 md:gap-4 py-4 border-b border-line transition-colors duration-700 ${marcada ? "bg-primary-soft" : ""}`}>
      <div className="w-12 md:w-16 aspect-[2/3] shrink-0 overflow-hidden border border-line bg-surface">
        {pelicula.poster_url && <img src={pelicula.poster_url} alt="" className="w-full h-full object-cover" loading="lazy" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          {/* <a> y no <Link>: con Link se abriría la vista rápida encima y el diario no se enteraría de los cambios */}
          <a href={`/pelicula/${pelicula.id}`} className="font-display font-bold uppercase text-foreground hover:text-primary break-words">
            {pelicula.titulo}
          </a>
          {pelicula.anio && <span className="text-sm text-muted">{pelicula.anio}</span>}
          {entrada.repeticion && (
            <span className="text-[11px] font-semibold uppercase tracking-wider text-primary bg-primary-soft px-1.5 py-0.5">Repetición</span>
          )}
        </div>
        <p className="mt-1 text-sm text-muted">
          <time dateTime={entrada.fecha_vista}>{formato(entrada.fecha_vista, { day: "numeric", month: "long", year: "numeric" })}</time>
          {cine && <> · <Link href={`/cines/${cine.slug}`} className="text-foreground hover:text-primary hover:underline">{cine.nombre}</Link></>}
        </p>
        {entrada.nota && <div className="mt-1"><NotaEstrellas valor={entrada.nota} soloLectura /></div>}
        {entrada.comentario && <Comentario texto={entrada.comentario} />}

        {onEditar && (
          <div className="mt-2 flex flex-wrap items-center gap-3 text-sm font-bold">
            {confirmar ? (
              <>
                <span className="font-normal text-foreground">¿Eliminar esta entrada?</span>
                <button type="button" onClick={eliminar} disabled={borrando} className="text-red-600 hover:underline disabled:opacity-60">
                  {borrando ? "Eliminando…" : "Sí, eliminar"}
                </button>
                <button type="button" onClick={() => setConfirmar(false)} className="text-muted hover:text-foreground">No</button>
              </>
            ) : (
              <>
                <button type="button" aria-haspopup="dialog" onClick={() => onEditar(entrada)} className="text-primary hover:underline">
                  Editar<span className="sr-only"> {pelicula.titulo}</span>
                </button>
                <button type="button" onClick={() => setConfirmar(true)} className="text-muted hover:text-red-600">
                  Eliminar<span className="sr-only"> {pelicula.titulo}</span>
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

// Entradas agrupadas por mes, en el orden de la lista. Las del perfil público no traen id: clave por posición.
export function ListaDiario({ entradas, marcada, onEditar, onBorrar }) {
  return porMes(entradas).map((m) => (
    <section key={m.clave} aria-labelledby={`mes-${m.clave}`} className="mt-6">
      <h3 id={`mes-${m.clave}`} className="text-xs font-bold uppercase tracking-wider text-muted border-b border-line pb-2">
        {nombreMes(`${m.clave}-01`)}
      </h3>
      <ul>
        {m.entradas.map((e, i) => (
          <Entrada key={e.id ?? i} entrada={e} marcada={e.id && e.id === marcada} onEditar={onEditar} onBorrar={onBorrar} />
        ))}
      </ul>
    </section>
  ));
}

// Mi diario: editar y borrar. Para añadir está el "+" de la barra (BotonAnadirDiario), que avisa con DIARIO_GUARDADO.
function MiDiario() {
  const [entradas, setEntradas] = useState([]);
  const [total, setTotal] = useState(0);
  const [estado, setEstado] = useState("cargando"); // cargando | listo | error
  const [error, setError] = useState("");
  const [editando, setEditando] = useState(null);
  const [aviso, setAviso] = useState("");
  const [marcada, setMarcada] = useState(null); // id de la entrada recién añadida

  // desplazamiento 0 = primera página; si no, se añade a lo cargado (sin repetir: un borrado mueve el desplazamiento)
  const pedirPagina = useCallback((desplazamiento) => {
    listar(POR_PAGINA, desplazamiento)
      .then((datos) => {
        setEntradas((previas) => {
          const base = desplazamiento ? previas : [];
          return ordenar([...base, ...datos.entradas.filter((e) => !base.some((b) => b.id === e.id))]);
        });
        setTotal(datos.total);
        setEstado("listo");
      })
      .catch((err) => {
        setError(err.message);
        setEstado("error");
      });
  }, []);

  useEffect(() => pedirPagina(0), [pedirPagina]);

  useEffect(() => {
    const anadida = ({ detail: guardada }) => {
      setEntradas((previas) => ordenar([...previas, guardada]));
      setTotal((t) => t + 1);
      setMarcada(guardada.id);
    };
    window.addEventListener(DIARIO_GUARDADO, anadida);
    return () => window.removeEventListener(DIARIO_GUARDADO, anadida);
  }, []);

  // La entrada recién añadida: a la vista y marcada un momento
  useEffect(() => {
    if (!marcada) return;
    document.getElementById(`entrada-${marcada}`)?.scrollIntoView({ block: "center" });
    const t = setTimeout(() => setMarcada(null), 2000);
    return () => clearTimeout(t);
  }, [marcada]);

  const cargarMas = () => {
    setEstado("cargando");
    pedirPagina(entradas.length);
  };

  const quitar = (id) => {
    setEntradas((previas) => previas.filter((e) => e.id !== id));
    setTotal((t) => t - 1);
  };

  const borrarEntrada = async (entrada) => {
    try {
      await borrar(entrada.id);
      quitar(entrada.id);
      setAviso(`«${entrada.pelicula.titulo}» eliminada del diario`);
      return true;
    } catch (err) {
      setAviso(err.message);
      return false;
    }
  };

  return (
    <div>
      <p role="status" aria-live="polite" className="text-sm font-semibold text-primary min-h-5">{aviso}</p>

      {estado === "cargando" && entradas.length === 0 ? (
        <Esqueleto />
      ) : estado === "error" && entradas.length === 0 ? (
        <p role="alert" className="py-8 text-red-600">{error}</p>
      ) : entradas.length === 0 ? (
        <p className="py-12 text-center text-lg text-foreground">
          Tu diario está vacío. Pulsa <strong>+</strong> en la barra de arriba para añadir una película que hayas visto.
        </p>
      ) : (
        <>
          <ListaDiario entradas={entradas} marcada={marcada} onEditar={setEditando} onBorrar={borrarEntrada} />
          {entradas.length < total && (
            <div className="mt-6 text-center">
              <button type="button" onClick={cargarMas} disabled={estado === "cargando"} className={BOTON_SECUNDARIO}>
                {estado === "cargando" ? "Cargando…" : "Cargar más"}
              </button>
              {estado === "error" && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
            </div>
          )}
        </>
      )}

      {editando && (
        <DialogoDiario
          pelicula={editando.pelicula} entrada={editando}
          onCerrar={() => setEditando(null)}
          onGuardado={(guardada) => {
            setEntradas((previas) => ordenar(previas.map((e) => (e.id === guardada.id ? guardada : e))));
            setAviso(`«${guardada.pelicula.titulo}» actualizada`);
          }}
          onBorrado={(id) => {
            quitar(id);
            setAviso(`«${editando.pelicula.titulo}» eliminada del diario`);
          }}
        />
      )}
    </div>
  );
}

export function Esqueleto() {
  return (
    <div aria-busy="true" aria-label="Cargando" className="space-y-4 py-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex gap-4">
          <div className="w-12 md:w-16 aspect-[2/3] bg-surface animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-5 w-1/2 bg-surface animate-pulse" />
            <div className="h-4 w-1/3 bg-surface animate-pulse" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Mis cines favoritos (solo los ve su dueño): la lista, quitar y enlace a /cines para añadir más.
// Los nombres salen de GET /cines (público); el orden, el de alta.
function MisCines() {
  const { favoritos, cargados, alternar } = useFavoritos();
  const { miPerfil } = useAuth();
  const visibles = miPerfil?.visibilidad === "publico" && miPerfil?.cines_publicos;
  const [cines, setCines] = useState(null);
  const id = useId();

  useEffect(() => {
    todosLosCines().then(setCines).catch(() => setCines([]));
  }, []);

  const nombre = (slug) => cines?.find((c) => c.slug === slug)?.nombre ?? slug;

  return (
    <section aria-labelledby={`${id}-titulo`} className="mt-8">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id={`${id}-titulo`} className={TITULO_SECCION}>Mis cines</h3>
        <Link href="/cines" className="text-sm font-bold text-primary hover:underline">Añadir más cines →</Link>
      </div>
      {!cargados || !cines ? (
        <div aria-busy="true" aria-label="Cargando tus cines" className="mt-3 h-11 bg-surface animate-pulse" />
      ) : favoritos.size === 0 ? (
        <p className="mt-3 text-muted">
          Aún no tienes cines favoritos. Pulsa la ★ en un cine de <Link href="/cines" className="font-bold text-primary hover:underline">Cines</Link> y
          sus sesiones saldrán primero en toda la web.
        </p>
      ) : (
        <>
          <p className="mt-1 text-sm text-muted">Sus sesiones salen primero en toda la web. {visibles ? "También se ven en tu perfil público." : "Solo tú ves esta lista."}</p>
          <ul className="mt-3 flex flex-wrap gap-2">
            {[...favoritos].map((slug) => (
              <li key={slug} className="flex items-center border border-line bg-surface">
                <Link href={`/cines/${slug}`} className="px-3 py-2 text-sm font-bold text-foreground hover:text-primary">
                  <span aria-hidden="true" className="text-primary">★</span> {nombre(slug)}
                </Link>
                <button type="button" onClick={() => alternar(slug, nombre(slug))} aria-label={`Quitar ${nombre(slug)} de mis cines`}
                        className="self-stretch px-3 border-l border-line text-muted hover:text-red-600 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary">
                  <span aria-hidden="true">×</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

// /u/<mi usuario>[/diario|/cines]: mi vista, aunque el perfil sea privado. Ve todas las pestañas y las secciones
// vacías (con ayuda), y debajo de las que los demás no ven, "Solo tú ves...". Los datos salen de mis endpoints.
function MiPerfil({ perfil, pestana }) {
  const { favoritos, cargados, alternar } = useFavoritos();
  const [todos, setTodos] = useState(null); // GET /cines, para nombre y zona de mis favoritos
  const [diario, setDiario] = useState(null); // GET /diario: { total, este_anio, entradas } o { error }

  useEffect(() => {
    todosLosCines().then(setTodos).catch(() => setTodos([]));
  }, []);

  // Las últimas entradas para la pestaña Perfil; se recargan al añadir una desde el "+" de la barra
  useEffect(() => {
    if (pestana !== "perfil") return;
    const cargar = () => listar(30, 0).then(setDiario).catch((err) => setDiario({ error: err.message }));
    cargar();
    window.addEventListener(DIARIO_GUARDADO, cargar);
    return () => window.removeEventListener(DIARIO_GUARDADO, cargar);
  }, [pestana]);

  const publico = perfil.visibilidad === "publico";
  const diarioSoloTu = !(publico && perfil.diario_publico);
  const cinesSoloTu = !(publico && perfil.cines_publicos);
  const cines = cargados && todos ? [...favoritos].map((slug) => todos.find((c) => c.slug === slug) ?? { slug, nombre: slug }) : null;
  const quienVe = !publico
    ? "Quien abra tu enlace verá «Este perfil no existe o es privado». Hazlo público en «Editar mi perfil» para compartirlo."
    : `Cualquiera con tu enlace ve tu nombre de usuario, tu avatar, tu bio y tu Letterboxd. ${
      perfil.diario_publico ? "También tu diario, con tus notas." : "Tu diario no se muestra."} ${
      perfil.cines_publicos ? "También tus cines favoritos." : "Tus cines favoritos no se muestran."}`;

  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 py-8">
      <CabeceraPerfil
        perfil={perfil} esDueno
        cifras={{ entradas: diario?.total, este_anio: diario?.este_anio, cines: cines?.length }}
      />
      {(!publico || pestana === "perfil") && (
        <div role={publico ? undefined : "note"} className={`mt-6 border p-4 ${publico ? "border-line bg-surface" : "border-primary bg-primary-soft"}`}>
          <p className="font-bold text-foreground">{publico ? "Tu perfil es público" : "Tu perfil es privado: solo tú lo ves"}</p>
          <p className="text-sm text-muted">{quienVe}</p>
        </div>
      )}
      <PestanasPerfil usuario={perfil.usuario} actual={pestana} visibles={["perfil", "diario", "cines"]} />

      {pestana === "perfil" && (
        diario?.error ? <p role="alert" className="py-8 text-red-600">{diario.error}</p>
          : !diario || !cines ? <Esqueleto />
            : <PestanaPerfil usuario={perfil.usuario} entradas={diario.entradas} total={diario.total} cines={cines} esDueno
                             diarioSoloTu={diarioSoloTu} cinesSoloTu={cinesSoloTu} />
      )}
      {pestana === "diario" && (
        <section aria-labelledby="mi-diario" className="mt-8">
          <h3 id="mi-diario" className={TITULO_SECCION}>Mi diario</h3>
          {diarioSoloTu && <SoloTu que="tu diario" />}
          <MiDiario />
        </section>
      )}
      {pestana === "cines" && (
        <section aria-labelledby="mis-cines" className="mt-8">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 id="mis-cines" className={TITULO_SECCION}>Mis cines</h3>
            <Link href="/cines" className="text-sm font-bold text-primary hover:underline">Añadir más cines →</Link>
          </div>
          {cinesSoloTu && <SoloTu que="tus cines" />}
          {!cines ? <div aria-busy="true" aria-label="Cargando tus cines" className="mt-6 h-20 bg-surface animate-pulse" />
            : cines.length ? <TarjetasCines cines={cines} onQuitar={(c) => alternar(c.slug, c.nombre)} />
              : <Ayuda>Aún no tienes cines favoritos. Pulsa la ★ en un cine de <Link href="/cines" className="font-bold text-primary hover:underline">Cines</Link> y sus sesiones saldrán primero en toda la web.</Ayuda>}
        </section>
      )}
    </div>
  );
}

const usuarioDeRuta = (ruta) => decodeURIComponent(ruta.split("/")[2] ?? "").toLowerCase();
const pestanaDeRuta = (ruta) => ({ diario: "diario", cines: "cines" })[ruta.split("/")[3]] ?? "perfil";

// En /u/[usuario]: si el visitante es el dueño, su vista; si no, children (la pública o el "no existe o es privado").
// esperar: mientras no se sabe, esqueleto en vez de children (en el 404, para no enseñarle al dueño "no existe").
export function SiSoyYo({ esperar = false, children }) {
  const { cargando, miPerfil } = useAuth();
  const ruta = usePathname();
  if (miPerfil?.usuario && miPerfil.usuario === usuarioDeRuta(ruta)) return <MiPerfil perfil={miPerfil} pestana={pestanaDeRuta(ruta)} />;
  if (esperar && (cargando || miPerfil === undefined)) {
    return <div className="max-w-3xl mx-auto px-4 md:px-6"><Esqueleto /></div>;
  }
  return children;
}

// /perfil: a /u/<mi usuario> o, sin usuario (o sin sesión), a la edición
export function IrAMiPerfil() {
  const { cargando, miPerfil } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (cargando || miPerfil === undefined) return;
    router.replace(miPerfil?.usuario ? `/u/${miPerfil.usuario}` : "/perfil/editar");
  }, [cargando, miPerfil, router]);
  return <div className="max-w-3xl mx-auto px-4 md:px-6"><Esqueleto /></div>;
}

// /perfil/editar: nombre, bio, visibilidad y diario público; debajo, mis cines y mis entradas
export default function EditarPerfil() {
  const { usuario, cargando, abrirLogin, miPerfil } = useAuth();
  const id = useId();

  if (cargando) {
    return <div className="max-w-3xl mx-auto px-4 md:px-6"><Esqueleto /></div>;
  }

  if (!usuario) {
    return (
      <div className="max-w-3xl mx-auto px-4 md:px-6 py-12 text-center space-y-4">
        <h2 className="text-3xl md:text-5xl font-black font-display uppercase text-primary">Mi perfil</h2>
        <p className="text-muted text-lg">
          {AUTH_DISPONIBLE ? "Inicia sesión para ver tu diario de películas." : "El inicio de sesión no está disponible ahora mismo."}
        </p>
        {AUTH_DISPONIBLE && (
          <button type="button" onClick={() => abrirLogin("Inicia sesión para ver tu diario")} aria-haspopup="dialog" className={BOTON_PRIMARIO}>
            Iniciar sesión
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-6">
      <div className="mb-6">
        <h2 className="text-3xl md:text-5xl font-black font-display uppercase text-primary">Editar mi perfil</h2>
        <p className="mt-1 text-muted">
          <span className="break-all">{usuario.email}</span>
          {miPerfil?.usuario && <> · <Link href={`/u/${miPerfil.usuario}`} className="font-bold text-primary hover:underline">Ver mi perfil</Link></>}
        </p>
      </div>

      <TarjetaPerfilPublico />

      <MisCines />

      <section aria-labelledby={`${id}-diario`} className="mt-8">
        <h3 id={`${id}-diario`} className={TITULO_SECCION}>Mi diario</h3>
        <MiDiario />
      </section>
    </div>
  );
}
