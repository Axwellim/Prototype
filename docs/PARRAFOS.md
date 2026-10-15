# Reconstrucción de párrafos

Se corrigieron los saltos físicos y las líneas vacías que fragmentaban oraciones del cuerpo de un oficio. El ejemplo de la Junta de Agua Potable conservaba el texto correcto, pero separaba «en sus» de «funciones diarias» y «tuberías de» de «agua potable».

El procesamiento automático OCR y la extracción digital ahora reconstruyen el cuerpo entre la fórmula de consideración y la despedida. También se admite una página de continuación que empieza directamente con prosa y termina con despedida. Sin esas señales se conserva el formato disponible.

Las líneas físicas consecutivas de prosa se unen con espacios. Una línea vacía se elimina si el texto continúa en minúscula o después de una palabra de enlace, siempre que la línea anterior no cierre una oración. Los límites dudosos se conservan. Se mantienen separados encabezados, destinatarios, firmantes, listas, rótulos, tablas y títulos en mayúsculas. No se cambian palabras ni signos de puntuación ni se deshacen guiones.

La lectura previa se conserva en el campo de respaldo ya disponible: `texto_pagina_completa` para OCR o `texto_digital` para extracción digital. Si ya existe un OCR completo previo, no se sobrescribe. Todas las versiones cuentan para el límite de texto. No se altera el original ni el PDF normalizado; el navegador ajusta visualmente cada párrafo al ancho disponible.

El 15 de octubre de 2026 se reprocesaron los seis documentos reales utilizados hasta ahora y se comprobó que sus secuencias de palabras permanecen idénticas y que aplicar el formato una segunda vez no cambia el resultado. Por ello, CER/WER no cambian: esas métricas ya normalizan espacios y saltos de línea. La mejora es de estructura y legibilidad.

Las salidas están en `.tools/parrafos-verificados`, excluidas de Git. En particular, `agua.txt` contiene los cuatro párrafos del cuerpo sin cortes internos y mantiene el encabezado y el firmante separados. No se modificaron las fichas ni las referencias humanas ya guardadas. Reiniciar Python y cargar de nuevo el documento para obtener el nuevo formato en el sistema.
