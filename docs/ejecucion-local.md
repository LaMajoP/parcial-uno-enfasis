# Cómo ejecutar el proyecto en local

Guía completa para levantar la plataforma, verla funcionando y saber qué hacer
cuando algo falla.

Si solo quieres los dos comandos: [Arranque rápido](#arranque-rápido).

---

## Requisitos

| Requisito | Cómo comprobarlo |
|---|---|
| Docker Desktop **corriendo** | `docker info` (si falla, abre la aplicación) |
| Docker Compose v2 | `docker compose version` |
| `make` | `make --version` (viene con macOS y Linux) |

**No hace falta instalar Python, Node, PostgreSQL ni nada más.** Todo corre
dentro de contenedores.

> **Apple Silicon (M1/M2/M3):** la imagen oficial de PostGIS solo se publica para
> amd64, así que Postgres corre emulado. Funciona bien, solo tarda algo más en
> arrancar la primera vez.

---

## Arranque rápido

```bash
cd "/Users/carlosdm/Desktop/Parcial Software"
make up
```

`make up` construye las imágenes, levanta Postgres, espera a que esté sano,
aplica las migraciones, carga los datos de demostración y arranca los cuatro
microservicios, el gateway y el frontend.

No se requiere ni se crea un archivo `.env`: la base de datos de Docker local
usa autenticación `trust` sin contraseña. Esa configuración es exclusiva de
desarrollo; producción obtiene su conexión desde AWS Secrets Manager. Si ya
tenías el volumen `pgdata` creado con la configuración anterior, Docker conserva
su autenticación original. Para reinicializar **solo los datos locales de
demostración** ejecuta `docker compose down -v` y luego `make up`.

**La primera vez tarda entre 5 y 10 minutos** porque descarga y construye seis
imágenes. Las siguientes son cuestión de segundos.

Cuando termine, comprueba que todo está en pie:

```bash
curl http://localhost:8080/health
```

Debe responder los cuatro servicios en `up`:

```json
{"success":true,"data":{"gateway":"up","status":"ok",
 "services":{"intake":"up","dispatch":"up","geospatial":"up","notification":"up"}}}
```

---

## Qué abrir en el navegador

| URL | Qué es |
|---|---|
| **http://localhost:3000/operator** | **Dashboard del operador** — empieza por aquí |
| http://localhost:3000 | Formulario del ciudadano |
| http://localhost:3000/track/`<id>` | Seguimiento de una emergencia |
| http://localhost:8080/health | Salud agregada de los 4 servicios |

Al arrancar, la base ya trae **20 recursos** (5 por ciudad, uno de cada tipo) y
**21 emergencias de demostración**, con 9 concentradas en un radio de ~800 m en
Cali para que el cálculo de zonas calientes dé un resultado visible.

---

## Recorrido de demostración

### 1. El dashboard del operador

Abre **http://localhost:3000/operator**.

En el mapa de Cali verás:

- Un **círculo grande de color** — la zona de concentración (*hotspot*): 8
  emergencias activas agrupadas. Haz clic para ver el detalle.
- **Puntos redondos de colores** — las emergencias, con el color de su prioridad:
  <br>🔴 P1 · 🟠 P2 · 🟡 P3 · 🔵 P4
- **Cuadrados verdes** — los recursos (ambulancias, bomberos, rescate…).

Debajo del mapa está la tabla de emergencias activas con filtros por ciudad,
prioridad y estado. En producción, Supabase Realtime invalida las consultas al
ocurrir un cambio y el tablero se actualiza sin polling. El contenedor local no
incluye credenciales públicas de Supabase, por lo que muestra el estado de
conexión Realtime como no disponible; las consultas REST locales siguen
funcionando a través del gateway.

### 2. Crear una emergencia

Ve a **http://localhost:3000** y rellena:

- **Tipo:** Rescate o emergencia médica
- **Ciudad:** Cali
- **Personas heridas:** 3
- Haz **clic en el mapa** para marcar dónde ocurre

Pulsa *Enviar reporte*. Te devuelve el identificador y la prioridad: **P1**,
calculada automáticamente por las reglas de clasificación.

> Los campos del formulario cambian según el tipo de emergencia que elijas. Cada
> tipo tiene los suyos y no se mezclan.

### 3. Ver el despacho automático

Vuelve al dashboard y espera unos segundos. Tu emergencia aparece en la tabla ya
con **Ambulancia Cali 01** en la columna *Recurso asignado* — **nadie la asignó a
mano**: el sistema buscó el recurso disponible más cercano del tipo adecuado y lo
despachó solo.

Desde la tabla puedes pulsar **Iniciar** y luego **Completar**. Verás cómo la
emergencia pasa a resuelta y la ambulancia vuelve a quedar libre.

### 4. Seguimiento como ciudadano

Tras enviar el reporte, el botón *Seguir esta emergencia* lleva a la vista de
seguimiento, que muestra en qué punto del proceso está.

### 5. Los eventos en vivo

Esto se ve mejor con dos ventanas. En una terminal:

```bash
curl -N http://localhost:8080/v1/notifications/stream
```

Deja eso corriendo y crea una emergencia en el navegador. Verás aparecer los
eventos uno a uno en la terminal, en el momento en que ocurren.

---

## Comandos disponibles

```bash
make help          # lista todos los comandos
```

| Comando | Qué hace |
|---|---|
| `make up` | Levanta todo (migraciones y datos incluidos) |
| `make down` | Para los contenedores **conservando** los datos |
| `make reset` | Borra la base y la recrea desde cero |
| `make logs` | Sigue los logs de todos los servicios |
| `make ps` | Estado de los contenedores |
| `make psql` | Abre una consola SQL contra la base |
| `make test` | Tests de los cuatro servicios (216 casos) |
| `make e2e` | Prueba de aceptación completa (reinicia la base antes) |
| `make migrate` | Reaplica solo las migraciones |
| `make seed` | Recarga los datos de demostración |

---

## Verificar que funciona de verdad

### Tests unitarios y de contrato

```bash
make test
```

216 casos repartidos entre los cuatro servicios: reglas de clasificación,
máquinas de estado, validación de payloads y formato de las respuestas. Tarda
alrededor de un minuto.

Para un solo servicio o un solo archivo:

```bash
docker compose run --rm --entrypoint pytest intake -q
docker compose run --rm --entrypoint pytest intake -q tests/test_triage.py
```

### Prueba de aceptación end-to-end

```bash
make e2e
```

Reproduce los once pasos de la demostración hablando **solo con el gateway**,
igual que hace el navegador: crea la emergencia, comprueba que se clasifica como
P1, que se asigna la ambulancia, que aparece en la zona y en el hotspot, que
quedan registradas las notificaciones y que el ciclo se cierra hasta resuelta.

Reinicia la base antes de ejecutarse, porque necesita el estado sembrado limpio:
uno de los pasos exige que se asigne *Ambulancia Cali 01* concretamente, y
fallaría —correctamente— si esa ambulancia ya estuviera ocupada.

### Mirar los datos directamente

```bash
make psql
```

```sql
-- Emergencias más recientes
SELECT type, priority, city, status FROM intake.emergencies
ORDER BY created_at DESC LIMIT 5;

-- Recursos de Cali y su estado
SELECT name, type, status FROM dispatch.resources WHERE city = 'CALI';

-- Quién atiende cada emergencia
SELECT e.type, e.priority, r.name, a.status
FROM dispatch.assignments a
JOIN dispatch.resources r ON r.id = a.resource_id
JOIN intake.emergencies e ON e.id = a.emergency_id;

-- Las notificaciones registradas
SELECT event_type, payload FROM notification.notifications
ORDER BY created_at DESC LIMIT 10;
```

Se sale con `\q`.

---

## Puertos

| Puerto | Qué escucha |
|---|---|
| **3000** | Frontend |
| **8080** | Gateway — **el único que usa el navegador** |
| 5432 | PostgreSQL |
| 8001–8004 | Los cuatro servicios, expuestos solo para depurar |

El frontend nunca habla con los puertos 8001–8004: todo pasa por el gateway. Por
eso migrar a la nube será cambiar una sola variable de entorno.

---

## Cuando algo falla

### `make up` falla nada más empezar

Docker Desktop no está corriendo. Ábrelo, espera a que el icono deje de animarse
y repite.

### «port is already allocated»

Otro programa ocupa uno de los puertos. Para ver cuál:

```bash
lsof -i :3000    # o :8080, :5432
```

Cierra ese programa o cambia el puerto directamente en `docker-compose.yml`.

### El navegador muestra una página en blanco

Mira si el frontend arrancó:

```bash
docker compose logs frontend | tail -20
```

### El dashboard dice que no puede contactar con el servidor

El gateway o algún servicio no está en pie:

```bash
curl http://localhost:8080/health
make ps
```

Si algún servicio aparece caído, sus logs dirán por qué:

```bash
docker compose logs intake | tail -30
```

### Una emergencia se queda sin recurso asignado

No es un fallo: significa que no quedaban recursos libres de esa ciudad. Es el
comportamiento correcto —la emergencia se registra igual y el operador puede
asignar a mano— pero si quieres volver al estado inicial:

```bash
make reset
```

### Los datos se ven raros tras muchas pruebas

```bash
make reset
```

Borra la base y la recrea con los datos de demostración limpios.

### Empezar completamente de cero

```bash
make down
docker compose down -v --rmi local    # borra también las imágenes construidas
make up
```

---

## Cómo está montado

```
Navegador (:3000)
      │
      ▼
  Gateway (:8080)  ── nginx, enruta por prefijo
      │
      ├── Intake (:8001)        recibe la emergencia y le calcula la prioridad
      ├── Dispatch (:8002)      busca recursos cercanos y los asigna
      ├── Geospatial (:8003)    consultas por zona y zonas calientes
      └── Notification (:8004)  registra y difunde los cambios de estado
      │
      ▼
PostgreSQL + PostGIS (:5432)
```

Cada servicio es independiente y tiene su propio esquema en la base de datos.
El detalle está en el [README](../README.md) y las decisiones de diseño en
[decisiones.md](decisiones.md).

---

## Diferencia intencional entre local y producción

- **Supabase Auth y Realtime no se configuran en local.** Docker Compose no
  versiona URL ni clave anónima de un proyecto Supabase. Por eso `/login` y el
  indicador Realtime requieren las tres variables públicas configuradas en
  Vercel para producir una sesión o suscripción real. El código del frontend ya
  integra Supabase Auth y Realtime; en producción los datos operativos siguen
  pasando por REST mediante API Gateway.
- **El dashboard no hace polling cada 5 segundos.** Cuando Supabase está
  configurado recibe eventos de `intake.emergencies` y
  `notification.notifications`, e invalida sus consultas REST.
