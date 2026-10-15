# Oficios con continuación y plantilla

En `Sociocultural-Enviado.pdf`, ambas páginas tienen texto digital visible correcto. La segunda página contiene sello y firma por debajo de «Atentamente», pero por encima del límite inferior fijo admitido anteriormente. Esto provocaba OCR innecesario y la inclusión del membrete y pie rasterizados. El filtro OCR del membrete requiere identificación del oficio; una continuación puede carecer de ella.

Se admite ahora una imagen pequeña de firma o sello después de un cierre visible, situado a partir del 35 % de la página, únicamente si el fondo ya se verificó en otra página del mismo PDF. Se mantienen los controles del fondo central, texto visible, tamaño y cobertura. No se añaden recortes fijos para páginas de continuación.

Los oficios digitales sobre fondos verificados reconstruyen sus párrafos mediante posiciones de líneas, separando rótulos, puntos numerados y el cierre. Una palabra en negrita dentro de un punto numerado no activa por sí sola el formato de cláusulas de convenios. Los nombres y cargos del cierre conservan sus líneas independientes.

La salida de las dos páginas conserva literalmente todas las palabras de la capa digital original, excluyendo solo espacios y saltos físicos al comparar. El membrete y pie pertenecen a la imagen de plantilla y no se transcriben. La capa anterior queda en `texto_digital`; el PDF permanece intacto. No se emplea una transcripción de referencia para generar el resultado, y no se atribuye CER/WER sin una referencia humana independiente.

Diagnóstico privado y texto revisable: `.tools/diagnostico-sociocultural`. Reiniciar el servicio Python y volver a cargar el PDF. Las cargas anteriores no se sobrescriben.

Validación: 105 pruebas Python aprobadas; siete ejemplos anteriores conservan palabras y método, y el convenio de cinco páginas conserva su texto completo. Los paquetes HTTP del oficio y del convenio conservan el PDF byte por byte y entregan las transcripciones verificadas.

## Formato de encabezado y firmante

La preferencia final del usuario conserva cada dato en su propia línea: número de oficio, fecha, tratamiento, nombre y cargo del destinatario. Los bloques se separan mediante una línea vacía. Después de Atentamente se separa el bloque de la firmante, pero sus datos consecutivos no llevan líneas vacías intermedias. El cuerpo conserva sus párrafos y puntos numerados completos. Se conserva Ing. según el original.

Validación del ajuste: 24 pruebas relacionadas aprobadas y verificación de los saltos solicitados sobre las dos páginas reales, sin cambios de palabras. Texto actualizado en .tools/diagnostico-sociocultural/texto-corregido.txt. Las cargas anteriores no se sobrescriben; reiniciar el procesador y cargar nuevamente el documento.

## Cierre con coma y asunto en dos líneas

Se admite Atentamente seguido de coma como inicio del cierre digital. El asunto puede continuar en la línea siguiente sin que su etiqueta provoque una línea vacía. En el oficio económico enviado se verificaron ambos bloques y la conservación de palabras; 23 pruebas relacionadas aprobadas. Texto privado en .tools/diagnostico-economico/texto-formato-corregido.txt.
