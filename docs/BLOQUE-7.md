# Bloque 7 — Métricas y pruebas de calidad

Implementado el 14 de octubre de 2026. Completa los siete bloques del prototipo.

## Uso

1. Reiniciar Python y Laravel para cargar el código actualizado. La migración adicional ya está aplicada en esta instalación.
2. Abrir **Revisar** en un documento completado y cotejar cada página con el original.
3. Corregir y guardar la transcripción de referencia. Después de guardar mediante JavaScript, recargar la página.
4. Marcar la confirmación de revisión y pulsar **Calcular CER y WER**. La confirmación expresa que la referencia fue revisada; el sistema no puede comprobar por sí mismo su corrección humana.
5. Consultar la tabla por resultado principal y variantes OCR disponibles. Los detalles muestran numeradores y denominadores.

Una copia del OCR es únicamente un borrador. No se calculan métricas automáticamente al copiar o guardar. Sin referencia identificada, no vacía y confirmada para el cálculo, no se generan resultados. Las referencias históricas sin autor deben guardarse como una versión identificada antes de evaluar. Las referencias automáticas de pruebas no se consideran mediciones institucionales.

## Cálculo y conservación

Se utiliza **jiwer 4.0.0**, con RapidFuzz como dependencia. Tanto CER como WER son `(sustituciones + eliminaciones + inserciones) / unidades de referencia`. CER cuenta caracteres Unicode, incluyendo los espacios normalizados; WER cuenta palabras separadas por espacios. Son tasas de error: menos es mejor y pueden superar el 100 %. No se convierten en porcentajes de precisión ni se sustituyen por confianza de Tesseract.

La política `nfc-espacios-v1` aplica Unicode NFC, convierte secuencias de espacios/saltos/tabulaciones en un espacio y elimina espacios en los extremos **solo en la copia usada para comparar**. Conserva mayúsculas, tildes, puntuación y números. Los caracteres son puntos de código, no grupos de grafemas. Una hipótesis vacía frente a una referencia válida cuenta como eliminaciones; una referencia vacía se rechaza.

La migración `2026_10_14_000004_add_quality_metrics.php` agrega JSON de métricas, hash SHA-256 de los textos comparados y fecha a cada versión de referencia. Se conserva el motor, versión, política, tasas y conteos. No altera el original, la extracción ni la referencia. Otra versión de referencia no hereda resultados y la vista oculta métricas si la extracción ya no coincide con el hash. Un cambio concurrente durante el cálculo devuelve 409 sin guardar resultados obsoletos. La evaluación vuelve a calcular la versión actual al solicitarla; no existe un historial separado de recálculos de una misma versión.

## Integración y límites

`POST /documentos/{uuid}/calidad` exige sesión, CSRF y como máximo diez solicitudes por minuto. Lee los textos desde PostgreSQL; el navegador envía página, versión y confirmación, nunca rutas ni textos sustitutos. `CalidadDocumentoController` valida el destino HTTP loopback, clave, respuesta y versión antes de persistir.

`POST /evaluar` en FastAPI utiliza la misma autenticación local y bloqueo de exclusión que el OCR. Rechaza cuerpos superiores a 250 000 bytes, más de tres resultados y textos superiores a **10 000 caracteres cada uno**. La recepción tiene un límite de 15 segundos y Laravel espera hasta 20 segundos. Es un cálculo acotado bajo petición, separado de la cola de extracción; si el procesador está ocupado, se informa y se puede reintentar. El bloqueo permanece retenido hasta terminar el cálculo aunque el cliente se desconecte. Los textos se procesan en memoria y no se registran en logs.

Las referencias completas siguen admitiendo 200 000 caracteres; superar el límite de evaluación no las recorta ni modifica. No se añadió un promedio global: para varias páginas se necesitan denominadores y referencias revisadas de todas las páginas que se pretenda evaluar.

## Verificación

Resultado final: **45 pruebas Python aprobadas**, sin omisiones en Windows, y **43 pruebas Laravel con 241 aserciones aprobadas contra PostgreSQL aislado**. La suite Laravel previa a la última prueba de variantes pasó también en SQLite (42 pruebas, 234 aserciones). `pip check`, Pint y las comprobaciones de sintaxis JavaScript pasaron. La migración figura aplicada y las vistas Blade se compilaron correctamente.

Se ejecutaron pruebas de regresión de carga, seguridad, cola, revisión, extracción digital y Tesseract real. La matriz de los diez formatos/escenarios exigidos está en [bloque 4](BLOQUE-4.md#pruebas-realizadas); todas sus muestras son sintéticas.

Las pruebas nuevas cubren tasas y conteos conocidos, equivalencia NFC/espacios, diferencias de mayúsculas/tildes/números, hipótesis vacía, referencia vacía, inserciones superiores al 100 %, autenticación, límites de solicitud, exclusión compartida OCR/evaluación, persistencia por versión, comparación de variantes, rechazo de resultados obsoletos y conservación íntegra de los textos.

Se ejecutó el flujo real en Chrome, Laravel, PostgreSQL y FastAPI con `prueba-sintetica-calidad-bloque7.pdf`: la página fue procesada realmente por el servicio y produjo `hola munda`; la referencia controlada `hola mundo` dio CER 10 % y WER 50 %. Una segunda referencia idéntica dio cero error. Esto comprueba la integración y la fórmula; **no mide la calidad del archivo institucional**. Se verificaron además el bloqueo con borrador modificado, la nueva versión sin tasas heredadas y móvil de 390 × 844 sin desbordamiento ni errores JavaScript. Artefactos locales: `.tools/quality-browser-report.json`, `quality-desktop.png`, `quality-mobile.png` y `resultado-calidad-bloque7.json`.

El script `scripts/test-quality-browser.cjs` requiere Chrome, Playwright y una ficha sintética nueva preparada en `.tools/quality-browser-fixture.json`, además de Laravel en 8011 y Python en 8012. Modifica exclusivamente la referencia de esa ficha de prueba y espera que inicialmente no tenga referencia. No usarlo sobre documentos institucionales. La ejecución normal usa los puertos 8000 y 8002.

La prueba de terminación de procesos Windows requiere ejecutarse fuera del aislamiento de esta herramienta. Se repitió la suite Python completa en ese contexto. El aviso de deprecación de httpx de Starlette afecta al cliente de pruebas, no al servicio de ejecución. No se cambiaron permisos globales del equipo.

## Pendientes y alcance final

Los siete bloques están implementados. Queda realizar una evaluación humana con documentos institucionales representativos: sellos, escaneos deteriorados, tablas y fondos complejos. No se ha medido una precisión institucional ni validado Ubuntu u otros navegadores. No hay una cuota dura de RAM del sistema operativo; se mantienen los límites de páginas, píxeles, texto, concurrencia y tiempo documentados en bloques anteriores. El acceso sigue siendo por operadores locales sin roles departamentales.

Las guías de bloques anteriores son registros de su alcance en esa fecha; sus apartados de funcionalidades futuras quedan superados por los bloques posteriores. La [guía de ejecución e instalación](EJECUCION.md) describe el estado final.

Fuente primaria del cálculo: [JiWER, uso y definiciones](https://github.com/jitsi/jiwer).
