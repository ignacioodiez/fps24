import type { Metadata } from "next";
import { Inter, Kanit, Raleway } from "next/font/google"; // <--- Importamos Kanit
import "./globals.css";

// 1. Fuente Base
const inter = Inter({ subsets: ["latin"] });

// 2. Fuente para Títulos (Sustituimos Anton por KANIT)
const kanit = Kanit({
  weight: "800", // Peso ExtraBold para que tenga impacto
  subsets: ["latin"],
  variable: "--font-kanit",
});

// 3. Fuente para Textos de Pelis
const raleway = Raleway({
  subsets: ["latin"],
  variable: "--font-raleway",
});

export const metadata = {
  title: "MadridFPS24",
  description: "Cartelera de cine alternativo y eventos en Madrid",
  // AÑADE ESTO 👇
  icons: {
    icon: "/logofps24.png", // La ruta a tu archivo en 'public'
    apple: "/logofps24.png", // Para cuando alguien lo guarde en el iPhone
  },
};
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${inter.className} ${kanit.variable} ${raleway.variable} bg-gray-900 antialiased text-white`}
      >
        {children}
      </body>
    </html>
  );
}