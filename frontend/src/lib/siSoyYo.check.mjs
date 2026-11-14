// Self-check: un fallo de /me/perfil o /me con sesión nunca da el 404. Uso: docker compose exec web node src/lib/siSoyYo.check.mjs
import assert from "node:assert/strict";
import { vistaAdmin, vistaSiSoyYo } from "./siSoyYo.js";

const yo = { id: "uid-1" };
const FALLO = { usuario: null, error: true }; // lo que deja AuthProvider si /me/perfil falla dos veces
const v = (cambios) => vistaSiSoyYo({ usuario: yo, cargando: false, miPerfil: { usuario: "Ana" }, ruta: "/u/ana", esperar: true, ...cambios });

// El dueño: su vista en cualquier pestaña, también en las que siempre son 404 (sesiones, amigos)
for (const ruta of ["/u/ana", "/u/ANA/cines", "/u/ana/sesiones", "/u/ana/amigos"]) assert.equal(v({ ruta }), "mio", ruta);

// /me/perfil falló con sesión: aviso, nunca el 404 neutro, en el 404 de /u/<x> y sus subrutas
for (const ruta of ["/u/ana", "/u/ana/cines", "/u/ana/sesiones", "/u/ana/amigos"]) {
  assert.equal(v({ miPerfil: FALLO, ruta }), "aviso", ruta);
}
// Mientras se comprueba (o se reintenta): esqueleto
assert.equal(v({ miPerfil: undefined }), "esperar");
assert.equal(v({ cargando: true, usuario: null, miPerfil: null }), "esperar");
// Sin sesión: el 404 neutro de siempre (sin aviso, sin datos)
assert.equal(v({ usuario: null, miPerfil: null }), "ajeno");
// Con sesión y perfil leído, pero es otro: el 404 neutro
assert.equal(v({ ruta: "/u/otro" }), "ajeno");
// Sesión sin nombre (usuario null, sin error): el 404 neutro
assert.equal(v({ miPerfil: { usuario: null } }), "ajeno");
// En una vista pública (sin esperar) el fallo no oculta nada: children
assert.equal(v({ miPerfil: FALLO, esperar: false }), "ajeno");

// Admin: GET /me falló (null) no es "no eres admin"
const a = (cambios) => vistaAdmin({ disponible: true, usuario: yo, cargando: false, esAdmin: true, ...cambios });
assert.equal(a({}), "panel");
assert.equal(a({ esAdmin: null }), "aviso");
assert.equal(a({ esAdmin: undefined }), "esperar");
assert.equal(a({ cargando: true, esAdmin: false }), "esperar");
assert.equal(a({ esAdmin: false }), "404");
assert.equal(a({ usuario: null, esAdmin: false }), "404");
assert.equal(a({ disponible: false }), "404");
console.log("OK: siSoyYo.check");
