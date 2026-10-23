// Mosaico de /especiales: el tamaño de cada tarjeta según su puesto en el ranking, para 2, 3 y 4 columnas.
// [ancho, alto] en celdas; "completa" (solo si hay una) ocupa todo el ancho.
const TAMANOS = { grande: [2, 2], alta: [1, 2], ancha: [2, 1], normal: [1, 1] };
// Tras la 1ª (grande) se repite: alta, dos normales, ancha, dos normales
const PATRON = ["alta", "normal", "normal", "ancha", "normal", "normal"];

// Clases literales para que Tailwind las genere: móvil 2 columnas, tablet (md) 3, escritorio (lg) 4
const CLASES = {
  2: { completa: "col-span-2 row-span-2", grande: "col-span-2 row-span-2", alta: "col-span-1 row-span-2", ancha: "col-span-2 row-span-1", normal: "col-span-1 row-span-1" },
  3: { completa: "md:col-span-3 md:row-span-2", grande: "md:col-span-2 md:row-span-2", alta: "md:col-span-1 md:row-span-2", ancha: "md:col-span-2 md:row-span-1", normal: "md:col-span-1 md:row-span-1" },
  4: { completa: "lg:col-span-4 lg:row-span-2", grande: "lg:col-span-2 lg:row-span-2", alta: "lg:col-span-1 lg:row-span-2", ancha: "lg:col-span-2 lg:row-span-1", normal: "lg:col-span-1 lg:row-span-1" },
};

// Coloca como CSS grid con grid-auto-flow: dense -> celdas vacías hasta la última fila ocupada
export function huecos(tamanos, cols) {
  const ocupadas = new Set();
  let filas = 0;
  for (const t of tamanos) {
    const [ancho, alto] = t === "completa" ? [cols, 2] : TAMANOS[t];
    for (let f = 0, puesta = false; !puesta; f++) {
      for (let c = 0; c + ancho <= cols && !puesta; c++) {
        const celdas = [];
        for (let df = 0; df < alto; df++) for (let dc = 0; dc < ancho; dc++) celdas.push(`${f + df},${c + dc}`);
        if (celdas.some((x) => ocupadas.has(x))) continue;
        celdas.forEach((x) => ocupadas.add(x));
        filas = Math.max(filas, f + alto);
        puesta = true;
      }
    }
  }
  return filas * cols - ocupadas.size;
}

// El patrón deja huecos al final según cuántas haya: las 3 últimas cambian de tamaño hasta que no quede
// ninguno (con empate, la combinación que menos se aparta del patrón)
export function disposicion(n, cols) {
  if (n === 1) return ["completa"];
  const base = ["grande", ...Array.from({ length: n - 1 }, (_, i) => PATRON[i % PATRON.length])];
  const k = Math.min(3, n - 1);
  const nombres = Object.keys(TAMANOS);
  let mejor = null;
  for (let combo = 0; combo < nombres.length ** k; combo++) {
    const cola = Array.from({ length: k }, (_, i) => nombres[Math.floor(combo / nombres.length ** i) % nombres.length]);
    const prueba = [...base.slice(0, n - k), ...cola];
    const coste = [huecos(prueba, cols), cola.filter((t, i) => t !== base[n - k + i]).length];
    if (!mejor || coste[0] < mejor.coste[0] || (coste[0] === mejor.coste[0] && coste[1] < mejor.coste[1])) {
      mejor = { coste, prueba };
    }
  }
  return mejor.prueba;
}

// -> clases de cada tarjeta, por puesto
export function clasesMosaico(n) {
  const por = [2, 3, 4].map((cols) => [cols, disposicion(n, cols)]);
  return Array.from({ length: n }, (_, i) => por.map(([cols, d]) => CLASES[cols][d[i]]).join(" "));
}
