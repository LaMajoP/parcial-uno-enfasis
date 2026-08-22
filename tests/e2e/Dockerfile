# Corre la prueba de aceptación desde dentro de la red de compose, para no
# depender de que la máquina anfitriona tenga Python ni httpx instalados.
FROM python:3.12-slim
WORKDIR /e2e
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENTRYPOINT ["pytest"]
