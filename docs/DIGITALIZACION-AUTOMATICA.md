# Digitalización automática y PDF de entrega

Implementado y verificado el 14 de octubre de 2026, después de los siete bloques iniciales y antes de las pruebas institucionales. No incorpora clasificación por institución ni categorías de recibido/enviado; esas pruebas se harán con el usuario posteriormente.

## Comportamiento para el operador

La carga ya no muestra opciones técnicas de OCR. El operador selecciona un PDF, JPG/JPEG o PNG y pulsa **Cargar documento**. Las nuevas cargas quedan siempre en modo `automatico`, aunque se envíe un campo manual desde el navegador. Al terminar, el listado ofrece **PDF** y **Revisar**; la revisión incluye **Abrir PDF digitalizado** y **Ver texto completo**. La transcripción automática sigue siendo de solo lectura; las correcciones humanas se versionan por separado.

Cada nueva digitalización completada conserva:

- El original recibido, con su nombre, formato, tamaño y hash.
- Un PDF de entrega privado, con ruta, tamaño y SHA-256 propios registrados en PostgreSQL.
- La transcripción por página, el método, duración y observaciones de decisión en la base de datos.
- Las referencias humanas y CER/WER cuando se revisan y solicitan, como en el bloque 7.

El PDF se guarda como archivo privado y la base registra su ubicación y metadatos; no se almacena un BLOB binario dentro de PostgreSQL. La transcripción sí queda en sus tablas. El formato mostrado en la columna **Formato recibido** describe el original; el resultado de entrega es PDF para los tres formatos admitidos.

## Elección automática

Primero se analiza cada página PDF: una capa digital suficiente se extrae con PyMuPDF; las demás páginas se renderizan y pasan por OCR español. Un documento mixto puede utilizar ambos métodos sin pedir una elección al operador.

Para páginas que requieren OCR e imágenes, la política `automatico-imagen-v1` analiza una copia de hasta 1400 × 1400 píxeles después del tratamiento EXIF/transparencia y la orientación OSD existente. Mide contraste entre percentiles 1 y 99, diferencia respecto al filtro mediana y líneas con inclinación leve. Elige preprocesamiento si encuentra contraste inferior a 110 niveles, más de 8 % de píxeles con diferencia de ruido superior a 35 niveles, inclinación estimada de al menos 0,4° dentro de ±5°, o ancho inferior a 1400 píxeles. Activa solamente los filtros correspondientes: contraste local, mediana, corrección de inclinación y ampliación acotada, con escala de grises. No activa binarización automáticamente.

Si no detecta esas condiciones usa OCR sin filtros adicionales. Ejecuta un solo reconocimiento elegido, además de la estimación de orientación cuando corresponde. Registra la decisión y sus motivos en las observaciones de la página. Los modos manuales se conservan en la API/cliente de diagnóstico y en registros históricos; no se muestran como decisión de carga al operador.

Es una heurística reproducible de características de imagen, **no una garantía de escoger el texto con menos errores**. No usa confianza Tesseract como precisión, ni diccionarios que cambien nombres/números, ni modelos generativos. CER/WER frente a referencias humanas permitirá contrastar y ajustar esta política con documentos reales.

## PDF y transcripción

Un PDF recibido y validado se copia byte a byte como PDF de entrega: conserva sus páginas, dimensiones, capa digital y contenido existente. No se rasteriza para normalizarlo. JPG/PNG se convierten a una página PDF preservando proporción, aplicando EXIF y componiendo transparencia sobre blanco. El tamaño físico se calcula con el DPI configurado; no se fuerza A4 ni se recorta o estira el contenido.

El preprocesamiento afecta a una copia para OCR; no reemplaza visualmente el original ni el PDF de entrega con una imagen filtrada. La conversión entrega un PDF convencional: **no certifica PDF/A ni añade una capa OCR seleccionable al PDF escaneado**. La transcripción se almacena por separado en PostgreSQL y se puede consultar completa. Los PDF digitales conservan su capa original porque no se reescriben.

FastAPI admite `POST /procesar?modo=automatico&normalizar=true`: recibe los bytes del original y devuelve un ZIP con exactamente `resultado.json` y `documento.pdf`. El ZIP es únicamente transporte interno, no un archivo que deba manejar el operador. El endpoint sin `normalizar=true` mantiene la respuesta JSON para diagnóstico.

El trabajador Laravel valida los miembros y tamaños del paquete sin extraer rutas arbitrarias, valida la transcripción, escribe un PDF con UUID nuevo y guarda sus metadatos y todas las páginas en la misma transacción. Solo entonces marca el documento como completado. Si falta PDF o falla la persistencia, no publica una transcripción parcial y limpia solamente el PDF nuevo de ese intento. Si el proceso muere abruptamente entre la escritura y la transacción puede quedar un archivo huérfano, sin estado completado; no hay un recolector automático de esos archivos.

La migración `2026_10_14_000005_add_normalized_pdf.php` añade `ruta_pdf`, `hash_pdf`, `tamano_pdf` y `politica_digitalizacion`, y cambia el modo predeterminado a automático. No modifica el modo ni resultados de registros existentes. No se ha ejecutado una conversión masiva de documentos anteriores: las nuevas cargas reciben este flujo, y las tareas antiguas que se procesen con el código nuevo también obtendrán PDF respetando su modo registrado. Los documentos ya completados conservan su resultado anterior.

## Configuración y arranque

La migración ya fue aplicada en este equipo. Reiniciar Python, Laravel y el trabajador para cargar el código actualizado, terminando primero el trabajo que esté en ejecución:

```powershell
# Una terminal por comando, desde la raíz
.\scripts\procesamiento.cmd
.\scripts\php.cmd .\laravel\artisan serve --host=127.0.0.1 --port=8000
.\scripts\cola-documentos.cmd
```

Para otra instalación existente, ejecutar primero `scripts\php.cmd laravel\artisan migrate --no-interaction` y `scripts\php.cmd laravel\artisan config:clear`.

Nuevos límites: `PROCESSOR_MAX_PDF_BYTES=41943040` en Python, `DOCUMENTOS_MAX_PDF_BYTES=41943040` y `PROCESSOR_MAX_RESPONSE_BYTES=62914560` en Laravel. En esta instalación ya se amplió el límite de respuesta Laravel para transportar PDF y JSON juntos. El tamaño de entrada sigue siendo 20 MB. Los límites por página, imagen y tiempo se mantienen; la generación y validación del PDF ocurren dentro del proceso aislado con el mismo timeout global. No se añadió una cuota dura de RAM.

## Verificación

Resultado de la regresión completa: **53 pruebas Python aprobadas** y **47 pruebas Laravel, 263 aserciones, aprobadas en PostgreSQL aislado**. Pint, sintaxis JavaScript y compilación Blade correctos. El cliente de pruebas Python mantiene el aviso de deprecación httpx ya documentado; no hay pruebas omitidas en Windows.

Se probaron decisiones controladas para imagen limpia, contraste bajo, ruido y resolución pequeña; conversión real PNG y JPEG preservando el original y proporción; PDF de varias páginas sin rasterización ni cambios de bytes; y paquetes HTTP reales para PDF digital, PDF mixto, PNG y JPEG con OCR Tesseract real donde corresponde. Cada PDF se abrió con PyMuPDF y se comprobó que sus páginas coincidieran con la transcripción recibida.

Laravel verifica persistencia conjunta, hash, autenticación, acceso parcial HTTP 206, rechazo de rutas ajenas/archivo alterado, PDF ausente, límite de salida y rollback de páginas con limpieza del único PDF nuevo. Se ejecutó la regresión de métricas y referencias humanas.

Las muestras son sintéticas. Aún no se comparó la heurística con una selección humana sobre documentos institucionales ni se afirma una mejora cuantificada del OCR. La validación de recibido/enviado por institución sigue pendiente.

Para las comprobaciones Chrome se usa `scripts/test-automatic-browser.cjs`, Laravel temporal en 8011 con `PROCESSOR_URL=http://127.0.0.1:8012` y `DOCUMENTOS_QUEUE=pruebas-automatico`, y Python temporal en 8012. La cola de ejecución normal sigue siendo `ocr`; se hizo configurable su nombre para aislar la prueba del trabajador ya abierto por el usuario. El ejecutor privado `.tools/process-automatic-browser.php` solo procesa las muestras creadas por este script y comprueba sus hashes y transcripción. Invoca el manejador del Job para esos registros concretos, sin consumir documentos ajenos. No es una prueba nueva del bucle del trabajador; ese bucle se verificó en el bloque 5.

La ejecución aislada en Chrome pasó para **PDF digital de dos páginas, PNG y JPG**: carga real sin selector, PDF servido con autenticación, transcripción visible y hashes de original/resultado correctos. No hubo errores JavaScript. Los artefactos están en `.tools/automatico-browser-report.json`, `.tools/automatico-listado.png`, `.tools/automatico-revision.png` y las fichas JSON por UUID. Se conservaron las tres muestras y sus resultados en la base de aplicación, identificadas con el prefijo `prueba-automatico-`.

La primera muestra de navegador se encoló antes de aislar la cola y fue atendida por el trabajador anterior del usuario, conectado a un servicio que aún no aceptaba `automatico`; quedó registrada como error de prueba. No se borró el registro ni se detuvieron los procesos del usuario. Esto confirma la necesidad de reiniciar Python y el trabajador tras la actualización, no una medición de documentos institucionales.

Referencia técnica: [PyMuPDF, manejo de imágenes y páginas PDF](https://pymupdf.readthedocs.io/en/latest/recipes-images.html).
