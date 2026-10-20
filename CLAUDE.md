# fps24

Agregador de cartelera de cines independientes de Madrid (fps24.es).

## Estructura
- `frontend/`: Next.js 16 + React 19 (JavaScript). Las páginas están en `frontend/src/app/`: `page.js` es la cartelera y `pelicula/[id]/page.js` el detalle. Lee la API con la variable `NEXT_PUBLIC_API_URL`.
- `backend/`: FastAPI (`main.py` y `app/`). Endpoints de lectura: `GET /pases` y `GET /pelicula/{id}`. Los scrapers (Playwright) están en `backend/app/scrapers/`.

## Entorno de prueba
- Se levanta con `docker compose up`: web en http://localhost:3000 y API en http://localhost:8000/docs.
- Usa una base de datos Postgres local, separada de producción. Los cambios de código se recargan solos.
- Para el lint: `docker compose exec web npm run lint`.

## Reglas
- Trabaja SOLO en la rama actual. Nunca cambies a `main`, ni hagas `git push` ni `git merge`.
- Por defecto edita solo dentro de `frontend/src`. No toques `backend/` ni `docker-compose.yml` sin pedírmelo.
- No cambies los endpoints ni el formato de la respuesta de la API.
- Nunca leas, muestres ni modifiques archivos `.env*`.
- No instales dependencias nuevas sin preguntarme antes.
- Mantén el estilo visual actual salvo que te pida cambiarlo.
- Antes de dar algo por terminado, ejecuta el lint y resume qué has cambiado.