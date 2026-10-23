// Fuentes: para cambiar una, cambia su nombre aquí por otra de Google Fonts (TextFont = texto, DisplayFont = títulos)
import { Plus_Jakarta_Sans as TextFont, Nunito as DisplayFont } from "next/font/google";
import "./globals.css";
// 👇 IMPORTANTE: Importamos el componente Footer
import Footer from "@/components/Footer"; 
import AuthProvider from "@/components/AuthProvider";


// Si la nueva fuente no es variable, añade weight: ["400", "700", "900"]
const textFont = TextFont({ subsets: ["latin"], variable: "--font-text" });
const displayFont = DisplayFont({ subsets: ["latin"], variable: "--font-title" });

export const metadata = {
  title: "MadridFPS24",
  description: "Cartelera de cine independiente en Madrid",
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
        {/* MAIN: El contenido principal crece para empujar el footer */}
        <main className="flex-grow">
            {children}
        </main>
        {modal}
        </AuthProvider>

        {/* FOOTER: Siempre al final */}
        <Footer />
        
      </body>
    </html>
  );
}