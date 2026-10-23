import TodayHeader from "@/components/TodayHeader";

// Email al que escribir para ejercer los derechos: cámbialo solo aquí
const EMAIL_CONTACTO = "ignacio.diez.vergara@gmail.com";
const ACTUALIZADA = "23 de octubre de 2026";

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
                el cine, tu nota y tu comentario si los añades. Es privado: solo lo ves tú.
              </li>
              <li>Próximamente, la lista de películas que marques como <strong className="text-foreground">&quot;quiero verla&quot;</strong>.</li>
            </ul>
          </Seccion>

          <Seccion titulo="Para qué">
            <p>
              Solo para identificar tu cuenta y guardar tus listas y tu diario. El diario (película, fecha, cine, nota y
              comentario) solo se usa para enseñártelo a ti en tu perfil: nadie más puede verlo. No vendemos tus datos ni
              los usamos para publicidad.
            </p>
          </Seccion>

          <Seccion titulo="Base legal">
            <p>
              Tu consentimiento al crear la cuenta y la necesidad de tratar esos datos para darte el servicio que pides
              (entrar y guardar tus listas).
            </p>
          </Seccion>

          <Seccion titulo="Con quién se comparten">
            <p>Solo con los proveedores técnicos que hacen funcionar la web:</p>
            <ul className="list-disc pl-5 space-y-1">
              <li><strong className="text-foreground">Supabase</strong>: gestiona las cuentas.</li>
              <li><strong className="text-foreground">Google</strong>: si eliges &quot;Continuar con Google&quot;, actúa como proveedor de inicio de sesión y nos confirma tu email y tu nombre.</li>
              <li><strong className="text-foreground">Resend</strong>: envía los correos con el enlace de acceso.</li>
              <li><strong className="text-foreground">Vercel</strong> y <strong className="text-foreground">Render</strong>: alojan la web.</li>
            </ul>
            <p>No vendemos ni cedemos datos a terceros.</p>
          </Seccion>

          <Seccion titulo="Cuánto tiempo">
            <p>Mientras tengas cuenta. Si la eliminas, se borran tus datos.</p>
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
              guarda en tu navegador lo necesario para mantener tu sesión iniciada; si no inicias sesión, no se guarda nada.
            </p>
          </Seccion>

          <p className="text-sm text-muted border-t border-line pt-6">Última actualización: {ACTUALIZADA}.</p>
        </div>
      </div>
    </main>
  );
}
