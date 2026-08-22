FROM nginx:1.27

# njs es lo que permite construir el /health agregado: nginx por sí solo no sabe
# consultar cuatro upstreams y combinar sus respuestas. El paquete viene del
# repositorio oficial de nginx, ya configurado en esta imagen, así que la versión
# del módulo encaja exactamente con la de nginx.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx-module-njs \
    && rm -rf /var/lib/apt/lists/*

COPY nginx.conf /etc/nginx/nginx.conf
COPY health.js /etc/nginx/njs/health.js

EXPOSE 8080

# No se valida la config con `nginx -t` durante el build: nginx resuelve los
# nombres de los upstreams al parsear el archivo, y en tiempo de build los
# contenedores de los servicios todavía no existen. Por el mismo motivo el
# gateway depende de los cuatro servicios en docker-compose.yml.
