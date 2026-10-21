import Link from "next/link";

// El SVG es un lienzo cuadrado con el logo en una franja central (~3:1): object-cover recorta el margen vacío.
export default function Logo({ className = "h-12" }) {
  return (
    <Link href="/" className="inline-block">
      <img src="/FPS24.svg" alt="MadridFPS24" className={`${className} w-auto aspect-[3/1] object-cover`} />
    </Link>
  );
}
