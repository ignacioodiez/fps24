// Fuentes: para cambiar una, cambia su nombre aquí por otra de Google Fonts (TextFont = texto, DisplayFont = títulos)
import { Plus_Jakarta_Sans as TextFont, Nunito as DisplayFont } from "next/font/google";
import "./globals.css";
// 👇 IMPORTANTE: Importamos el componente Footer
import Footer from "@/components/Footer"; 
import AuthProvider from "@/components/AuthProvider";
import PanelLogin, { ElegirUsuario } from "@/components/PanelLogin";
import FavoritosProvider from "@/components/FavoritosProvider";
import SesionesGuardadasProvider from "@/components/SesionesGuardadasProvider";
import { Analytics } from "@vercel/analytics/next";


// Si la nueva fuente no es variable, añade weight: ["400", "700", "900"]
const textFont = TextFont({ subsets: ["latin"], variable: "--font-text" });
const displayFont = DisplayFont({ subsets: ["latin"], variable: "--font-title" });

// metadataBase: canonical y Open Graph relativos salen absolutos. Sin canonical aquí: lo heredarían todas las páginas
export const metadata = {
  metadataBase: new URL("https://fps24.es"),
  title: "Cartelera de cine en Madrid: horarios, VOSE y precios | fps24",
  description: "Todas las sesiones de los cines independientes y de autor de Madrid en una cartelera: horarios, versión original, precios y día del espectador.",
  openGraph: { siteName: "fps24", locale: "es_ES", type: "website", images: ["/logofps24.png"] },
  twitter: { card: "summary" },
  icons: {
    icon: "/logofps24.png", 
    apple: "/logofps24.png",
  },
};

// modal: hueco paralelo (app/@modal) para la vista rápida de una película sobre la portada
export default function RootLayout({ children, modal }) {
  return (
    <html lang="es" className={`${textFont.variable} ${displayFont.variable}`}>
      <body
        className="font-sans bg-background text-foreground antialiased flex flex-col min-h-screen"
      >
        <AuthProvider>
        <FavoritosProvider>
        <SesionesGuardadasProvider>
        {/* MAIN: El contenido principal crece para empujar el footer */}
        <main className="flex-grow">
            {children}
        </main>
        {modal}
        <PanelLogin />
        <ElegirUsuario />
        </SesionesGuardadasProvider>
        </FavoritosProvider>
        </AuthProvider>

        {/* FOOTER: Siempre al final */}
        <Footer />
        <Analytics />
      </body>
    </html>
  );
}