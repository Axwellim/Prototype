# Párrafos y listas en oficios fotografiados

La imagen de Bienes recibido tenía correctamente reconocido el contenido, pero el OCR agrupaba los cuatro párrafos del cuerpo y las cinco viñetas en bloques únicos. El formateador anterior solo separaba párrafos cuando cambiaba el grupo interno del OCR, y no reconocía las viñetas confundidas con `+` o `+.`.

La reconstrucción considera también las posiciones y el final corto de una línea con puntuación, aunque Tesseract mantenga el mismo grupo. Las continuaciones largas que terminan en dos puntos se reúnen con la oración anterior; los rótulos cortos siguen separados. Las viñetas reconocidas como signos más al comienzo de una línea se representan como guiones, cada elemento por separado. Solo los títulos consecutivos al inicio se espacian como bloques; los datos del destinatario mantienen sus líneas independientes. El asunto se reúne hasta el saludo.

Las palabras proceden exclusivamente del OCR. No se copian los párrafos de referencia ni se incorpora el bloque repetido al final del mensaje del usuario. No se corrigen por inferencia las comas reconocidas en lugar de puntos. Se conserva el OCR previo como respaldo y no se modifica la imagen original.

Se comprobó la presencia de los cuatro párrafos y cinco elementos de la lista en la imagen real, así como la conservación del contenido de los cuatro ejemplos fotografiados de Bienes enviado, Bienes recibido, firmas y Agua, normalizando únicamente símbolos de viñeta para compararlos. La suite general aprobó 109 pruebas durante la implementación; la versión final pasó las 16 pruebas relacionadas, incluidas tres nuevas comprobaciones de formato. Se verificó también el paquete HTTP con PDF y transcripción.

Texto revisable privado: `.tools/diagnostico-recibido/texto-parrafos-corregidos.txt`. Reiniciar el servicio Python y cargar nuevamente la imagen. Las fichas previas permanecen sin sobrescribir.
