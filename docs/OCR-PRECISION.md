# Recuperación de texto impreso bajo firmas y sellos

Actualización del 15 de octubre de 2026. Sustituye el resultado parcial descrito en [OCR-VIALIDAD.md](OCR-VIALIDAD.md): separar las columnas no bastaba para recuperar el nombre de la presidenta ni su cargo y correo.

## Tratamiento aplicado

Se mantiene el OCR de página completa y la separación de plantilla y columnas. En los bloques de dos firmantes se añade una lectura de líneas impresas: las cajas de los cargos y su altura permiten ubicar nombres y continuaciones, sobre una copia con atenuación moderada del azul. La segunda lectura utiliza el modelo español de [tessdata_best oficial](https://github.com/tesseract-ocr/tessdata_best), configurado separadamente; el cuerpo sigue usando el modelo anterior. Son seis recortes como máximo por bloque de dos columnas. Los nombres proceden exclusivamente de esos resultados ópticos; no se buscan en referencias humanas ni se incorporan nombres institucionales al código.

Después se aplican reglas de normalización acotadas:

- Abreviaturas y signos de formato: Íng. → Ing., Cl. ante números de identificación → CI., terminaciones espurias después de teléfonos, despedida Atentamente y N° en la identificación de un oficio. Estas son reglas de formato, no nuevas lecturas ópticas de cada signo.
- Cargos y continuaciones en mayúsculas: una palabra dudosa se contrasta con palabras que aparecen al menos dos veces en la propia página. Solo se corrige si hay una candidata única a distancia de edición pequeña. La forma canónica se elige por frecuencia. Los títulos y otros términos administrativos reconocidos se protegen para evitar cambios como PRESIDENTE → PRESENTE. No se aplica esta corrección a los nombres personales.
- Correos: se reconocen confusiones acotadas del delimitador @ y se extrae una dirección completa. No se completa un usuario ni un dominio ausentes. Si ninguna lectura ofrece una dirección reconocible, se conserva la anterior.

Por tanto, el resultado combina lectura óptica y normalización de formato/consistencia. No es una transcripción exclusivamente literal de cada carácter del OCR, ni un modelo entrenado con las referencias del usuario. Las reglas pueden fallar sobre otros documentos y no garantizan resolver cualquier superposición. Se conserva el OCR previo y el PDF intacto para el cotejo.

## Resultado controlado

Referencia: versión aportada por el usuario, limitada a número/fecha, destinatario, asunto, cuerpo, despedida y datos impresos de ambos firmantes. Excluye membrete decorativo, descripciones de firmas y sellos, pie institucional y el bloque de recepción que no aparece en esta página.

| Resultado | CER | WER |
| --- | ---: | ---: |
| Salida parcial anterior mostrada por el software | 1,93 % | 6,79 % |
| Nueva lectura y normalización | 0,11 % | 0,71 % |

Se recuperan Ing. Erika Bolaños, PRESIDENTA DEL GAD PARROQUIAL DE IMANTAG, su identificación, teléfono y correo; el bloque de Pablo Yacelga se conserva separado con su cargo y contactos. Las palabras del cuerpo permanecen idénticas a la salida anterior. Persisten «víal» en lugar de «vial» y una diferencia de guion en «Presente».

Las tasas comparan la misma referencia de contenido en ambas salidas. No se equiparan a las tasas de la captura anterior, cuya referencia incluía otras zonas. Este documento se usó para ajustar el tratamiento; falta probarlo con documentos nuevos para medir generalización.

Los cuatro ejemplos anteriores conservan sus resultados: los primeros dos oficios mantienen CER/WER de 0,41 % / 2,65 % y 0,59 % / 3,17 %; la segunda página recibida con firmas y el PDF digital de Ambiente conservan exactamente sus textos previos.

Artefactos privados: `.tools/diagnostico-vialidad/refinado.txt`, `refinado.json`, `referencia-contenido.txt` y `comparacion-refinado.json`. Se mantienen separados de las salidas anteriores. El algoritmo de producción no lee esos archivos.

## Modelo y configuración

En este equipo se instaló el modelo en `.tools/tessdata-best`, con su licencia Apache-2.0. El archivo está excluido de Git. Fuente: `https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/spa.traineddata`. SHA-256 verificado:

```text
e2c1ffdad8b30f26c45d4017a9183d3a7f9aa69e59918be4f88b126fac99ab2c
```

Para otra instalación, descargar ese modelo y su LICENSE del repositorio oficial, verificar el hash y configurar en `procesamiento/.env`:

```dotenv
PROCESSOR_REFINEMENT_TESSDATA_DIR=C:/ruta/al/proyecto/.tools/tessdata-best
```

Sin modelo configurado se conserva la lectura por columnas anterior y las reglas de formato/consistencia; no se ejecuta la segunda lectura de precisión. Las operaciones guardadas indican si el modelo se utilizó. Si falla la lectura opcional, se conserva la lectura regional y se registra una observación.

Todo el reconocimiento se realiza localmente; no se envían documentos a servicios externos. Reiniciar el servicio Python y cargar de nuevo el PDF para aplicar el tratamiento. Las fichas completadas y sus referencias previas no se sobrescriben.

Validación final: 82 pruebas Python aprobadas. Paquete HTTP real comprobado: PDF idéntico al original, transcripción refinada y OCR completo de respaldo conservados.
