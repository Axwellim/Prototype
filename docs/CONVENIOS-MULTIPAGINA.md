# Convenios digitales de varias páginas

El convenio económico-productivo de cinco páginas contiene texto digital visible. La imagen de fondo y los dos logotipos superiores repetidos provocaban su envío innecesario al OCR. Las letras «e» aisladas correspondían a viñetas mal reconocidas. La última página, con menos texto y dos columnas de representantes, necesitaba conservar la lectura de cada bloque por separado.

## Cambio de procesamiento

La comprobación de fondo claro admite logotipos pequeños en el 15 % superior únicamente si la misma imagen aparece en varias páginas del PDF. No admite por esa razón imágenes adicionales en el cuerpo. Una página con menos texto puede reutilizar la comprobación de un fondo ya verificado dentro del mismo archivo, siempre que conserve suficientes caracteres visibles distribuidos verticalmente. El estado no se comparte entre documentos; el texto oculto no autoriza esta excepción. Se mantienen las comprobaciones de tinta rasterizada, cobertura, transformación y límites.

Para documentos digitales numerados sobre estos fondos, se reconstruyen los párrafos mediante las posiciones de las líneas. Se conservan títulos y cláusulas, se representan las viñetas reales como guiones y se unen sus continuaciones. Los bloques finales de representantes en dos columnas se leen por separado, manteniendo nombres y cargos asociados. Las palabras proceden del PDF: no se sustituyen por textos de referencia ni se completan nombres mediante listas particulares.

La capa digital previa queda en `texto_digital`. El PDF entregado se conserva idéntico al original. Las páginas escaneadas siguen pasando por OCR; esta mejora no equivale a reentrenar Tesseract ni garantiza resultados perfectos en cualquier plantilla.

## Comparación

Las cinco páginas tienen CER y WER de 0,00 % frente a la referencia revisada, normalizando espacios. Se excluyeron de la referencia los marcadores de página y «Continuación de la cláusula 4.1.», que eran anotaciones explicativas ausentes del original. La separación visual también se revisó por separado, porque CER/WER no evalúan saltos de línea.

Las entradas, transcripciones, métricas y comprobaciones se conservan privadamente en `.tools/diagnostico-convenio`. Las referencias guardadas y las fichas anteriores no se sobrescriben. Para aplicar el cambio, reiniciar el servicio Python y cargar nuevamente el documento.

Validación final: 103 pruebas Python aprobadas; siete documentos anteriores reprocesados sin diferencias de palabras ni método; respuesta HTTP verificada con cinco páginas digitales, capa previa conservada y PDF idéntico byte por byte.
