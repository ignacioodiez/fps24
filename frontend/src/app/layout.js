import { Inter, Kanit, Raleway } from "next/font/google";
import "./globals.css";
// 👇 IMPORTANTE: Importamos el componente Footer
import Footer from "@/components/Footer"; 
import Script from "next/script"; // 👈 NUEVO
import { GA_TRACKING_ID } from "@/lib/gtag"; // 👈 NUEVO


// 1. Fuente Base
const inter = Inter({ subsets: ["latin"] });

// 2. Fuente para Títulos
const kanit = Kanit({
  weight: "800",
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
  description: "Cartelera de cine independiente en Madrid",
  icons: {
    icon: "/logofps24.png", 
    apple: "/logofps24.png",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="es">
      <head>
        <Script
          strategy="afterInteractive"
          src={`https://www.googletagmanager.com/gtag/js?id=${GA_TRACKING_ID}`}
        />
        <Script
          id="google-analytics"
          strategy="afterInteractive"
          dangerouslySetInnerHTML={{
            __html: `
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
              gtag('config', '${GA_TRACKING_ID}', {
                page_path: window.location.pathname,
              });
            `,
          }}
        />
      </head>
      {/* 👆 FIN GOOGLE ANALYTICS */}


      <body
        className={`${inter.className} ${kanit.variable} ${raleway.variable} bg-black antialiased text-white flex flex-col min-h-screen`}
      >
        {/* MAIN: El contenido principal crece para empujar el footer */}
        <main className="flex-grow">
            {children}
        </main>

        {/* FOOTER: Siempre al final */}
        <Footer />
        
      </body>
    </html>
  );
}