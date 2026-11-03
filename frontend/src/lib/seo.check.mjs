// Self-check de SEO contra la web levantada (docker compose up): sitemap, 404 reales, noindex y canonical.
// Uso: docker compose exec web node src/lib/seo.check.mjs   (BASE=http://... para otra URL)
import assert from "node:assert/strict";

const BASE = process.env.BASE || "http://localhost:3000";
const SITIO = "https://fps24.es";
const pedir = (ruta) => fetch(`${BASE}${ruta}`, { redirect: "manual" });
const noindex = (html) => /<meta name="robots" content="[^"]*noindex/.test(html);

// 1. Sitemap: solo URLs públicas, que respondan 200 y sean indexables
const xml = await (await pedir("/sitemap.xml")).text();
const urls = [...xml.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
assert.ok(urls.length > 6, "el sitemap debería traer cines y películas");
assert.ok(urls.some((u) => u.includes("/pelicula/")), "faltan películas en el sitemap");
for (const url of urls) {
  assert.ok(url.startsWith(SITIO), url);
  assert.ok(!/\/(u|perfil|admin|newsletter\/(baja|confirmada))(\/|$)/.test(url), `URL privada en el sitemap: ${url}`);
  const res = await pedir(url.slice(SITIO.length) || "/");
  assert.equal(res.status, 200, `${url} -> ${res.status}`);
  const html = await res.text();
  assert.ok(!noindex(html), `${url} está en el sitemap pero es noindex`);
  const canonical = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
  assert.equal(canonical?.replace(/\/$/, ""), url.replace(/\/$/, ""), `${url}: canonical ${canonical}`);
}

// 2. 404 reales (no 200 con un mensaje) y noindex en lo privado
for (const ruta of ["/pelicula/999999999", "/pelicula/abc", "/cines/no-existe", "/u/no-existe-xyz", "/u/no-existe-xyz/sesiones", "/u/no-existe-xyz/amigos", "/ruta-que-no-existe"]) {
  assert.equal((await pedir(ruta)).status, 404, ruta);
}
for (const ruta of ["/perfil", "/perfil/editar", "/admin", "/newsletter/baja", "/newsletter/confirmada", "/u/no-existe-xyz"]) {
  assert.ok(noindex(await (await pedir(ruta)).text()), `${ruta} debería ser noindex`);
}

// 3. robots.txt apunta al sitemap y no bloquea nada (lo privado se excluye con noindex, que Google tiene que poder leer)
const robots = await (await pedir("/robots.txt")).text();
assert.match(robots, /Sitemap: https:\/\/fps24\.es\/sitemap\.xml/);

// 4. Ficha de película: en el HTML del servidor, con un solo h1 y JSON-LD válido
const pelicula = urls.find((u) => u.includes("/pelicula/"));
const html = await (await pedir(pelicula.slice(SITIO.length))).text();
assert.equal(html.match(/<h1[\s>]/g)?.length, 1, "un solo h1");
const ld = JSON.parse(html.match(/<script type="application\/ld\+json">(.*?)<\/script>/s)[1]);
assert.equal(ld["@type"], "Movie");
assert.ok(ld.name);

console.log(`OK: SEO (${urls.length} URLs del sitemap con 200 e indexables, 404 reales, noindex en lo privado)`);
