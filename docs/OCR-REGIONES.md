# OCR de oficios con membrete, sello y pie de contacto

Implementado y verificado el 14 de octubre de 2026, a partir de la imagen real `Bienes-Enviado.jpeg` aportada por el usuario. El usuario confirmó en la conversación que había cotejado la referencia con la imagen. La política automática se identifica ahora como `automatico-regiones-v2`.

## Resultado del caso real

Se reprodujeron las tasas de la captura usando la referencia confirmada del **contenido del oficio**, sin añadir a la referencia membrete decorativo, sello ni contacto del pie:

| Salida comparada con esa misma referencia | CER | WER |
| --- | ---: | ---: |
| Flujo anterior | 19,88 % | 28,03 % |
| Flujo nuevo por regiones | 0,41 % | 2,65 % |

La reducción combina mejor reconocimiento y exclusión de contenido auxiliar que no forma parte de la referencia. No se interpreta como precisión global del sistema ni como evaluación de otras instituciones. Permanecen errores puntuales de signos, acentos y fragmentación de palabras; la revisión humana continúa siendo necesaria. En particular, no se cambió `MARE` por `MADRE`, ni se corrigieron nombres, números o frases mediante contexto o un modelo generativo.

El número de oficio y la fecha se recuperaron en la prueba. Los artefactos locales, excluidos de Git, están en `.tools/diagnostico-bienes`: copia de entrada, referencia confirmada, salida anterior, salida nueva, `comparacion.json` con tasas y conteos, y resultados de diagnóstico. Contienen información del documento del usuario; no deben publicarse. El archivo de OneDrive y la ficha previamente cargada no se reemplazan.

Se creó una ficha independiente **validacion-bienes-v2.jpeg**, UUID `351003c8-0e4f-4781-8fe7-2cdab590a8a0`, mediante el manejador del Job contra FastAPI local actualizado. Conserva su original, PDF normalizado, contenido principal y OCR completo en la base de aplicación. En Chrome se guardó la referencia aportada y confirmada por el usuario, con una nota de procedencia, y se solicitó el cálculo real a FastAPI/jiwer: la tabla mostró 0,41 % / 2,65 %, sin errores JavaScript. Captura privada: `.tools/diagnostico-bienes/revision-v2.png`; comprobación: `navegador.json`. Esta validación utiliza una cola aislada y no consume tareas ajenas ni reemplaza la ficha anterior. El SHA-256 del original de OneDrive coincide con la copia de entrada.

## Cambios

- El modo automático utiliza TSV de Tesseract: palabras, posiciones, líneas y párrafos. El parser trata las comillas como caracteres, evitando que una comilla del texto absorba filas siguientes como si fuera CSV entrecomillado.
- Conserva saltos entre líneas reconocidas y decide los espacios entre párrafos con sus separaciones geométricas. Para oficios reconocidos como una sola columna, reúne fragmentos con posiciones horizontales compatibles; no aplana párrafos completos en una línea.
- En imágenes pequeñas, la ampliación automática puede llegar a 2,5× y 2400 píxeles de ancho, siempre respetando el límite de píxeles. Usa interpolación cúbica en ese modo. Los modos manuales conservan su tratamiento anterior.
- Reconoce un perfil acotado de oficio GAD/Parroquial/Imantag con anclas `OFICIO` o `CIRCULAR`. Localiza el comienzo administrativo y un pie de contacto separado, en lugar de recortar un porcentaje fijo de todas las páginas.
- Dentro de ese perfil, detecta candidatos rectangulares de tinta azul/violeta en la zona superior derecha. Elimina esa región solamente en una copia para OCR. No es un detector universal de sellos: se advierte de la posibilidad de superposición y se conserva la lectura completa.
- Trata número y fecha como un bloque local de identificación. Usa umbral adaptativo, corrección local de inclinación y segmentación de bloque, sin reconstruir sus caracteres a partir de una plantilla. La sustitución del bloque exige reconocer identificación, dígitos y una expresión de fecha.

Las páginas sin ese perfil conservan la lectura completa: no se les aplican estos recortes ni exclusiones. La reconstrucción general por TSV sí se utiliza en OCR automático. Los PDF digitales que ya tienen una capa suficiente siguen con la extracción digital existente; esta mejora regional se aplica a imágenes y páginas que pasan por OCR, incluidas las de PDF escaneados o mixtos. No incorpora clasificación por institución, departamento ni recibido/enviado.

## Conservación y presentación

Cada variante OCR puede guardar en el JSON de `extracciones_documento`:

- `texto`: contenido mostrado como transcripción principal.
- `texto_pagina_completa`: OCR completo previo a las exclusiones, cuando se utiliza lectura regional.
- `alcance`: `pagina_completa` o `contenido_principal`.
- `exclusiones` y `operaciones`: explicación de lo aplicado.

La revisión indica el alcance y ofrece el desplegable **OCR de página completa antes de excluir zonas auxiliares**. La vista de texto completo reúne las transcripciones principales de todas las páginas y enlaza la revisión para consultar el OCR completo. El original y el PDF de entrega conservan visualmente membrete, sello y pie; no se les aplican las máscaras del OCR. Las referencias humanas se mantienen en su historial independiente.

No se necesita otra migración: los datos adicionales se guardan dentro del JSON de variantes existente. El límite de caracteres cuenta tanto el contenido principal como el OCR completo conservado. El servicio mantiene el timeout global y la exclusión de concurrencia. En un oficio reconocido puede ejecutar hasta tres lecturas, además de OSD: página completa, contenido principal e identificación local.

## Evaluación y uso

La referencia debe incluir número, fecha, destinatario, asunto y cuerpo, con el mismo alcance que el resultado comparado. Si se incluyen anotaciones como “Sello de recepción” y transcripciones del contacto en una referencia que se compara con el contenido principal, las métricas dejan de medir la tarea pretendida. CER/WER sigue normalizando espacios y saltos de línea; la separación visual requiere revisión independiente.

Reiniciar **Python y el trabajador Laravel** para cargar el código nuevo; recargar el navegador. Los documentos ya completados no se reprocesan automáticamente y sus resultados anteriores permanecen intactos. La ficha independiente de validación permite comparar este caso sin sustituir su extracción ni referencia originales.

## Pruebas y límites

Regresión completa: **57 pruebas Python aprobadas** y **52 pruebas Laravel, 292 aserciones, aprobadas sobre PostgreSQL aislado**. Se verificaron comillas TSV, saltos de línea y párrafos, reunión de fragmentos, anclas de oficio, conservación de número/fecha/cuerpo, exclusión del pie, uso de copias, respaldo completo y ausencia de recorte para formato desconocido. La suite mantiene las pruebas reales de OCR para JPG/PNG/PDF escaneado/mixto y las de seguridad, cola, referencias, métricas y eliminación lógica. Permanece el aviso de deprecación de httpx del cliente de pruebas.

Las regiones son heurísticas. Un sello negro, un sello en otra zona, tinta azul que sea contenido relevante, contactos integrados en el cuerpo, varias columnas, manuscritos, tablas o perspectivas más fuertes pueden necesitar revisión o un perfil diferente. Una región omitida puede contener información válida: consultar siempre el OCR completo y el original cuando haya duda. El caso probado no garantiza los mismos resultados en todos los documentos con membrete parecido.

Fuentes primarias: [salida TSV y segmentación de Tesseract](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html), [preprocesamiento y calidad de entrada](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).
