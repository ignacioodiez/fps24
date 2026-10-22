import TarjetaEspecial from "@/components/TarjetaEspecial";

// Escritorio: cuadrícula de 4x4 que llena siempre el cuadrado (mismo alto que estrenos). La 1ª (mayor nota)
// es grande; las demás, compactas. Clases literales para que Tailwind las genere. Por nº de tarjetas:
//  1: AAAA   2: AABB   3: AABB   4: AABB   5: AABB   6: AABB   7: AABB
//     AAAA      AABB      AABB      AABB      AACC      AACC      AACC
//     AAAA      AABB      AACC      CCDD      DDEE      DDEE      DDEE
//     AAAA      AABB      AACC      CCDD      DDEE      FFFF      FFGG
const G22 = "md:col-span-2 md:row-span-2";
const DISPOSICION = {
  1: ["md:col-span-4 md:row-span-4"],
  2: ["md:col-span-2 md:row-span-4", "md:col-span-2 md:row-span-4"],
  3: ["md:col-span-2 md:row-span-4", G22, G22],
  4: [G22, G22, G22, G22],
  5: [G22, "md:col-span-2", "md:col-span-2", G22, G22],
  6: [G22, "md:col-span-2", "md:col-span-2", "md:col-span-2", "md:col-span-2", "md:col-span-4"],
  7: [G22, "md:col-span-2", "md:col-span-2", "md:col-span-2", "md:col-span-2", "md:col-span-2", "md:col-span-2"],
};

// Con 7 caben todas legibles: las compactas miden 2 columnas x 1 fila (unos 290x95 px a 1280 px de ancho).
export default function MosaicoEspeciales({ especiales }) {
  const lista = especiales.slice(0, 7);
  const celdas = DISPOSICION[lista.length] || [];
  // Móvil (2 columnas): la 1ª ocupa las dos; si el resto es impar, también la última, para no dejar hueco
  const ultimaAncha = (lista.length - 1) % 2 === 1;

  return (
    <ul className="grid grid-cols-2 md:grid-cols-4 md:grid-rows-4 md:h-full gap-2">
      {lista.map((especial, i) => (
        <TarjetaEspecial
          key={especial.pase.id}
          especial={especial}
          grande={i === 0}
          // Con 1-3 la grande ocupa todo el alto: hay sitio para la sinopsis
          amplia={i === 0 && lista.length <= 3}
          className={`${i === 0 || (ultimaAncha && i === lista.length - 1) ? "col-span-2" : ""} ${celdas[i]}`}
        />
      ))}
    </ul>
  );
}
