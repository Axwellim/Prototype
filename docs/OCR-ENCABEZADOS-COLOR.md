# Encabezados impresos azules y firmante único

Verificado el 15 de octubre de 2026 con `Recibido-Vialidad.jpeg`, recibido de la Junta de Agua Potable. Su encabezado azul contiene datos del emisor que deben conservarse. La pasada general fragmentaba la dirección y el contacto; también confundía el día y convertía una rúbrica en «VIA».

## Tratamiento

En modo automático, se buscan de tres a seis filas de texto azul en la parte superior de la copia original en color, excluyendo componentes grandes compatibles con dibujos. El color por sí solo no autoriza borrar contenido: se exige reconocer dirección o contacto para adoptar la nueva lectura. Se mantiene el texto reconocido situado por encima de esa región y el cuerpo posterior.

La región se alinea mediante proyección de su tinta y se lee por filas sobre el canal rojo, que da contraste al texto azul. No se aplica la atenuación de azul utilizada para separar firmas. Para palabras alfabéticas dudosas de una línea de dirección se permiten hasta seis intentos locales: solo se cambia una palabra si dos modos de segmentación devuelven la misma alternativa a un carácter de distancia. No hay diccionario de calles ni nombres procedentes de la referencia. Ambos modos pertenecen al mismo motor y no son evidencia independiente; esa coincidencia puede ser errónea en otros documentos.

La fecha próxima al encabezado se reconoce localmente. Se normalizan confusiones de dígitos O/U → 0 e I/L → 1 únicamente en el campo de día de una fecha textual y se valida el calendario; no se completan día, mes o año ausentes. Se normaliza la inicial del lugar. Para contactos con separador «/», un usuario y dominio ya reconocidos pero separados por un espacio pueden unirse mediante @. También se admite una comilla confundida con ese delimitador. No se inventan caracteres del usuario ni del dominio.

En cierres con un solo nombre y cargo impresos, se apartan líneas cortas compatibles con trazos azules entre «Atentamente» y el nombre. El nombre y las líneas posteriores se conservan. El OCR completo previo queda en `texto_pagina_completa`; el original y el PDF normalizado no se modifican con los tratamientos de OCR. Todas las lecturas siguen contando para el límite de texto.

## Resultado

Se recuperan la dirección «Simón Bolívar y García Moreno Casa de Aguas», el contacto `juntaaguapotableimantag@gmail.com`, la fecha del 01 de junio de 2026 y el firmante sin el ruido de la rúbrica. El cuerpo entre destinataria y despedida mantiene exactamente las mismas palabras de la salida anterior, normalizando espacios y saltos de línea.

La referencia es la aportada por el usuario, sin el marcador descriptivo «[Firma manuscrita]». Se conserva el punto final tras Imantag de esa referencia, aunque no se aprecia impreso en la imagen.

| Salida | CER | WER |
| --- | ---: | ---: |
| Pasada anterior | 6,35 % | 18,86 % |
| Nueva lectura | 0,09 % | 0,57 % |

La única diferencia restante es ese punto final. Las cifras comparan exactamente la misma referencia y no se equiparan a las de la captura (7,39 % / 18,64 %), cuyo texto exacto no se sustituyó ni se asumió idéntico. Este ejemplo se utilizó para ajustar las heurísticas y no demuestra el rendimiento sobre documentos nuevos.

Los cinco ejemplos anteriores conservan sus resultados: primeros oficios enviado y recibido, segunda página con firmas, PDF digital de Ambiente y oficio enviado de Vialidad con dos firmantes. Pasaron 87 pruebas Python; tras reforzar la conservación del emisor por encima del encabezado se repitieron las 11 pruebas afectadas y la extracción real, sin cambios de resultado. Se verificó también el paquete HTTP con PDF normalizado, transcripción y OCR de respaldo.

Artefactos privados: `.tools/diagnostico-agua` conserva entrada, referencia, salidas anterior y nueva, comparación y paquete verificado. El código de producción no consulta estos archivos. Reiniciar Python y cargar de nuevo la imagen para obtener el resultado; las fichas previas no se sobrescriben.
