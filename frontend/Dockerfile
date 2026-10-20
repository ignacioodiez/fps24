FROM node:22-alpine

WORKDIR /app

# Primero solo los package*.json, para aprovechar la caché de capas.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

# Servidor de desarrollo con recarga en caliente.
CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0"]
