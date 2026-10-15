# Bloque 4 — OCR local en español y comparación de preprocesamiento

Implementado y verificado el 14 de octubre de 2026. Se conserva la extracción digital del bloque 3 y se añade OCR. La integración con Laravel/Jobs sigue reservada al bloque 5.

## Qué se implementó

- Tesseract 5.5.3.20260724 en `.tools/tesseract`, con `spa`, `osd` y `eng` comprobados mediante `--list-langs`. Se utiliza **spa** para reconocer documentos; osd se usa únicamente para orientación.
- Pillow, OpenCV headless y NumPy, con versiones fijadas en los requirements existentes. Python llama directamente al ejecutable Tesseract mediante argumentos separados, sin shell ni rutas procedentes del cliente; no hace falta pytesseract.
- PDF evaluado página por página. Las páginas con texto digital suficiente conservan PyMuPDF; las restantes se renderizan y pasan por Tesseract. El texto digital parcial se conserva en `texto_digital` para auditoría, sin concatenarlo al texto OCR y duplicarlo.
- JPG/JPEG y PNG: validación del formato real con Pillow, decodificación, comprobación de píxeles, corrección EXIF en copia y OCR. Se rechazan imágenes animadas para no omitir fotogramas silenciosamente.
- Orientación OSD opcional, aplicada solo cuando hay una estimación con suficiente confianza. Si no puede determinarse se continúa con una observación. Esa confianza sirve para orientar, no es una medida de precisión del texto.
- Preprocesamiento opcional y registrado por variante: escala de grises, contraste moderado CLAHE, corrección de inclinación pequeña, reducción de ruido mediana, binarización Otsu y ampliación acotada. Se trabaja siempre sobre copias; nunca se guardan cambios en los originales.
- Tres modos: `original`, `preprocesado` y `comparar`. El último devuelve ambos textos y sus tiempos. **En comparación, el texto principal es el OCR original**: no se elige automáticamente un ganador ni se inventa precisión.
- Una tarea pesada a la vez. Tesseract y OpenCV usan un hilo cada uno. Timeout por invocación Tesseract y timeout global del documento; en timeout global se termina el árbol de procesos antes de limpiar temporales. Los temporales OCR están dentro del directorio temporal del documento.

## Cómo ejecutarlo ahora

Si ya tienes Python escuchando en 8002, detenerlo con Ctrl+C y reiniciarlo desde la raíz del proyecto:

```powershell
.\scripts\procesamiento.cmd
```

En otra terminal:

```powershell
# Comparar las dos variantes de una imagen
.\.venv\Scripts\python.exe .\procesamiento\probar_pdf.py .\.tools\ocr-bloque4\imagen.png --modo comparar --salida .\.tools\mi-comparacion.json

# PDF escaneado o mixto
.\.venv\Scripts\python.exe .\procesamiento\probar_pdf.py .\.tools\ocr-bloque4\mixto.pdf --modo comparar --salida .\.tools\mi-comparacion-pdf.json
```

El cliente se llama `probar_pdf.py` por continuidad, pero ahora admite PDF, JPG/JPEG y PNG. No sobrescribe resultados: elegir otro nombre si ya existe la salida. Acepta `--puerto` para comprobaciones en otro puerto local; por defecto utiliza 8002 y siempre 127.0.0.1.

Laravel sigue conservando las cargas como **Pendiente**. Este bloque no llama a Python desde el navegador, no inicia trabajadores ni modifica las tablas de extracción. La integración que actualizará esos estados corresponde al siguiente bloque.

## Archivos de ejemplo conservados

En `.tools/ocr-bloque4/`:

| Original sintético | Resultado obtenido por HTTP real |
| --- | --- |
| `mixto.pdf` | `resultado-mixto.json` — página 1 digital, página 2 OCR, dos variantes OCR |
| `imagen.png` | `resultado-imagen.json` — OCR original y preprocesado |
| `invitacion.jpg` | `resultado-invitacion.json` — OCR preprocesado |
| `sin-texto.pdf` | `resultado-sin-texto.json` — texto vacío y observación para revisión manual |
| `escaneado.pdf` | Disponible para comprobaciones adicionales con el cliente |

Comparar los textos con el original: nombres, acentos, número de oficio, fecha y disposición. Que el proceso termine como `completado` significa que se ejecutó, no que el reconocimiento sea correcto. Un documento sin texto puede completar el proceso con texto vacío; se indica expresamente en observaciones. No se muestran CER, WER ni porcentajes sin referencia humana.

Las verificaciones HTTP se realizaron en una instancia temporal en 8003 porque 8002 ya estaba ocupado. Se detuvo únicamente esa instancia de prueba al finalizar; la instancia previa del usuario no fue alterada.

## Contrato actualizado

`POST /procesar?modo=original|preprocesado|comparar`

Mantiene la clave `X-Processor-Token`, el cuerpo binario y la restricción loopback. Ahora admite `application/pdf`, `image/jpeg` e `image/png`; el contenido debe coincidir con el tipo indicado. No recibe rutas ni nombres de ejecutables del cliente.

Se mantienen los campos del bloque 3 y se añaden:

- `metodo=ocr` en las páginas reconocidas por Tesseract.
- `texto_digital`: capa digital que había antes del OCR, si la página provenía de un PDF.
- `variantes_ocr`: lista con `modo`, `texto`, `duracion_ms` y `operaciones` para cada variante ejecutada.

`texto` y `texto_completo` usan una sola variante por página. En modo comparar, la primera es original y la segunda preprocesada. Los tiempos de variante incluyen su preparación y reconocimiento; el tiempo de página incluye también orientación y, en PDF, renderizado.

Si se deshabilita OCR mediante configuración, PDF puede seguir devolviendo `requiere_ocr` como en el bloque 3; las imágenes se rechazan con una explicación. No se reinterpreta `requiere_ocr` como un estado de base de datos de Laravel.

## Configuración nueva

Se añadieron ejemplos a `procesamiento/.env.example`. En esta máquina la ruta del ejecutable ya está configurada en el `.env` local, sin cambiar la clave existente.

| Variable | Valor inicial | Función |
| --- | --- | --- |
| PROCESSOR_OCR_ENABLED | true | Activa OCR en las páginas que lo necesitan |
| PROCESSOR_TESSERACT_CMD | tesseract | Ruta del ejecutable en el servidor; aquí apunta a `.tools/tesseract/tesseract.exe` |
| PROCESSOR_TESSDATA_DIR | vacío | Directorio opcional de datos de idioma; vacío usa el predeterminado del motor |
| PROCESSOR_OCR_MODE | original | Modo por defecto, sustituible por el parámetro modo |
| PROCESSOR_OCR_TIMEOUT_SECONDS | 40 | Límite por invocación de Tesseract, incluida OSD |
| PROCESSOR_RENDER_DPI | 250 | Resolución del renderizado de páginas PDF y metadato DPI enviado al motor |
| PROCESSOR_MAX_IMAGE_PIXELS | 12000000 | Máximo de píxeles antes de decodificar/renderizar y al transformar |
| PROCESSOR_CORRECT_ORIENTATION | true | Intenta orientación OSD |
| PROCESSOR_OSD_MIN_CONFIDENCE | 5 | Umbral de orientación, no de precisión OCR |
| PROCESSOR_PREPROCESS_GRAYSCALE | true | Escala de grises |
| PROCESSOR_PREPROCESS_CONTRAST | true | CLAHE moderado |
| PROCESSOR_PREPROCESS_DESKEW | true | Inclinación detectada dentro de ±5 grados |
| PROCESSOR_PREPROCESS_DENOISE | false | Mediana 3×3, opcional |
| PROCESSOR_PREPROCESS_BINARIZE | false | Otsu, opcional |
| PROCESSOR_PREPROCESS_UPSCALE | true | Ampliación hasta 2× para imágenes estrechas, sin exceder píxeles |

Si una operación como contraste, binarización o inclinación necesita gris, esa conversión se registra incluso si el interruptor específico de escala de grises está desactivado. Para evitarla también deben desactivarse las operaciones que la requieren.

Se mantienen tamaño máximo 20 MB, 100 páginas, salida de texto limitada y timeout global de 120 segundos. Un PDF largo puede alcanzar el timeout global antes de acabar: ajustar dentro de los rangos documentados según pruebas reales. La comparación añade una segunda pasada OCR y consume más tiempo. Un PDF cuya página exceda el límite de renderizado se rechaza antes de reservar el pixmap; puede bajarse el DPI mediante configuración. El límite de texto incluye la capa digital conservada y todas las variantes OCR, para acotar también los resultados de comparación.

## Instalación en otra máquina

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements.txt
# Para las pruebas:
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements-dev.txt
```

Instalar Tesseract siguiendo el enlace de [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), indicado por la documentación del proyecto. Usar un directorio nuevo dedicado al motor, no la raíz de un proyecto existente. Agregar español o copiar `spa.traineddata` desde [tessdata_fast 4.1.0](https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0). Para orientación debe existir también `osd.traineddata`. Configurar las rutas de ejecutable y datos en el `.env` del servidor.

```powershell
.\.tools\tesseract\tesseract.exe --version
.\.tools\tesseract\tesseract.exe --list-langs
```

En esta instalación la comprobación Authenticode del instalador informó un problema de validez de certificados. No se ejecutó en ese intento: se comprobó después el SHA-256 contra el digest publicado por la API del release oficial y coincidió. Se instaló con esa verificación; no se desactivaron controles de Windows. SHA-256 del instalador: `bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4`. SHA-256 del archivo español descargado: `6f2e04d02774a18f01bed44b1111f2cd7f3ba7ac9dc4373cd3f898a40ea6b464` (registro local, no una segunda validación independiente del modelo).

En Ubuntu, instalar los paquetes `tesseract-ocr`, `tesseract-ocr-spa` y `tesseract-ocr-osd`, crear el entorno Python e instalar requirements. Configurar `PROCESSOR_TESSERACT_CMD=tesseract` o su ruta Linux. El código evita flags Windows en Unix y termina los procesos por grupo. La ejecución Ubuntu está pendiente; la prueba específica de terminación Windows se omite en otros sistemas.

## Pruebas realizadas

Comando habitual desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pytest -c .\procesamiento\pytest.ini .\procesamiento\tests -q
.\.venv\Scripts\python.exe -m pip check
```

Resultado final de la suite completa: **38 pruebas aprobadas**, sin omisiones en Windows. `pip check` correcto. Permanece el aviso de deprecación de httpx en el cliente de pruebas de Starlette; no afecta al OCR de ejecución.

La ejecución dentro del sandbox pasó 37 pruebas y falló la terminación del descendiente. Se verificó que la terminación funciona fuera del aislamiento, y finalmente se repitió la suite completa con autorización fuera del sandbox, con 38 aprobadas. Se usó una carpeta temporal nueva del proyecto y se desactivó solamente la caché pytest en esa ejecución para evitar permisos incompatibles entre entornos; no se cambiaron permisos globales.

| Escenario requerido | Evidencia ejecutada |
| --- | --- |
| PDF digital de una página | Suite de regresión, texto español y valores conservados |
| PDF digital de varias páginas | Suite de regresión, separación de páginas |
| PDF escaneado de una página | OCR Tesseract real sobre PDF sintético |
| PDF escaneado de varias páginas | OCR Tesseract real, dos páginas |
| PDF mixto | Digital + OCR real, sin concatenación duplicada; también HTTP real |
| Imagen JPG/JPEG con texto | OCR real y comprobación de texto esperado |
| Imagen PNG con texto | OCR real y comparación; también HTTP real |
| Invitación gráfica | Imagen sintética con formas, color y texto; OCR real, PNG y JPEG |
| PDF sin texto reconocible | HTTP real sobre PDF vacío: resultado vacío con observación |
| Corrupto/no permitido | Suite sobre PDF corrupto/reparado, imágenes corruptas, formato discordante y tipo no permitido |

También se probaron comparación sin selección automática, original intacto, EXIF real, filtros opcionales, límite de píxeles antes del renderizado, rechazo de PNG animado, errores de idioma y timeout simulados, aplicación de rotación OSD mediante respuesta simulada y terminación real del árbol de procesos Windows. OSD se invocó realmente durante otras pruebas; no se cuantificó su fiabilidad en fotos giradas.

## Limitaciones y pendientes

- Todas las muestras son sintéticas. Falta evaluación manual con documentos institucionales, escaneos deteriorados, sellos y tipografías variadas. Las aserciones de texto esperado no son una medida general de precisión.
- No hay corrección de perspectiva ni garantía para texto manuscrito, tablas, fondos complejos o ángulos de inclinación fuera del rango. OSD puede fallar en textos cortos; se deja constancia y no se fuerza una rotación incierta.
- Los resultados preprocesados no siempre son mejores. No se combinan variantes ni se compara con una referencia humana todavía.
- El modo original conserva corrección EXIF, transparencia sobre blanco y, si es concluyente, orientación OSD, comunes a ambas variantes; no significa mantener los bytes originales como entrada directa de Tesseract.
- Las imágenes pequeñas pueden ampliarse en la variante preprocesada, pero no se recupera detalle que no existe en el original. Los PDF se renderizan a un DPI configurable.
- Los límites reducen consumo; aún no existe cuota dura de RAM del sistema operativo. Un cierre abrupto de todo el servicio/sistema puede dejar temporales; la limpieza por timeout controlado sí se ha verificado.
- No se procesan documentos Laravel automáticamente, ni se implementan la revisión web, persistencia de variantes en base de datos, reintentos de cola, CER o WER. Esos puntos pertenecen a los bloques siguientes.

Fuentes técnicas: [calidad de OCR Tesseract](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html), [línea de comandos](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [instaladores Windows](https://github.com/UB-Mannheim/tesseract/wiki).
