# Plantilla y firmantes en dos columnas

Actualización posterior: el resultado parcial descrito aquí fue sustituido por [la lectura de precisión y normalización documentada](OCR-PRECISION.md). Esta guía conserva el estado anterior como antecedente.

Revisado el 15 de octubre de 2026 con `Vialidad-enviado.pdf`, una página escaneada sin capa digital. Se comparó la imagen renderizada con la salida del procesador. La referencia proporcionada por ChatGPT incorpora una recepción del 29 de septiembre de 2026 a las 16h00 que **no aparece en esta página**. No debe utilizarse ese bloque para evaluar este archivo. Los marcadores descriptivos de firmas y sellos tampoco son texto impreso del oficio.

## Cambios del algoritmo

- El reconocimiento de membrete consulta las posiciones de las palabras, además de las líneas. Así se reconoce el emisor cuando el OCR une el lema con el número del oficio. La mención al GAD en el destinatario sigue sin autorizar recortes.
- Una región candidata a sello solo se enmascara si termina antes del asunto. En este PDF se detectaba una marca tenue dentro del cuerpo; ahora no se oculta. Si no se identifica el asunto, tampoco se autoriza esa máscara. El cuerpo del nuevo resultado contiene exactamente las mismas palabras que la pasada completa anterior, normalizando espacios y saltos de línea.
- El identificador reconocido en la pasada completa se conserva si cumple una estructura alfabética con número y año y la lectura local introduce un código discrepante. No se obtiene el número de una referencia humana.
- Cuando aparecen despedida, cargos alineados en dos columnas y datos de contacto, se reconoce cada bloque por separado sobre una copia con atenuación de tinta azul. Se conserva el orden completo del firmante izquierdo antes del derecho. Se requiere reconocer un nombre y un cargo en ambos bloques; de lo contrario se conserva la lectura regional previa. Los correos se intentan leer localmente y se conserva su lectura previa si el intento no aporta un contacto reconocible.

Los recortes y máscaras se aplican solo a copias de OCR. El original, el PDF normalizado y el OCR de página completa se conservan. La lectura del contenido principal excluye el membrete decorativo, el pie institucional y la marca de CamScanner. Se mantienen los datos de contacto de los firmantes, aunque su OCR puede contener errores.

## Resultado y límites

Se conservan número y fecha del oficio, destinatario, asunto y cuerpo. Se elimina el ruido del membrete y pie, y se separa el bloque de Pablo Yacelga del bloque de la presidenta. Persisten errores importantes en el nombre y cargo de la presidenta bajo el sello, en la despedida y en algunos signos y contactos. Las observaciones de procesamiento exigen cotejar esos datos. No se insertan nombres, cargos ni números desde la transcripción de ChatGPT y no se reconstruyen letras ocultas mediante reglas de contexto.

La separación por columnas es una heurística de un diseño de dos bloques aproximadamente simétricos, no un detector universal de estructura. La atenuación de color tampoco separa perfectamente tinta azul y texto negro cuando se superponen. Es necesario revisar los firmantes en este documento; no se presenta su transcripción como totalmente corregida.

No se calcula una nueva tasa CER/WER contra la referencia proporcionada porque contiene contenido ajeno a la página y comentarios descriptivos. Los 11,91 % / 19,86 % de la captura no se equiparan a una medición nueva. Antes de evaluar, corregir el alcance de la referencia y cotejar los datos superpuestos con el original.

La regresión sobre los cuatro ejemplos anteriores se verificó: primer enviado mantiene CER 0,41 % / WER 2,65 %; primera página recibida mantiene 0,59 % / 3,17 %; el cierre con firmas de la segunda página y el PDF digital de Ambiente conservan exactamente su texto anterior. Estos son ejemplos usados para ajustar el sistema, no una validación independiente del rendimiento general.

Artefactos privados: `.tools/diagnostico-vialidad` conserva entrada, imagen renderizada, OCR completo anterior, salida nueva y JSON. `.tools/regresion-oficios-vialidad` conserva las dos primeras regresiones. No se modifica la carga anterior ni su referencia en la base. Reiniciar Python y cargar nuevamente el PDF para obtener la nueva lectura.

Validación final: 75 pruebas Python aprobadas y paquete HTTP real verificado, con PDF idéntico al original, nueva transcripción y OCR completo de respaldo.
