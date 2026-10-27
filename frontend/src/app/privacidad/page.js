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
                solo lo ves tú, salvo que actives «Mostrar mi diario en mi perfil».
              </li>
              <li>
                Tu <strong className="text-foreground">perfil</strong>, si decides crearlo (es opcional): un nombre de
                usuario y una bio corta. Es <strong className="text-foreground">privado por defecto</strong>. Si lo haces
                público, cualquiera con tu enlace (fps24.es/u/tu-usuario) verá tu nombre de usuario y tu bio, nunca tu email.
                Si además activas «Mostrar mi diario en mi perfil» (está apagado por defecto), verá también todas las
                entradas de tu diario, incluidas tus notas y comentarios. Puedes apagarlo o volver a hacer el perfil privado
                cuando quieras y deja de verse al momento.
              </li>
              <li>
                Opcionalmente, un <strong className="text-foreground">avatar</strong> (tus iniciales sobre un color, o el
                póster de una película de nuestro catálogo, que viene de TMDB) y tu{" "}
                <strong className="text-foreground">usuario de Letterboxd</strong>. Solo se ven en tu perfil público, es
                decir, si tú lo haces público; con el perfil privado no los ve nadie más que tú.
              </li>
              <li>
                Tus <strong className="text-foreground">cines favoritos</strong>, si marcas alguno con la ★: son privados
                por defecto y se usan para enseñarte primero sus sesiones. Solo aparecen en tu perfil público si lo haces
                público y activas «Mostrar mis cines favoritos en mi perfil público» (está apagado por defecto).
              </li>
              <li>
                Tus <strong className="text-foreground">sesiones guardadas</strong> («Mis sesiones»), si guardas alguna
                desde la hora de una sesión: película, cine, día, hora, versión y enlace de compra. Son privadas: solo
                las ves tú, nunca aparecen en tu perfil público, y se borran con tu cuenta.
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
              comentario) se usa para enseñártelo a ti en tu perfil y, solo si tú lo activas y tu perfil es público, a
              quien abra tu enlace. No vendemos tus datos ni los usamos para publicidad.
            </p>
            <p>
              El administrador de FPS24 tiene un panel con <strong className="text-foreground">cifras agregadas</strong>{" "}
              (cuántas cuentas, perfiles, entradas de diario y cines favoritos hay en total) y la lista de{" "}
              <strong className="text-foreground">nombres de usuario</strong>, también los de perfiles privados, con si
              el perfil y el diario son públicos, la fecha de alta y cuántas entradas y favoritos tiene cada uno (solo el
              número). Lo usa solo para mantener el servicio (por ejemplo, resolver problemas o retirar un nombre que
              suplante a otra persona). También puede ocultar películas de las destacadas, de Estrenos y de Especiales.
            </p>
            <p>
              Desde la web, el administrador <strong className="text-foreground">no ve tus entradas del diario, tus notas
              ni tus comentarios</strong>, ni tu email: si haces público tu diario, lo ve como cualquier otra persona con
              tu enlace. Los perfiles públicos no se muestran en buscadores.
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
