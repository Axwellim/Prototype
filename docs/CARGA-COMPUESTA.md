# Documentos compuestos e invitaciones

Ampliación posterior a la versión 1.0.0: el formulario permite cargar documento, invitación o ambos en un solo registro. Las casillas son editables; Documento está seleccionado inicialmente. Siempre hay un único selector de archivos. No se intenta clasificar automáticamente el diseño.

Nunca quedan ambas casillas desmarcadas: al desmarcar la última opción activa se selecciona la otra. Si ambas están marcadas, el selector recibe primero las partes del documento y luego cambia a invitación única. Si ya se adjuntó una invitación sola y después se activa Documento, el mismo selector recibe las partes del documento. Su título y ayuda indican qué componente se está adjuntando; al completar ambos se bloquea hasta quitar uno. Para ampliar las partes de un documento antes de adjuntar la invitación, mantener seleccionada únicamente la casilla Documento.

## Uso

1. Para un documento, seleccionar un PDF, varias imágenes JPG/PNG o un PDF acompañado de imágenes. Solo se admite un PDF en el documento principal. Se pueden añadir imágenes en varias selecciones y usar Subir/Bajar/Quitar para definir el orden. Las páginas internas de cada PDF mantienen su orden.
2. Para guardar únicamente una invitación, desmarcar Documento y marcar Invitación. Elegir un único PDF o imagen. El selector se bloquea al aceptarlo y se puede habilitar otra vez con Quitar invitación.
3. Para adjuntar ambos, marcar ambas casillas. Al añadir el segundo componente se presenta un modal: una invitación se guarda sin transcripción; un documento se transcribe. Se puede confirmar, cancelar o cerrar el modal con Escape. La advertencia funciona también si primero se seleccionó la invitación.
4. Guardar. El trabajo se realiza en la cola habitual, con un solo procesamiento pesado simultáneo. La carga no espera a que termine el OCR.

El documento se transforma en un único PDF y conserva sus transcripciones por página. La invitación permanece en un PDF separado, asociado al mismo registro; nunca se incorpora a las páginas ni al texto del documento. Una invitación independiente aparece como «Sin transcripción» y no tiene referencias ni métricas OCR. Se puede consultar su PDF desde el historial. La revisión del documento incluye un enlace a la invitación adjunta.

## Archivo de origen y apertura de la revisión

En una carga híbrida se transcriben todas las partes del documento, no solo la primera. La vista previa muestra el PDF unificado completo en un visor continuo, incluidas las páginas procedentes de imágenes y conservando el orden elegido. Abre la primera página del conjunto; no da prioridad al PDF original. Al desplazarse aparecen las demás páginas. Al seleccionar una página o su enlace «Revisar transcripción», el panel derecho muestra su texto y sus referencias. Cada página identifica el archivo de origen. En nuevas cargas el registro utiliza el nombre del PDF principal, si existe.

El visor dibuja progresivamente las páginas próximas al área visible y libera los lienzos que quedan fuera de ella. El zoom se mantiene y la representación de cada página está limitada a seis millones de píxeles. No se cargan simultáneamente todas las páginas como imágenes en memoria. Los originales y la transcripción guardada no se modifican.

El cuadro «Texto extraído automáticamente» reúne la transcripción de todas las páginas en orden, con separadores de página y desplazamiento interno. La referencia editable y sus métricas siguen siendo por página. El botón para copiar como borrador copia únicamente la página seleccionada; al cambiar de variante OCR se actualiza solo esa página dentro del texto completo.

«Ir a página» y «Revisar transcripción» cambian la selección sin recargar la pestaña. Se conserva el PDF cargado y el visor se desplaza a la página elegida; el panel derecho se actualiza con sus variantes OCR, referencia, historial y métricas. La dirección del navegador refleja la selección. El cambio no ejecuta de nuevo el OCR.

Ambos controles desplazan también el cuadro de texto completo hasta el inicio de la transcripción seleccionada. La posición se calcula con el ancho, fuente y ajuste de líneas reales del cuadro; al volver a la primera página se recupera el inicio del texto. La barra de desplazamiento interna se conserva.

Si hay un borrador sin guardar se pide confirmación antes de cambiar de página. Mientras se guarda una referencia se bloquea el cambio, y durante la carga se impide editar el panel que va a sustituirse. Si falla la conexión, se conserva el panel y su contenido; las peticiones anteriores se cancelan al seleccionar otra página. Chrome verificó la navegación de ambos controles sin solicitudes de navegación de pestaña, el guardado en la página correcta, la cancelación de un cambio con borrador y la conservación del contenido tras un error de red simulado.

El servicio comunica cuántas páginas aporta cada componente; Laravel valida la suma y conserva los conteos junto a los metadatos originales. Para cargas anteriores sin esos conteos solo se deduce el origen cuando el total coincide con el número de componentes, de modo que cada uno aporta exactamente una página. En otros casos se muestra igualmente el conjunto completo sin inventar rangos de procedencia. No se sobrescriben transcripciones ni referencias guardadas.

Esta corrección se comprobó con 60 pruebas Laravel y 349 aserciones y navegación real de una carga híbrida desde Chrome, verificando el dibujo de la imagen y del PDF y la transcripción correspondiente al cambiar de página. Las seis pruebas Python de composición verificaron previamente que ambas partes están en el mismo PDF.

## Límites y conservación

- Hasta 19 partes para el documento y una invitación: 20 archivos como máximo, compatibles con el límite PHP habitual de archivos por petición.
- El límite de carga se aplica al conjunto, inicialmente 20 MB. Se reserva un pequeño margen para el contenedor interno; los PDF resultantes mantienen el límite configurado de 40 MB en conjunto.
- Se validan los contenidos y extensiones de cada archivo en el servidor; las reglas no dependen solo de JavaScript. Una segunda invitación, varios PDF en el documento, formatos no admitidos o componentes asociados sin confirmación se rechazan.
- Los originales se conservan privados, con nombre, orden, tamaño y hash. Cuando hay varias partes se almacenan juntos en un contenedor interno sin compresión. El navegador sigue aceptando únicamente PDF/JPG/PNG, no ZIP. La descarga de originales de una composición entrega ese contenedor.
- El servicio Python valida el manifiesto y las entradas internas sin extraer rutas arbitrarias. La composición conserva las capas digitales del PDF y convierte las imágenes en páginas. La invitación pasa por validación y normalización, sin OCR ni extracción de su texto.
- El resultado PDF y la invitación se publican con sus hashes dentro de la misma actualización de la ficha. Los reintentos conservan los originales. La eliminación lógica del historial conserva todos los archivos asociados.

## Instalación y actualización

La migración `2026_10_15_000007_add_composicion_documental` agrega campos opcionales y el tipo de registro. Los registros anteriores siguen siendo documentos. La migración ya se aplicó en este equipo, sin reescribir sus transcripciones ni archivos.

En otra instalación, aplicar las migraciones pendientes antes de usar el formulario:

```powershell
.\scripts\php.cmd .\laravel\artisan migrate
```

Reiniciar Laravel, el servicio Python y el trabajador para cargar los cambios; después recargar el navegador. Las cargas anteriores no se convierten automáticamente en composiciones. No se añadieron dependencias ni modelos de IA.

## Verificación

- 119 pruebas Python aprobadas, incluidas seis nuevas comprobaciones de composición, orden, invitación sin OCR, rechazo de contenedores inválidos y transporte HTTP real.
- 58 pruebas Laravel con 332 aserciones aprobadas en SQLite y en PostgreSQL de pruebas. Incluyen carga compuesta, preservación de originales, límites de tipo, confirmación, invitación independiente sin extracciones, asociación, consulta privada y autenticación. Se repitieron las cinco pruebas específicas después de las últimas comprobaciones de consistencia.
- Chrome real con archivos sintéticos: casillas editables, selección predeterminada, rechazo de dos PDF, reordenación, confirmación/cancelación del modal, bloqueo de invitación única, aviso inverso, carga HTTP, cola, OCR, PDF combinado y consulta. Se verificó que la invitación independiente conserva su PDF byte por byte y cero registros de extracción. También se comprobó móvil de 390 × 844, sin desbordamiento ni errores JavaScript.
- El PDF combinado generado tiene primero la imagen y después el PDF, conforme al orden elegido. La transcripción no contiene el texto de la invitación asociada.

Artefactos privados de navegador en `.tools/composition-browser`: base de pruebas, documentos sintéticos, reporte, captura y PDF resultante. Se utilizaron los puertos temporales 8015/8016, sin detener los servicios normales ni emplear documentos institucionales para estas pruebas.
