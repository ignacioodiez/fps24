import TodayHeader from "@/components/TodayHeader";

// Email al que escribir para ejercer los derechos: cámbialo solo aquí
const EMAIL_CONTACTO = "ignacio.diez.vergara@gmail.com";
const ACTUALIZADA = "27 de octubre de 2026";

export const metadata = {
  title: "Privacidad - FPS24",
  description: "Qué datos guarda FPS24, para qué los usa, con quién se comparten y cómo ejercer tus derechos.",
};

const ENLACE = "text-primary font-bold hover:underline break-words";

function Seccion({ titulo, children }) {
  return (
    <section className="space-y-3">
      <h3 className="text-xl font-display font-bold uppercase text-foreground">{titulo}</h3>
      <div className="space-y-3 text-muted leading-relaxed">{children}</div>
    </section>
  );
}

export default function PrivacidadPage() {
  const email = <a href={`mailto:${EMAIL_CONTACTO}`} className={ENLACE}>{EMAIL_CONTACTO}</a>;

  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />

      <div className="max-w-3xl mx-auto px-4 md:px-6">
        <div className="text-center mb-10">
          <h2 className="text-4xl md:text-6xl font-black font-display uppercase text-foreground mb-4">
            <span className="text-primary">Privacidad</span>
          </h2>
          <p className="text-muted text-lg">Qué datos guardamos, para qué y cómo puedes controlarlos. Sin letra pequeña.</p>
        </div>

        <div className="space-y-10">
          <Seccion titulo="Quién es el responsable">
            <p>
              FPS24 (fps24.es) es un proyecto personal de <strong className="text-foreground">Ignacio Díez Vergara</strong>.
              Para cualquier duda sobre tus datos, escribe a {email}.
            </p>
          </Seccion>

          <Seccion titulo="Qué datos se guardan">
            <p>Puedes usar la cartelera sin cuenta. Si decides entrar, guardamos:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li>Tu <strong className="text-foreground">email</strong>, para enviarte el enlace de acceso e identificar tu cuenta.</li>
              <li>
                Si inicias sesión con <strong className="text-foreground">Google</strong>, recibimos de tu cuenta de Google
                solo tu email y tu nombre de perfil. Nada más: ni contactos, ni archivos, ni tu contraseña.
              </li>
              <li>
                Tu <strong className="text-foreground">diario</strong>: las películas que apuntes como vistas, con la fecha,
                el cine, tu nota y tu comentario si los añades. Es <strong className="text-foreground">privado por defecto</strong>:
                solo lo ves tú, salvo que elijas «Solo amigos» o «Público» en «¿Quién ve tu diario?».
              </li>
              <li>
                Tu <strong className="text-foreground">perfil</strong>, si decides crearlo (es opcional): un nombre de
                usuario y una bio corta. Para el perfil, el diario y los cines eliges entre tres niveles:{" "}
                <strong className="text-foreground">Privado</strong> (por defecto: solo tú),{" "}
                <strong className="text-foreground">Solo amigos</strong> y <strong className="text-foreground">Público</strong>{" "}
                (cualquiera con tu enlace, fps24.es/u/tu-usuario). Nunca se ve tu email. El diario y los cines nunca pueden
                ser más abiertos que el perfil: si lo cierras, se cierran con él. Si muestras tu diario, se ven todas sus
                entradas, incluidas tus notas y comentarios. Puedes cambiarlo cuando quieras y deja de verse al momento.
              </li>
              <li>
                Opcionalmente, un <strong className="text-foreground">avatar</strong> (tus iniciales sobre un color, o el
                póster de una película de nuestro catálogo, que viene de TMDB) y tu{" "}
                <strong className="text-foreground">usuario de Letterboxd</strong>. El avatar lo ve quien pueda ver tu
                perfil (con «Solo amigos», también quien no es tu amigo, junto a tu nombre de usuario); el Letterboxd, solo
                quien puede ver el perfil entero. Con el perfil privado no los ve nadie más que tú.
              </li>
              <li>
                Tus <strong className="text-foreground">cines favoritos</strong>, si marcas alguno con la ★: son privados
                por defecto y se usan para enseñarte primero sus sesiones. Solo aparecen en tu perfil si eliges «Solo
                amigos» o «Público» en «¿Quién ve tus cines favoritos?».
              </li>
              <li>
                Tus <strong className="text-foreground">sesiones guardadas</strong> («Mis sesiones»), si guardas alguna
                desde la hora de una sesión: película, cine, día, hora, versión y enlace de compra. Son privadas: solo
                las ves tú, nunca aparecen en tu perfil (ni para tus amigos), y se borran con tu cuenta.
              </li>
              <li>
                Tus <strong className="text-foreground">amigos</strong>, si añades a alguien: a quién has enviado una
                solicitud, quién te la ha enviado, a quién has aceptado y a quién has bloqueado, con la fecha. Lo ves solo
                tú, en la pestaña Amigos de tu perfil, y se borra con tu cuenta.
              </li>
              <li>
                Si te suscribes a la <strong className="text-foreground">newsletter</strong> «Esta semana en Madrid» (no
                hace falta cuenta): solo tu <strong className="text-foreground">email</strong> y las fechas de alta,
                confirmación y baja. Nada más: ni tu nombre ni qué abres o en qué pinchas.
              </li>
              <li>Próximamente, la lista de películas que marques como <strong className="text-foreground">&quot;quiero verla&quot;</strong>.</li>
            </ul>
          </Seccion>

          <Seccion titulo="Para qué">
            <p>
              Solo para identificar tu cuenta y guardar tus listas y tu diario. El diario (película, fecha, cine, nota y
              comentario) se usa para enseñártelo a ti en tu perfil y, solo si tú lo eliges, a tus amigos o a quien abra
              tu enlace. No vendemos tus datos ni los usamos para publicidad.
            </p>
            <p>
              El administrador de FPS24 tiene un panel con <strong className="text-foreground">cifras agregadas</strong>{" "}
              (cuántas cuentas, perfiles, entradas de diario y cines favoritos hay en total) y la lista de{" "}
              <strong className="text-foreground">nombres de usuario</strong>, también los de perfiles privados, con quién
              puede ver el perfil y si el diario es público, la fecha de alta y cuántas entradas y favoritos tiene cada uno (solo el
              número). Lo usa solo para mantener el servicio (por ejemplo, resolver problemas o retirar un nombre que
              suplante a otra persona). También puede ocultar películas de las destacadas, de Estrenos y de Especiales.
            </p>
            <p>
              Desde la web, el administrador <strong className="text-foreground">no ve tus entradas del diario, tus notas
              ni tus comentarios</strong>, ni tu email: si haces público tu diario, lo ve como cualquier otra persona con
              tu enlace. Los perfiles públicos no se muestran en buscadores.
            </p>
          </Seccion>

          <Seccion titulo="Amigos y bloqueo">
            <p>
              Una <strong className="text-foreground">amistad</strong> en FPS24 es mutua: una persona envía la solicitud
              (escribiendo tu nombre de usuario exacto) y la otra la acepta. Si las dos se la envían, queda aceptada sola.
              Puedes rechazar una solicitud, cancelar una que hayas enviado o quitar a un amigo cuando quieras; nadie
              recibe un aviso por ello. Al enviar una solicitud siempre ves el mismo mensaje, exista o no ese usuario.
            </p>
            <p>
              Lo que pongas en <strong className="text-foreground">«Solo amigos»</strong> lo ven únicamente tus amigos
              aceptados y con la sesión iniciada: nunca va en la página que se sirve sin sesión ni se guarda en cachés
              compartidas. Si tu perfil es «Solo amigos», quien no sea tu amigo verá solo tu nombre de usuario y tu
              avatar, con un botón para añadirte. Un perfil «Privado» no lo ven ni tus amigos.
            </p>
            <p>
              Si <strong className="text-foreground">bloqueas</strong> a alguien, deja de ser tu amigo, se borran las
              solicitudes entre los dos y ya no puede enviarte otras ni ver tu perfil: verá «Este perfil no existe o es
              privado», como si no existiera, sin saber que le has bloqueado. Puedes desbloquear desde la pestaña Amigos.
              Ten en cuenta que lo que tengas en «Público» se puede ver sin iniciar sesión.
            </p>
          </Seccion>

          <Seccion titulo="Newsletter">
            <p>
              Tu email se usa solo para enviarte, cada lunes, los estrenos y las sesiones especiales de la semana. Al
              suscribirte te mandamos un correo para <strong className="text-foreground">confirmar</strong> que el
              email es tuyo (doble confirmación): hasta que no pulses el enlace no recibes nada. Si no lo confirmas, no
              te volveremos a escribir.
            </p>
            <p>
              Puedes <strong className="text-foreground">darte de baja con un clic</strong> desde el enlace que va al
              pie de cada correo (o desde el botón «Cancelar suscripción» de tu gestor de correo). La baja es inmediata.
              Guardamos el email marcado como baja para no volver a escribirte; si quieres que lo borremos del todo,
              escríbenos. Los correos se envían con <strong className="text-foreground">Resend</strong>.
            </p>
          </Seccion>

          <Seccion titulo="Base legal">
            <p>
              Tu consentimiento al crear la cuenta y la necesidad de tratar esos datos para darte el servicio que pides
              (entrar y guardar tus listas). En la newsletter, tu consentimiento, que confirmas con el enlace del primer correo
              y puedes retirar en cualquier momento con la baja.
            </p>
          </Seccion>

          <Seccion titulo="Con quién se comparten">
            <p>Solo con los proveedores técnicos que hacen funcionar la web:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong className="text-foreground">Supabase</strong>: gestiona las cuentas.</li>
              <li><strong className="text-foreground">Google</strong>: si eliges &quot;Continuar con Google&quot;, actúa como proveedor de inicio de sesión y nos confirma tu email y tu nombre. Para mostrar su botón, la web carga un script de Google <strong className="text-foreground">solo cuando abres el panel de inicio de sesión</strong>; desde ese momento Google puede saber que lo has abierto y usar sus propias cookies, según su política de privacidad.</li>
              <li><strong className="text-foreground">Resend</strong>: envía los correos con el enlace de acceso y los de la newsletter (para eso recibe tu email).</li>
              <li><strong className="text-foreground">Vercel</strong> y <strong className="text-foreground">Render</strong>: alojan la web.</li>
            </ul>
            <p>No vendemos ni cedemos datos a terceros.</p>
          </Seccion>

          <Seccion titulo="Cuánto tiempo">
            <p>Mientras tengas cuenta. Si la eliminas, se borran tus datos.</p>
            <p>El email de la newsletter, mientras sigas suscrito; tras la baja, solo marcado como baja hasta que pidas borrarlo.</p>
          </Seccion>

          <Seccion titulo="Tus derechos">
            <p>
              Puedes pedir acceso a tus datos, rectificarlos, suprimirlos, oponerte a su uso o llevártelos (portabilidad).
              Escribe a {email} indicando qué necesitas.
            </p>
            <p>
              Si crees que no hemos atendido bien tu petición, puedes reclamar ante la{" "}
              <a href="https://www.aepd.es" target="_blank" rel="noopener noreferrer" className={ENLACE}>
                Agencia Española de Protección de Datos (AEPD)
              </a>.
            </p>
          </Seccion>

          <Seccion titulo="Analítica">
            <p>
              FPS24 <strong className="text-foreground">no usa cookies de analítica ni de seguimiento</strong>. Solo se
              guarda en tu navegador lo necesario para mantener tu sesión iniciada; si no inicias sesión, no se guarda nada. El script de Google del botón de inicio de sesión solo se carga si abres ese panel.
            </p>
          </Seccion>

          <p className="text-sm text-muted border-t border-line pt-6">Última actualización: {ACTUALIZADA}.</p>
        </div>
      </div>
    </main>
  );
}
