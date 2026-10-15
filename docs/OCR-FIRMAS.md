# Lectura del cierre con firmas

Verificación del 15 de octubre de 2026 con `Bienes-Recibido2.jpeg`. La mejora es una heurística de procesamiento de imagen y segmentación: no utiliza la referencia humana para producir texto, no incorpora nombres específicos y no reentrena Tesseract.

## Comportamiento

En modo automático se busca un cierre «Atentamente» seguido de entre dos y ocho firmantes y varios cargos impresos en una columna. Se exige tinta azul/violeta en esa zona. Si las señales no bastan, se conserva la lectura completa. Los diseños de otras columnas y las firmas exclusivamente negras no activan esta corrección.

En copias temporales se atenúa el color mediante canal azul, diferencia cromática y reconstrucción de los píxeles enmascarados. Se reconocen el bloque y las líneas de nombres por separado. Se eligen lecturas según geometría y confianza interna de Tesseract; esa confianza no mide exactitud real. Las palabras siguen siendo resultados del OCR: no se completa «PRESIDE» con un diccionario ni se reemplazan nombres con la referencia. La selección puede preferir una lectura errónea.

El texto principal conserva el cuerpo hasta el cierre y los rótulos impresos reconocidos. Se apartan marcas manuscritas y zonas auxiliares posteriores al bloque de firmantes. Se conserva la lectura previa en `texto_pagina_completa`, además de la primera pasada en `texto_lectura_inicial` cuando hubo recuperación de cobertura. El original y el PDF normalizado permanecen intactos. Las observaciones avisan que nombres y cargos superpuestos requieren cotejo. Un fallo OCR de la pasada opcional conserva la lectura completa.

Este tratamiento no es un reconocedor de escritura manuscrita ni un detector universal de firmas o sellos. No genera «[Firma manuscrita]», no interpreta la anotación lateral y no reconstruye una tabla de recepción. Los nombres con tinta superpuesta pueden seguir conteniendo errores; la supresión de marcas tampoco garantiza separar todo el texto impreso en otros formatos. La política registrada para nuevas extracciones automáticas es `automatico-cierre-v4`. No requiere migraciones ni nuevas dependencias.

## Medición controlada

La referencia abarca exclusivamente el cuerpo impreso y el cierre, incluidos comité, período, nombres y cargos, a partir de la transcripción revisada por el usuario. Excluye marcadores explicativos de firma, interpretación manuscrita incierta y tabla descriptiva del sello. Se comparan ambas salidas contra esa misma referencia.

| Salida | CER | WER |
| --- | ---: | ---: |
| Anterior | 5,98 % | 11,57 % |
| Nueva | 0,27 % | 1,85 % |

El cuerpo previo a «Atentamente» es idéntico antes y después. Se recuperan PRESIDENTA, TESORERA y SECRETARIA. Persisten diferencias de acento en COMITÉ y Paulina, guion del período y puntuación del cuerpo. Las tasas no equivalen a las de la captura (9,09 % / 12,23 %), cuyo texto exacto de referencia no se asumió idéntico. Esta muestra se usó para ajustar la heurística; no demuestra rendimiento sobre documentos futuros.

Los dos casos anteriores mantienen CER/WER: enviado 0,41 % / 2,65 %; recibido primera página 0,59 % / 3,17 %. Los artefactos privados están en `.tools/diagnostico-firmas` y `.tools/regresion-oficios-firmas-final`. No se modificó la carga anterior ni su referencia. Se creó la ficha independiente `validacion-firmas-v4.jpeg`, UUID `488d5ca0-0a59-468a-9a59-8193c5c73bfb`, validada mediante el Job de Laravel y el servicio HTTP local: PDF y ambas lecturas guardados.

Para utilizar el código actualizado, reiniciar el servicio Python y el trabajador de la cola. Las fichas ya completadas conservan su extracción anterior; cargar nuevamente el documento para obtener la nueva lectura.

Verificación automatizada: 66 casos Python comprobados entre la suite general y la repetición de los casos de paquete PDF tras actualizar la etiqueta de versión; 53 pruebas Laravel con 296 aserciones aprobadas en PostgreSQL de pruebas.
