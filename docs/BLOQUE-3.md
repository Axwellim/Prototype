# Bloque 3 — FastAPI y extracción digital con PyMuPDF

Implementado el 14 de octubre de 2026. Alcance: servicio independiente para PDF digitales; no incorpora OCR ni integración con la cola Laravel.

## Entregables

```text
config/php/                 Configuración PHP existente, sin cambios en este bloque
procesamiento/
  app/
    config.py               Configuración validada y lectura del .env local
    schemas.py              Respuestas y coherencia de páginas con Pydantic
    extraction.py           Lectura, validación y extracción digital por página
    worker.py               Proceso separado para cada documento
    main.py                 API local, autenticación, límites y concurrencia
  tests/test_service.py     Pruebas con documentos sintéticos
  .env.example              Ejemplo sin secretos
  .env                      Clave local, excluida de Git
  requirements.in           Dependencias directas de ejecución
  requirements.txt          Versiones de ejecución fijadas
  requirements-dev.in       Dependencias de pruebas
  requirements-dev.txt      Versiones de pruebas fijadas
  probar_pdf.py             Cliente HTTP local de comprobación
  pytest.ini
scripts/procesamiento.cmd   Arranque Windows en 127.0.0.1:8002
.venv/                      Entorno aislado, excluido de Git
.tools/python312/           Python local 3.12.10, excluido de Git
.tools/ejemplo-digital-bloque3.pdf
.tools/resultado-digital-bloque3.json
```

Python disponible en PATH era un acceso de Windows sin intérprete funcional. Se descargó Python 3.12.10 desde python.org y se verificó su firma Authenticode, correspondiente a Python Software Foundation. Se instaló en `.tools/python312` para este usuario, sin añadirlo al PATH, sin launcher ni asociaciones de archivos. El instalador puede registrar la instalación en la cuenta Windows; los ejecutables están dentro del proyecto. No se instaló Tesseract, Ollama ni modelos generativos.

Versiones instaladas: FastAPI 0.143.1, PyMuPDF 1.28.2, Pydantic 2.14.1 y Uvicorn 0.54.0. `pip check` no detectó dependencias incompatibles. Los requirements incluyen las dependencias transitivas resueltas en este entorno. Las pruebas usan pytest y httpx separados de las dependencias de ejecución.

## Ejecución en Windows

En una terminal, desde `C:\xampp\htdocs\Prototype`:

```powershell
.\scripts\procesamiento.cmd
```

Debe indicar `Uvicorn running on http://127.0.0.1:8002`. Detener con Ctrl+C. No necesita activar PowerShell ni cambiar su política de scripts. Se utiliza un único proceso Uvicorn, sin recarga automática; el procesamiento pesado se limita a un documento a la vez. No iniciar varias instancias del servicio: el bloqueo de concurrencia es por instancia.

En otra terminal, comprobar un documento propio:

```powershell
.\.venv\Scripts\python.exe .\procesamiento\probar_pdf.py "C:\ruta\documento.pdf" --salida .\.tools\revision-manual.json
```

El cliente no sobrescribe archivos de salida existentes: usar otro nombre en una segunda revisión. Si no se inició el servicio, informa que no puede conectarse. Si el PDF es rechazado, informa el estado HTTP y el motivo. No imprime la clave del servicio.

Ya se generaron y comprobaron estos archivos de ejemplo:

- `.tools/ejemplo-digital-bloque3.pdf`: PDF digital sintético de dos páginas.
- `.tools/resultado-digital-bloque3.json`: respuesta obtenida mediante HTTP real, validada con Pydantic.

Comparar el original y el JSON, especialmente números de oficio, fechas, acentos, nombres y separación de páginas. El JSON contiene texto por página y `texto_completo` separado por form feed (`\f`). La extracción conserva mayúsculas, signos y saltos de línea entregados por PyMuPDF; no corrige ni normaliza nombres o números.

Laravel sigue funcionando con su comando anterior en el puerto 8000. Los documentos cargados desde Laravel **permanecen pendientes**: este bloque no conecta el navegador al procesador ni guarda extracciones en PostgreSQL. La integración Laravel–Python y los Jobs corresponden al bloque 5. Para revisar ahora un archivo, utilizar el cliente local anterior; no exponer la clave Python al navegador.

## Instalación reproducible en otro Windows

Instalar Python 3.12 de 64 bits desde https://www.python.org/downloads/windows/ y verificar el intérprete real. Desde la raíz del proyecto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements.txt
# Solo para ejecutar pruebas:
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements-dev.txt
Copy-Item .\procesamiento\.env.example .\procesamiento\.env
```

Generar una clave con `python -c "import secrets; print(secrets.token_hex(32))"` utilizando el intérprete disponible, y colocarla en `PROCESSOR_API_TOKEN` dentro de `procesamiento/.env`. No compartirla ni publicarla. En esta máquina ya se generó una clave aleatoria de 64 caracteres y se guardó localmente; no hay que reemplazarla para ejecutar el servicio. Nunca sobrescribir un `.env` existente al repetir la instalación.

Para recrear el entorno en esta máquina puede usarse `.tools\python312\python.exe` en lugar de `py -3.12`. Los entornos virtuales no son portables: recrearlos tras mover el proyecto a otro equipo o sistema operativo.

## Contrato HTTP

- `GET /salud`: requiere la clave y responde con disponibilidad del servicio y fase actual. No garantiza que un documento arbitrario pueda procesarse.
- `POST /procesar`: requiere `X-Processor-Token: <clave local>` y `Content-Type: application/pdf`. El cuerpo son los bytes del PDF. No recibe JSON, rutas, nombres de archivo ni formularios multipart. Este contrato permite que el futuro Job envíe un stream del archivo privado sin revelar rutas.
- Solo acepta clientes loopback y el lanzador escucha únicamente en `127.0.0.1`.
- No hay CORS habilitado ni documentación interactiva pública. El navegador usa Laravel; el cliente interno usa la clave compartida.

Respuesta de éxito: `estado`, `numero_paginas`, `duracion_total_ms`, `paginas` y `texto_completo`. Cada página incluye `numero`, `metodo`, `texto`, `duracion_ms` y `observaciones`.

`estado=completado` significa que todas las páginas tienen texto digital suficiente según los umbrales configurados, no que el texto sea perfecto. Si alguna página necesita OCR se devuelve `estado=requiere_ocr`, y su método es `requiere_ocr`. Se conserva cualquier texto digital parcial para inspección, sin inventar texto de imágenes. Estos valores son del contrato del servicio en este bloque; no cambian los estados persistentes Laravel (`pendiente`, `procesando`, `completado`, `error`).

Errores: 401 sin clave válida, 403 para origen no local, 415 tipo de contenido incorrecto, 413 tamaño excedido, 422 PDF vacío/inválido/corrupto/cifrado o límites de contenido/páginas, 503 ocupado o almacenamiento temporal no disponible, 504 tiempo de extracción excedido y 408 recepción demasiado lenta. Un fallo inesperado del proceso devuelve 500 sin detalles internos.

## Detección por página y configuración

Valores de `procesamiento/.env.example` y sus valores por defecto:

| Variable | Valor | Función |
| --- | --- | --- |
| PROCESSOR_MAX_BYTES | 20971520 | Tamaño del cuerpo, 20 MB |
| PROCESSOR_MAX_PAGES | 100 | Máximo de páginas |
| PROCESSOR_TIMEOUT_SECONDS | 120 | Límite del subproceso de extracción |
| PROCESSOR_MAX_TEXT_CHARS | 1000000 | Máximo de caracteres extraídos en total |
| PROCESSOR_MIN_CHARS | 80 | Mínimo de caracteres sin espacios por página |
| PROCESSOR_MIN_WORDS | 12 | Mínimo de palabras por página |
| PROCESSOR_MIN_PRINTABLE_RATIO | 0.95 | Proporción mínima de caracteres imprimibles |
| PROCESSOR_MIN_ALNUM_RATIO | 0.55 | Proporción mínima de letras/números |
| PROCESSOR_MAX_IMAGE_COVERAGE | 0.65 | A partir de esta fracción de área de imágenes se requiere revisión OCR |

Reiniciar el servicio después de cambiar configuración. El arranque falla si falta la clave o si los valores están fuera de los rangos admitidos. El tamaño se comprueba tanto con Content-Length como mientras se recibe el cuerpo, incluso sin longitud anunciada. La recepción tiene un plazo de 30 segundos, separado del límite de extracción.

Una página se marca como digital cuando cumple todas las condiciones. Unos pocos caracteres o un encabezado no bastan. Una imagen que ocupa gran parte de la página obliga a revisión OCR incluso si existe suficiente texto en otra zona. Se guarda la razón de cada decisión. Los umbrales son heurísticos y ajustables mediante documentos reales.

Limitaciones de detección: una invitación digital con fondo gráfico puede requerir OCR innecesariamente; una página legítima muy corta también. Una capa OCR anterior extensa pero incorrecta puede pasar los umbrales. La cobertura suma áreas recortadas y limita el total a 1, sin calcular la unión geométrica exacta; las imágenes superpuestas pueden sobreestimar cobertura. No se interpreta texto dibujado como vectores ni se garantiza el orden en tablas/columnas complejas. No hay porcentajes de precisión ni confianza OCR.

## Protección y recursos

Cada petición usa un directorio temporal generado por el servidor y una copia del PDF; no modifica ni elimina originales de Laravel. El directorio se limpia tras éxito o error controlado. El parser trabaja en un subproceso, con un plazo que permite terminarlo incluso si está bloqueado en código nativo. Al desconectarse el cliente durante la extracción se espera al hijo antes de liberar el bloqueo y limpiar sus archivos.

Se rechazan PDF con contraseña, reparados automáticamente o sin páginas. PyMuPDF valida su estructura y carga cada página. No se ejecuta JavaScript ni se renderizan imágenes. Los errores conocidos se devuelven en español y se registran por código; se registran páginas, duración y estado sin texto ni credenciales.

Los límites de entrada, páginas, salida, tiempo y concurrencia reducen consumo, pero **no hay todavía un límite duro de RAM impuesto por el sistema operativo**. Un PDF comprimido adversario podría consumir mucha memoria antes de alcanzar un límite de texto. La configuración de aislamiento/cuotas del servidor de producción sigue pendiente. Una terminación forzada de todo el servicio o del sistema también puede dejar un directorio temporal huérfano; no se implementó limpieza global automática que pudiera afectar a otros archivos.

## Pruebas realizadas

Resultado final: **21 pruebas aprobadas**, con un aviso de deprecación de la dependencia de pruebas, y ninguna dependencia incompatible según pip check.

Desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -c .\procesamiento\pytest.ini .\procesamiento\tests -q
.\.venv\Scripts\python.exe -m pip check
```

La suite verifica PDF digital español de una página y varias páginas, conservación de números/fechas/nombres, separación de páginas, páginas vacías y con texto escaso, imagen dominante con texto digital, archivos corruptos/reparados/cifrados y formatos incorrectos, límites de tamaño con cabecera y por stream, páginas y texto, autenticación, origen local, rechazo de rutas JSON, original intacto, umbrales configurables, respuesta ante timeout/fallo del hijo, fallo de temporales, concurrencia, limpieza y consistencia del esquema Pydantic.

La prueba de timeout fuerza la excepción de subprocess para verificar su traducción a HTTP 504; no es una medición de rendimiento de un PDF real lento. Se ejecutaron también compilación Python y `pip check`.

Se ejecutó una comprobación HTTP real en Uvicorn: envío de PDF sintético de dos páginas, respuesta completada, validación del JSON y rechazo 401 sin clave. Se guardaron los artefactos de ejemplo indicados arriba. No se utilizaron documentos institucionales.

La dependencia Starlette emite un aviso de futura sustitución de httpx por httpx2 en su cliente de pruebas. La suite actual funciona; no se ocultó el aviso ni se añadió una dependencia de ejecución para eliminarlo.

## Pendientes

OCR real de PDF escaneados, mixtos e imágenes; Tesseract spa; preprocesamiento; integración por cola; revisión en Blade; CER/WER; pruebas con documentos institucionales y evaluación humana. No se afirma haber probado reconocimiento OCR de los diez escenarios finales. No se alteraron las rutas, los archivos originales ni los registros existentes de Laravel.

## Ubuntu (preparado, sin ejecutar en esta sesión)

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r procesamiento/requirements.txt
# Crear procesamiento/.env con clave local antes de iniciar.
cd procesamiento
../.venv/bin/python -m uvicorn app.main:app_factory --factory --host 127.0.0.1 --port 8002 --workers 1 --no-access-log
```

Usar una versión de Python mantenida compatible con las dependencias. Validar instalación de wheels, permisos del usuario de servicio, temporales y límites de recursos en Ubuntu antes del despliegue. No se ha probado Ubuntu.

Fuentes oficiales: [extracción de texto PyMuPDF](https://pymupdf.readthedocs.io/en/latest/recipes-text.html), [FastAPI](https://fastapi.tiangolo.com/), [Python para Windows](https://www.python.org/downloads/windows/).
