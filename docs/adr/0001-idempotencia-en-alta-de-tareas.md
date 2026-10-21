# ADR 0001 — Idempotencia en el alta de tareas

- **Estado:** Aceptada
- **Fecha:** 2026-10-21
- **Ámbito:** `POST /tasks` (recurso `tasks`, versión 0.2.0)
- **Referencias:** [`docs/feature-tasks.md`](../feature-tasks.md) (decisiones 8–11, A2 y A5;
  criterios CA-26 a CA-33); commits `a5bcc57` (idempotencia) y `90a09e7` (atomicidad ante
  peticiones simultáneas).

## Contexto

El objetivo del sprint es **reducir las pérdidas de trabajo no registrado y mejorar la
trazabilidad** de las tareas del equipo de operaciones. Para eso, cada trabajo real tiene que
quedar registrado **exactamente una vez**: si no se registra, se pierde; si se registra dos
veces, ya no se sabe cuál es la buena, quién la tiene asignada ni si se hizo.

Había dos situaciones que podían duplicar tareas y romper esa trazabilidad:

- **Reintentos del cliente ante timeouts o fallos de red.** El cliente no sabe si su `POST`
  llegó al servidor. La respuesta pudo perderse después de crear la tarea, así que reintenta y
  crea una segunda.
- **Dobles envíos del equipo de soporte operativo.** Un doble clic, reenviar un formulario o
  repetir una operación manual dan lugar a altas idénticas.

Restricciones técnicas de partida:

- **Sin autenticación:** no hay usuario autenticado al que atar una clave.
- **Almacén en memoria:** se pierde al reiniciar la app.
- **Rutas síncronas:** FastAPI ejecuta las rutas `def` en un threadpool, así que puede haber
  dos altas en paralelo.
- **Clientes actuales:** algunos no envían ninguna cabecera especial, y su contrato no puede
  romperse.

## Decisión

El alta de tareas admite **idempotencia opcional** con la cabecera `Idempotency-Key`. La
implementación vive en `tasks/service.py` (`create_task`) y en `tasks/repository.py`.

1. **Cabecera opcional.**
   - Sin `Idempotency-Key`, el alta se comporta como antes: dos `POST` iguales crean dos tareas
     (CA-33).
   - La clave tiene de 1 a 64 caracteres, contados en caracteres y no en bytes.
   - No se recorta y distingue mayúsculas. Si no cumple la forma, la petición da 422.
2. **Huella del cuerpo normalizado.**
   - La huella es un SHA-256 del cuerpo ya validado, con `title` recortado y los valores por
     defecto aplicados, serializado con las claves ordenadas.
   - Solo entran `title`, `description`, `priority`, `due_date` y `assignee_id` (A5).
   - Así, `{"title": " Revisar "}` y `{"title": "Revisar", "priority": 3}` son el mismo cuerpo
     (decisión 8).
3. **Respuesta ante una clave repetida.**
   - Con la misma huella, devuelve **200** con la tarea original, con el mismo `id` y el mismo
     `created_at`, y no crea otra (decisión 11).
   - Con otra huella, devuelve **409** con `errors.already_exists("clave de idempotencia",
     <clave>)`, del catálogo existente.
4. **La clave solo se guarda tras un 201.**
   - Si la primera petición da 422 o 404, la clave no queda reservada: el siguiente intento
     válido crea la tarea (decisión 9).
5. **Orden de evaluación:**
   1. forma del cuerpo y de la cabecera (422);
   2. fecha límite pasada (422; también en una repetición, según A2);
   3. clave de idempotencia (200 / 409);
   4. responsable (404);
   5. creación (201).
6. **Alcance y duración.** La clave es global, porque no hay usuarios, y no caduca. Se guarda
   en memoria junto a su huella y su tarea, y `reset()` la limpia (decisión 10).
7. **Atomicidad.** Un `threading.Lock` en el service cubre todo el tramo: buscar la clave,
   comprobar el responsable, crear la tarea y guardar la clave. Así, dos peticiones
   simultáneas con la misma clave no crean dos tareas.

## Alternativas consideradas

| Alternativa | Por qué se descartó |
|-------------|---------------------|
| **No hacer nada.** El cliente o el equipo de soporte deduplican a mano. | No resuelve el problema: los duplicados llegan a la API y la trazabilidad depende de una limpieza manual posterior. |
| **Deduplicar por clave natural** (`title` + `assignee_id` + `due_date`) sin cabecera. | Da falsos positivos: dos tareas legítimas pueden coincidir en título, responsable y fecha. Además, rechazarlas sería perder trabajo real, justo lo contrario del objetivo. |
| **`Idempotency-Key` obligatoria.** | Rompe a los clientes actuales que no la envían. Con la cabecera opcional, la protección es gradual sin cambiar el contrato. |
| **Repetición con otro cuerpo → 200 con la tarea original**, sin 409. | Oculta errores del cliente, que creería haber registrado datos distintos de los guardados. El 409 deja el conflicto a la vista. |
| **Guardar la clave también cuando la petición falla** (reservarla al recibirla). | Una primera petición con un responsable inexistente o un título inválido bloquearía la clave. El reintento corregido no podría crear la tarea y se perdería el trabajo. |
| **`PUT /tasks/{id}` con un id generado por el cliente.** | Cambia el contrato (el `id` lo asigna el servidor y empieza en 1) y añade un verbo que queda fuera del alcance del sprint. |
| **Claves con caducidad (TTL) o ligadas al usuario.** | Requieren una política de expiración y autenticación, y las dos quedan fuera del alcance del sprint. Se dejan como trabajo futuro. |
| **Atomicidad con rutas `async def`**, sin lock. | Depende de que nunca haya un `await` entre comprobar y guardar, lo que es frágil ante cambios. El lock es explícito y funciona con las rutas síncronas actuales. |

## Consecuencias

**Positivas**

- Un reintento por timeout o fallo de red, o un doble envío del equipo de soporte, ya no
  duplica tareas: cada trabajo queda registrado una sola vez y se mantiene la trazabilidad.
- El cliente que reintenta recibe la misma tarea que se creó (200), así que puede reconciliar
  su estado sin consultas adicionales.
- El contrato sigue siendo compatible: los clientes sin la cabecera funcionan igual que antes.
- El conflicto de clave usa el catálogo de errores existente, sin funciones nuevas en
  `core/errors.py`.

**Negativas y riesgos asumidos**

- **Memoria sin límite.** Las claves no caducan, así que el almacén crece con cada alta que
  lleva clave.
- **Sin persistencia.** Al reiniciar la app se pierden las tareas y las claves. Un reintento
  que llegue después de un reinicio crea la tarea de nuevo.
- **Claves globales.** Dos clientes distintos que usen la misma clave chocan, y el segundo
  recibe 200 o 409 en lugar de crear su tarea. Corresponde al cliente generar claves únicas,
  por ejemplo UUID.
- **Altas serializadas.** El lock serializa las altas. Con el volumen actual no importa, pero
  limita el rendimiento si crece mucho.
- **Decodificación de la cabecera.** Para contar la longitud en caracteres, la cabecera se
  vuelve a decodificar como UTF-8, porque Starlette la entrega como latin-1. Si los bytes no
  son UTF-8 válido, se usa el valor tal cual.

**Trabajo futuro**

- Caducidad (TTL) de las claves y un límite de tamaño del almacén.
- Claves ligadas al usuario cuando exista autenticación.
- Almacenar tareas y claves en una base de datos, con una restricción de unicidad sobre la
  clave en lugar del lock en memoria.
