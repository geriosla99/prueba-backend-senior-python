# Prueba Técnica — Backend

**Tiempo estimado:** 1 hora
**Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, pytest, Docker

---

## Contexto

Construye un servicio HTTP que evalúe solicitudes de crédito. Una solicitud incluye:

| Campo               | Tipo  | Descripción                                       |
|---------------------|-------|---------------------------------------------------|
| `amount`            | int   | Monto solicitado en COP                           |
| `monthly_income`    | int   | Ingresos mensuales en COP                         |
| `employment_months` | int   | Antigüedad laboral en meses                       |
| `external_score`    | int   | Score externo (0–1000)                            |
| `product`           | str   | Tipo de producto: `PHONE`, `TWIST` o `CARD`       |

## Reglas de evaluación

Existen tres políticas que se aplican según el tipo de producto:

| Producto | Política     | Regla                                                                 |
|----------|--------------|-----------------------------------------------------------------------|
| PHONE    | Conservadora | `score ≥ 700` AND `employment_months ≥ 12` AND `cuota ≤ 25% ingreso` |
| TWIST    | Estándar     | `score ≥ 600` AND `cuota ≤ 35% ingreso`                              |
| CARD     | Agresiva     | `score ≥ 550` OR (`score ≥ 500` AND `monthly_income ≥ 3,000,000`)    |

> Asume plazo fijo de 12 meses: `cuota = amount / 12`

Cada solicitud debe persistirse con su decisión (`APPROVED` o `REJECTED`) y las razones del rechazo cuando aplique.

## Endpoints requeridos

1. **`POST /applications`** — recibe la solicitud, la evalúa y la persiste. Retorna la decisión.
2. **`GET /applications/{id}`** — retorna una solicitud por ID.
3. **`GET /applications?status=APPROVED&product=TWIST`** — lista con filtros opcionales.

## Restricciones de diseño

- La selección de política según producto **no** debe ser un `if/elif` dentro del endpoint.
- El acceso a la base de datos **no** debe estar acoplado al endpoint.
- Cubre con tests al menos: una aprobación, un rechazo por cada política, y el flujo end-to-end del endpoint.

## Bonus (solo si te sobra tiempo)

`POST /applications/{id}/reevaluate` que vuelva a correr la evaluación con la política actual (útil si cambian umbrales).

---

## Setup

**Requisitos:** Docker Desktop instalado. Nada más.

### Levantar el servicio

```bash
docker compose up --build
```

- API: http://localhost:8000
- Docs interactivos: http://localhost:8000/docs

### Correr los tests

```bash
docker compose run --rm app pytest -v
```

### Estructura sugerida (puedes modificarla si lo justificas)

```
app/
├── main.py              # FastAPI app + routers
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── database.py          # engine + session
├── repositories/        # acceso a datos
├── services/            # orquestación
└── strategies/          # políticas de evaluación
tests/
```

## Entrega

Push a tu repo personal (público, o privado con acceso compartido) y envía el link.

¡Éxitos!

---

## Solución

### Supuestos

El enunciado deja varios puntos abiertos. Estas son las decisiones que tomé y por qué:

| # | Tema | Supuesto | Razón |
|---|------|----------|-------|
| 1 | Cuota | `cuota = amount / 12`, **sin intereses** ni seguros | Es lo que indica el enunciado; la tasa se modelaría como otro parámetro de la política |
| 2 | Límites | Todos los umbrales son **inclusivos** (`≥`, `≤`), p. ej. cuota = 25% exacto aprueba | Es la lectura literal de las reglas; está cubierto por tests de borde |
| 3 | Moneda | Montos en **COP enteros**, sin centavos | El COP en la práctica no usa centavos; los enteros evitan errores de redondeo |
| 4 | Cálculo | La regla de la cuota se evalúa con **aritmética entera**: `amount*100 ≤ ingreso*pct*12` | `amount/12` con floats puede fallar justo en el límite |
| 5 | Validación | `amount > 0`, `score` en 0–1000, ingresos y antigüedad `≥ 0`, producto ∈ {PHONE, TWIST, CARD}; campos extra rechazados | Un dato inválido no es una solicitud evaluable: responde **422 y no se persiste** |
| 6 | Ingreso 0 | Se permite `monthly_income = 0` | Es un caso real (independiente sin ingreso demostrable); PHONE y TWIST lo rechazan por la cuota, y CARD puede aprobar solo por score, como dice su regla |
| 7 | CARD | Ignora cuota y antigüedad | La regla no las menciona; la considero intencional ("agresiva") |
| 8 | Razones | Se devuelven **todas** las reglas incumplidas, no solo la primera | Es más útil para el cliente y el analista; en CARD se explican ambas ramas del OR |
| 9 | Decisión | Solo `APPROVED` / `REJECTED` (no hay "en revisión") | Así lo define el enunciado; un estado `MANUAL_REVIEW` sería una extensión natural |
| 10 | Reevaluación | **Sobrescribe** la decisión y actualiza `evaluated_at`; es idempotente y se puede llamar las veces que se quiera | Es lo más simple que cumple el bonus; ver propuesta de historial abajo |
| 11 | Trazabilidad | Se guarda el nombre de la política aplicada | Permite saber con qué regla se decidió |
| 12 | Listado | Orden por `id` ascendente, paginación `limit` (máx. 500, por defecto 100) / `offset` | Evita respuestas sin límite |
| 13 | Fechas | En UTC | Estándar para backends; SQLite no guarda la zona horaria, Postgres sí |
| 14 | Alcance | Sin autenticación ni idempotency key | Fuera del alcance de 1 hora; se listan como propuestas |

### Arquitectura

```
app/
├── main.py                 # App FastAPI: registra routers, crea tablas
├── domain.py               # Tipos de dominio puros (Product, Decision, CreditRequest, EvaluationResult)
├── models.py               # Modelo SQLAlchemy Application
├── schemas.py              # Contrato HTTP (Pydantic v2) con validaciones
├── database.py             # engine + sesión
├── dependencies.py         # Composition root: arma Service(Repository, PolicyRegistry)
├── routers/applications.py # Endpoints delgados: validan, delegan y traducen errores a HTTP
├── services/               # ApplicationService: orquesta evaluación + persistencia
├── repositories/
│   ├── base.py             # ApplicationRepository (clase abstracta / puerto)
│   └── application_repository.py  # SqlAlchemyApplicationRepository (adaptador)
└── strategies/
    ├── base.py             # EvaluationPolicy (clase abstracta, Template Method)
    ├── policies.py         # Conservative / Standard / Aggressive
    └── registry.py         # PolicyRegistry: Product -> política
```

Flujo: `router → service → PolicyRegistry → policy.evaluate() → repository → DB`

### Patrones y principios

- **Strategy.** Cada producto usa una política intercambiable. `PolicyRegistry` reemplaza el `if/elif`: agregar un producto es agregar una entrada, sin tocar ni el endpoint ni el servicio (Open/Closed).
- **Template Method.** `EvaluationPolicy` (ABC) define el algoritmo común: recolectar las razones y construir la decisión. Cada subclase solo implementa `rejection_reasons()`. Así todas deciden igual (sin razones → APPROVED) y no se puede crear una política incompleta, porque Python impide instanciar una subclase que no implemente el método abstracto.
- **Repository + Dependency Inversion.** El servicio depende de la abstracción `ApplicationRepository`, no de SQLAlchemy. En producción se inyecta `SqlAlchemyApplicationRepository`; en `tests/test_service.py` se usa un `InMemoryApplicationRepository` para probar el servicio sin base de datos.
- **Umbrales como parámetros.** Por ejemplo `ConservativePolicy(min_score=800)`. No hay números mágicos en la lógica, y esto es lo que le da sentido a `reevaluate`.
- **Dominio sin frameworks.** Las políticas reciben un `CreditRequest` (dataclass) y no conocen ni Pydantic ni SQLAlchemy.
- **Inyección de dependencias de FastAPI.** En los tests se sobreescriben `get_db` (SQLite en memoria, aislada por test) y `get_policy_registry` (para simular cambios de umbral).

### Endpoints

| Método | Ruta | Respuesta |
|--------|------|-----------|
| POST | `/applications` | `201` con la decisión · `422` si el input es inválido |
| GET | `/applications/{id}` | `200` · `404` |
| GET | `/applications?status=&product=&limit=&offset=` | `200` lista filtrada |
| POST | `/applications/{id}/reevaluate` (bonus) | `200` con la nueva decisión · `404` |

```bash
curl -X POST localhost:8000/applications -H 'content-type: application/json' \
  -d '{"amount":1200000,"monthly_income":2000000,"employment_months":24,"external_score":750,"product":"PHONE"}'
```

### Tests (32)

- `test_policies.py`: pruebas unitarias puras. Cubren aprobación y rechazo por cada política, los bordes de la cuota, las dos ramas del OR de CARD y el registro.
- `test_service.py`: prueba el servicio con el repositorio en memoria, incluida la reevaluación con umbrales nuevos.
- `test_applications_api.py`: flujo end-to-end por HTTP (crear → consultar, filtros, 404, 422, reevaluación).

### Propuestas (con más tiempo)

1. **Historial de evaluaciones**: una tabla `evaluations` (1 aplicación → N evaluaciones) en lugar de sobrescribir, para auditoría regulatoria.
2. **Versionado de políticas**: guardar `policy_version` y cargar los umbrales desde configuración o BD, para cambiarlos sin desplegar.
3. **Razones con código**: `{"code": "SCORE_TOO_LOW", "message": ...}` para que el frontend no dependa del texto.
4. **Reglas componibles (Specification)**: `MinScore`, `MaxInstallmentRatio`, `AnyOf(...)`, para armar políticas nuevas por configuración.
5. Alembic en lugar de `create_all`, Postgres, idempotency key en el POST, autenticación y logging estructurado.
