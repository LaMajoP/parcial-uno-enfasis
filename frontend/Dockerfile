FROM node:22-alpine
WORKDIR /app

# Las dependencias se instalan en una capa aparte: cambiar código fuente no
# obliga a reinstalar node_modules.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
