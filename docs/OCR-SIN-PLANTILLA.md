# Documentos recibidos sin plantilla del GAD

Verificado el 15 de octubre de 2026 con `Bienes-Recibido.jpeg`, aportado por el usuario. El usuario confirmó que la transcripción hasta el último recurso solicitado estaba revisada contra la imagen. Las “Observaciones de digitalización” posteriores son comentarios de ChatGPT y no se incluyeron en la referencia.

## Causas corregidas

La detección de plantilla anterior era demasiado amplia: buscaba GAD, Parroquial e Imantag en la zona superior, pudiendo confundir el destinatario con el membrete del emisor. Ahora esas señales deben estar situadas **antes de la identificación del oficio**. Una mención al GAD en el destinatario no autoriza recortes ni máscaras de plantilla. En este caso se conserva el encabezado del comité, la fecha y la página completa.

También existía una lectura incompleta de la fotografía incluso antes del recorte: la primera pasada omitía gran parte de los párrafos y la lista. Se añadió una comprobación de cobertura por componentes de imagen y cajas de palabras del OCR. Ante cobertura inferior a 0,75, se intenta una corrección local de iluminación y se repite la segmentación automática de página. Solo se adopta esa lectura si la cobertura mejora más de 0,08. Estos valores son señales geométricas internas, **no precisión OCR ni sustitutos de CER/WER**. La selección no consulta la referencia humana.

Si siguen detectándose posibles omisiones, se registra una observación para revisión. La corrección no garantiza detectar todas las omisiones ni reconstruye palabras por contexto. La iluminación se corrige en una copia, sin modificar el original ni el PDF de entrega.

La política es ahora `automatico-cobertura-v3`. Si se utiliza la lectura recuperada, se conserva la primera en `texto_lectura_inicial` dentro del JSON de variantes. La interfaz la muestra en **Lectura inicial antes de recuperar zonas sin transcribir**. Se cuenta también ese texto dentro del límite global. No requiere otra migración ni dependencias nuevas.

## Resultados de las dos imágenes reales

Ambos documentos se volvieron a procesar con el mismo código final y sus respectivas referencias confirmadas:

| Caso | Alcance conservado | CER | WER |
| --- | --- | ---: | ---: |
| Bienes enviado, membrete del GAD | Contenido principal; OCR completo conservado | 0,41 % | 2,65 % |
| Bienes recibido, comité de padres | Página completa | 0,59 % | 3,17 % |

En el recibido se comprobaron encabezado del emisor, fecha del 29 de septiembre de 2026, párrafos y los cinco elementos de la lista, incluidos parlante, micrófono, proyector y sillas. En el enviado se mantuvieron las tasas anteriores, sin regresión en esta muestra. Quedan errores puntuales de signos y segmentación, por lo que la revisión humana sigue siendo necesaria. Estas tasas no representan el rendimiento general de todos los documentos.

La comparación controlada de la salida anterior del recibido contra la referencia documental sin comentarios dio CER 62,34 % y WER 64,79 %. No se equipara directamente esa medición con los 72,20 % / 74,16 % de la captura del usuario: la salida y la referencia exactas de esa evaluación no se sustituyeron ni se asumieron idénticas. Los datos comparados se conservaron para poder inspeccionarlos.

Artefactos privados: `.tools/diagnostico-recibido` contiene entrada, referencia, salida anterior, nueva y comparación; `.tools/regresion-oficios-v3` contiene ambas salidas y tasas del código final. Están excluidos de Git y contienen información de los documentos del usuario. Se conserva el archivo original de OneDrive y la carga anterior.

Ficha independiente: **validacion-recibido-v3.jpeg**, UUID `c0efbade-d76b-4f34-8fba-a564aa44221c`. Se procesó mediante el manejador del Job contra FastAPI local actualizado y conserva original, PDF privado, transcripción completa y lectura inicial. En Chrome se guardó la referencia proporcionada y confirmada por el usuario, con nota de procedencia, y se calcularon las métricas por la ruta normal: CER 0,59 % y WER 3,17 %. Se verificaron fecha y los cinco recursos, sin errores JavaScript. Captura privada: `.tools/diagnostico-recibido/revision-v3.png`; reporte: `navegador.json`. La tarea de validación utilizó una cola aislada, sin consumir tareas de otros documentos. El original de OneDrive coincide por SHA-256 con la copia de entrada.

## Verificación y ejecución

**61 pruebas Python aprobadas**, sin omisiones en Windows; **53 pruebas Laravel, 296 aserciones, aprobadas en PostgreSQL aislado**. Las nuevas pruebas cubren el GAD como destinatario, conservación del formato desconocido, detección de texto inferior no leído, corrección de iluminación sin alterar el origen, página vacía y presentación segura de la lectura inicial. Se mantuvieron las pruebas de OCR, PDF, cola, revisión, métricas y eliminación lógica. Permanece el aviso de deprecación del cliente de pruebas httpx ya documentado.

Reiniciar Python y el trabajador Laravel para cargar el código actualizado, y recargar el navegador. Las fichas ya completadas conservan sus extracciones anteriores; las validaciones se guardan como fichas independientes. No se reprocesan automáticamente documentos del usuario.
