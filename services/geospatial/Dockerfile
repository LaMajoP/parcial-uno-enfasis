# ---- base ----
FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# ---- local: uvicorn ----
# Añade las dependencias de test para que `make test` corra dentro del contenedor.
# La imagen de Lambda no las lleva.
FROM base AS local
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests ./tests
COPY pytest.ini .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- lambda: preparado para ECR (NO se usa todavia) ----
FROM public.ecr.aws/lambda/python:3.12 AS lambda
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
COPY app ${LAMBDA_TASK_ROOT}/app
CMD ["app.main.handler"]
