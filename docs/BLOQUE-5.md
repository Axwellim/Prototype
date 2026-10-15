# Bloque 5 — Integración Laravel–Python mediante cola PostgreSQL

Implementado y verificado el 14 de octubre de 2026. No se implementa todavía la revisión dividida ni CER/WER.

## Resultado

Al cargar un documento, Laravel guarda el original privado y registra el documento y su tarea en una misma transacción PostgreSQL. La respuesta al navegador termina sin llamar al OCR. Un trabajador separado envía el archivo al servicio FastAPI local, valida el JSON y guarda todas las páginas y el estado completado en otra transacción. Si falla cualquier página, no se guardan resultados parciales de ese intento.

Estados: **pendiente → procesando → completado**, o **error**. El listado consulta los estados cada cuatro segundos sin recargar la página y muestra páginas, métodos, duración y un mensaje público de error. No se inventa porcentaje de avance: el servicio devuelve sus páginas juntas al terminar.

Se agregó un selector para OCR original, preprocesado o comparación. La opción elegida se conserva por documento; ambas variantes se almacenan cuando corresponde. La comparación mantiene original como texto principal, según el contrato del bloque 4.

## Ejecutar ahora en Windows

Usar tres terminales, todas desde `C:\xampp\htdocs\Prototype`. Detener antes las instancias anteriores para que carguen el código y la configuración actualizados.

Terminal 1 — Python:

```powershell
.\scripts\procesamiento.cmd
```

Debe escuchar en `127.0.0.1:8002` con un proceso Uvicorn.

Terminal 2 — Laravel:

```powershell
.\scripts\php.cmd .\laravel\artisan serve --host=127.0.0.1 --port=8000
```

Terminal 3 — un único trabajador:

```powershell
.\scripts\cola-documentos.cmd
```

Debe mostrar que atiende la cola PostgreSQL `ocr`. No usar `queue:listen`, ni iniciar un trabajador adicional. El lanzador llama al comando `documentos:trabajar`, que comprueba los tiempos y rechaza otra instancia mediante un bloqueo PostgreSQL. Para detener cada terminal, Ctrl+C; preferir terminar el documento actual antes de detener el trabajador.

Abrir http://127.0.0.1:8000 e ingresar con la cuenta local existente. Cargar un archivo y observar la transición a procesando y completado. Si el archivo es muy rápido, la consulta periódica puede pasar directamente de pendiente a completado. El documento completado del ejemplo de verificación se llama `prueba-integracion-bloque5.pdf`.

Para una comprobación de una sola tarea:

```powershell
.\scripts\cola-documentos.cmd --once
```

Para procesar lo pendiente y terminar:

```powershell
.\scripts\cola-documentos.cmd --stop-when-empty
```

Esos comandos atienden documentos reales de la cola de aplicación; no son pruebas aisladas. No ejecutar dos instancias a la vez.

## Documentos anteriores y reintentos

Los documentos cargados antes de este bloque se conservaron. Los que siguen pendientes y no tenían una tarea muestran **Procesar**; al pulsarlo se encolan una sola vez. No se encoló ni procesó automáticamente todo el archivo existente.

Si falla una tarea se muestra **Reintentar**. Corregir primero el servicio, idioma, contraseña compartida o archivo según el mensaje. El reintento crea una solicitud nueva; una tarea antigua no puede sobrescribir ese intento. Un documento ya completado no se reencola desde esta acción. Las referencias humanas existentes se conservan separadas y no se actualizan desde el Job.

No usar `queue:retry all` para reintentar documentos del módulo: la acción del listado controla estados y solicitudes correctamente. Los registros anteriores de `failed_jobs` se conservan como diagnóstico, también después de un reintento exitoso. No se eliminaron documentos ni resultados existentes.

## Archivos y cambios

| Archivo/componente | Responsabilidad |
| --- | --- |
| `app/Jobs/ProcesarDocumento.php` | Estado, exclusión, petición al servicio y persistencia por documento |
| `app/Services/ProcesadorDocumental.php` | Transporte HTTP local y validación de respuesta |
| `app/Services/ColaDocumental.php` | Encolado transaccional y reintento con bloqueo de fila |
| `app/Console/Commands/TrabajarDocumentos.php` | Trabajador único y comprobación de tiempos |
| `config/documentos.php` | Servicio y límites HTTP/Job |
| `config/queue.php` | Conexión de cola `documentos`, driver database y cola `ocr` |
| `2026_10_14_000002_add_document_processing_tracking.php` | Migración adicional sin reemplazar las existentes |
| `routes/web.php`, controlador, Blade y JS | Estado autenticado, modo OCR, Procesar y Reintentar |
| `tests/Feature/ColaDocumentalTest.php` | Pruebas de integración con transporte simulado |
| `scripts/cola-documentos.cmd` | Lanzador Windows |

La migración ya se ejecutó en la base de aplicación. Agrega solicitud UUID, modo, contador de intentos, fechas de encolado/inicio/fin, tiempo total, métodos y error al documento. Agrega `texto_digital` y `variantes_ocr` JSON a las extracciones. No modifica evaluaciones humanas ni recrea tablas existentes.

En otra instalación, después de configurar base y dependencias:

```powershell
.\scripts\php.cmd .\laravel\artisan migrate --no-interaction
.\scripts\php.cmd .\laravel\artisan config:clear
```

No ejecutar `migrate:fresh` sobre la base de aplicación.

## Configuración y claves

Se añadieron a `laravel/.env.example`:

```dotenv
PROCESSOR_URL=http://127.0.0.1:8002
PROCESSOR_API_TOKEN=
PROCESSOR_HTTP_TIMEOUT=170
PROCESSOR_JOB_TIMEOUT=210
PROCESSOR_MAX_RESPONSE_BYTES=20971520
DOCUMENTOS_RETRY_AFTER=370
```

En esta máquina la clave del `.env` privado de Laravel ya coincide con `procesamiento/.env`. No se copia a Blade, JavaScript, respuestas de estado ni payloads de Jobs. Si se cambia la clave, actualizar ambos `.env`, limpiar configuración si estaba cacheada y reiniciar servicio y trabajador. No guardar claves en Git.

Laravel solo acepta un URL de procesador HTTP con host literal `127.0.0.1`, sin credenciales, rutas, query ni fragmento. Se deshabilitan redirecciones y proxies en esa petición. El navegador no puede seleccionar el servidor ni enviar rutas. El trabajador verifica ruta privada, tamaño y SHA-256 antes de abrir el original y transmite sus bytes con el Content-Type registrado.

Se limita la conexión a cinco segundos, la solicitud HTTP a 170 segundos y la respuesta a 20 MB. También se comprueban páginas, numeración, tipos de extracción, variantes y texto completo antes de guardar. Un procesador desactualizado o con OCR deshabilitado que devuelva resultados incompletos se registra como error, sin marcar el documento como completado.

Jerarquía inicial: Python tiene 120 segundos para el subproceso, más hasta 30 segundos de recepción; HTTP Laravel 170; Job 210; reserva de cola 370. El comando exige `HTTP + 15 < Job` y `Job + 60 < retry_after`. Mantener además los límites Python compatibles. No reducir tiempos con tareas antiguas todavía reservadas; terminar o revisar la cola antes de cambiar la configuración.

## Concurrencia, fallos y recuperación

El comando de trabajo mantiene un bloqueo de sesión PostgreSQL para impedir dos trabajadores oficiales. Cada Job adquiere otro bloqueo PostgreSQL antes del trabajo pesado, incluso si se inicia por error con `queue:work`. FastAPI conserva su exclusión de una tarea. Si el bloqueo del Job está ocupado, la tarea se libera con una demora de 15 segundos. Hasta 50 reservas permiten esperar por contención, pero una excepción de procesamiento falla la tarea en el primer error mediante `maxExceptions=1`; el reintento ordinario es manual.

La solicitud UUID hace que tareas duplicadas o antiguas no repitan resultados ni cambien el estado de otro intento. La persistencia de páginas y estado completado es atómica. El Job no borra el original y no toca las evaluaciones OCR humanas.

En un cierre abrupto puede quedar estado procesando. PostgreSQL libera el bloqueo cuando se cierra la conexión. Con el trabajador nuevamente activo, la tarea reservada vuelve a estar disponible tras 370 segundos; si su ejecución anterior quedó procesando más allá del margen, se marca error y permite reintentar, en lugar de repetir OCR a ciegas. Sin trabajador activo no hay un proceso de recuperación automática; debe iniciarse.

PHP de Windows no dispone normalmente de pcntl, por lo que el timeout del trabajador no es un límite duro del proceso en ese entorno. Se usan además los plazos nativos HTTP y los límites del servicio Python. La cuota dura de RAM sigue pendiente; `--memory=256` recicla el trabajador PHP entre tareas si excede ese consumo y no limita la memoria de Python. Ubuntu deberá verificarse antes de producción y ejecutar un único proceso supervisado con `php artisan documentos:trabajar`, no varios workers.

## Pruebas ejecutadas

```powershell
# SQLite en memoria
Set-Location .\laravel
..\scripts\php.cmd vendor\bin\phpunit
Set-Location ..

# Base aislada imantag_documental_test, no la base de aplicación
.\scripts\php.cmd .\scripts\test-postgres.php
```

Resultado final: **25 pruebas y 141 aserciones aprobadas en SQLite y en PostgreSQL**. Comprobados también formato PHP con Pint, sintaxis JS y requisitos de plataforma Composer. Las 38 pruebas Python del bloque 4 no se repitieron porque este bloque no modifica Python.

La cobertura nueva comprueba encolado persistente sin HTTP durante la carga, rollback si falla el encolado, persistencia de variantes y capa digital, conservación de referencia humana y original, idempotencia, error del servicio, reintento sin duplicación, solicitud antigua sin efecto, respuesta inconsistente sin resultados parciales, archivo alterado, URL externo rechazado, documentos previos sin tarea, estado autenticado y recuperación de una ejecución interrumpida.

Además se ejecutó un recorrido real con Laravel en 8011, FastAPI en 8012 y la base PostgreSQL de aplicación:

1. Un segundo trabajador se rechazó mientras otra sesión mantenía el bloqueo PostgreSQL.
2. Se inició sesión por HTTP y se cargó un PDF mixto sintético; respondió 201 con estado pendiente y una tarea persistida, sin extracciones aún.
3. Se provocaron dos fallos de autenticación del procesador en trabajadores de prueba, sin cambiar las claves guardadas en los `.env`. Quedaron estado error y registros en `failed_jobs`.
4. Se reintentó desde la ruta HTTP protegida con CSRF, utilizando una solicitud nueva.
5. El trabajador con la clave correcta completó el documento: página 1 digital, página 2 OCR, dos variantes OCR conservadas, SHA-256 original intacto y estado HTTP completado. El servicio informó 5730 ms de procesamiento en esa muestra, no una promesa de rendimiento.

Se conservó el ejemplo `prueba-integracion-bloque5.pdf`, UUID `81c2fcec-513c-44b2-9de9-659a3d2b3476`, con sus resultados. Los fallos de prueba permanecen en `failed_jobs`. Los artefactos auxiliares están en `.tools/queue-smoke-document.json`; no contienen la clave del procesador.

El sandbox bloqueó escrituras de sesiones, pruebas, caché, registros y el formateador. El servidor HTTP de prueba y los controles finales se repitieron con autorización fuera del aislamiento; no se cambiaron permisos globales. Se detuvieron los servidores temporales 8011/8012 y los trabajadores de una sola tarea; no se detuvieron las instancias anteriores del usuario.

## Qué comprobar y qué falta

Con las tres terminales activas, cargar una imagen o un PDF, elegir modo y esperar el estado completado. Para una carga anterior pendiente, pulsar Procesar. Si no avanza, revisar primero la terminal del trabajador; si falla, comprobar el servicio Python, la coincidencia de claves y los idiomas de Tesseract antes de Reintentar.

La consulta de estado no presenta el texto extraído todavía: la revisión con original, navegación por páginas, transcripción humana y texto completo corresponde al bloque 6. CER/WER pertenecen al bloque 7. No se añadieron clasificación, embeddings ni modelos generativos.

Fuentes oficiales: [colas Laravel](https://laravel.com/docs/12.x/queues), [cliente HTTP Laravel](https://laravel.com/docs/12.x/http-client).
