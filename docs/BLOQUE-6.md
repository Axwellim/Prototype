# Bloque 6 — Interfaz de revisión documental

Implementado y verificado el 14 de octubre de 2026. Alcance: revisar originales y texto por página, guardar referencias humanas por separado y consultar el texto completo. No se implementan métricas todavía.

## Cómo utilizarlo

1. Abrir Laravel en http://127.0.0.1:8000 e ingresar con la cuenta local.
2. En un documento **Completado**, pulsar **Revisar**. El botón aparece también cuando la consulta de estados detecta que acaba de completarse.
3. Usar **Anterior**, **Siguiente** o **Ir a página**. El original y el texto mostrado corresponden a la misma página.
4. Ajustar el original con **−**, **+** y **Ajustar**. El zoom va del 50 % al 200 % respecto al ancho del panel, no a un tamaño físico de impresión.
5. Si hay variantes OCR, elegir **Sin filtros adicionales** o **Con preprocesamiento** para compararlas. La extracción automática es de solo lectura.
6. Introducir una transcripción corregida. Si el campo está vacío, **Copiar resultado como borrador** permite usar explícitamente el resultado seleccionado como punto de partida. Revisarlo antes de guardar; no se crea una referencia automáticamente.
7. Guardar con **Guardar transcripción de referencia**. Se confirma el guardado sin recargar la página y se conserva la extracción original.
8. **Ver texto completo** muestra la extracción automática de todas las páginas, en orden y con separación visible. Las referencias humanas se consultan en cada página.

Si Laravel no está iniciado, desde la raíz:

```powershell
.\scripts\php.cmd .\laravel\artisan serve --host=127.0.0.1 --port=8000
```

Para revisar documentos ya completados no hace falta tener Python ni la cola ejecutándose. Para cargar y procesar documentos nuevos siguen siendo necesarias las tres terminales del [bloque 5](BLOQUE-5.md). Si el navegador conserva archivos antiguos, actualizar con Ctrl+F5.

## Interfaz

En escritorio hay dos paneles: original a la izquierda y extracción/referencia a la derecha. En pantallas estrechas se apilan. El PDF se renderiza página por página en canvas con PDF.js; las imágenes usan el original autenticado. Hay una alternativa **Abrir original en otra pestaña** si el navegador no puede mostrarlo dentro del panel.

PDF.js 6.4.299 se sirve completamente desde `laravel/public/vendor/pdfjs`, incluidos worker, fuentes, CMaps y WASM, con licencia Apache 2.0 incluida. No hay CDN ni una dependencia de npm/Vite para ejecutar la aplicación. Se desactiva evaluación de código y XFA en el renderizador; no se implementa ejecución de acciones JavaScript del PDF ni formularios PDF interactivos.

El canvas se limita aproximadamente a seis millones de píxeles y el factor de densidad a 2 para reducir consumo. Si se alcanza el límite se informa que se limitó la resolución. Esto no constituye una cuota dura de memoria para todo el navegador o su parser PDF.

La selección de zoom se conserva en la pestaña mediante sessionStorage, usando solo el UUID y la preferencia de zoom. Los borradores y textos documentales no se guardan en almacenamiento local del navegador.

## Referencias, historial y conflictos

Cada guardado con cambios crea una nueva fila en `evaluaciones_ocr`. Se conserva el historial anterior, con usuario y fecha; guardar el mismo contenido y observaciones sobre la versión actual no duplica la fila. La referencia actual es la versión más reciente de esa página. Las evaluaciones preexistentes con `numero_pagina=NULL` se conservan y no se sustituyen por referencias de página.

Se añadió una migración independiente, `2026_10_14_000003_add_reference_author.php`, con autor opcional `usuario_id` e índice para consultar versiones por página. Está aplicada en esta máquina. No se recrearon tablas ni se eliminaron referencias existentes. Si se elimina una cuenta por administración de base de datos, el texto permanece y su autor queda vacío.

El formulario envía el identificador de la versión que se cargó al abrir la página. Si otro operador guardó entretanto, el servidor devuelve **409** y conserva el borrador del operador que recibe el conflicto. Hay que conservar ese borrador y recargar para comparar antes de guardar de nuevo. Un bloqueo de fila serializa los guardados de una misma ficha documental.

JavaScript avisa al abandonar una página con cambios sin guardar, incluyendo navegación a otra página del documento. La advertencia depende del navegador y no es un autoguardado: un cierre forzado o un fallo del equipo puede perder el borrador. Los fallos de sesión, red o validación muestran un mensaje y mantienen los campos editables.

Tras guardar se actualizan autor y fecha, y aparece **Actualizar historial** para consultar las nuevas versiones. Si se editó durante la petición, se informa que hay cambios posteriores sin guardar. La selección de otra variante OCR no reemplaza una transcripción ya introducida.

El límite inicial es `DOCUMENTOS_MAX_REFERENCE_CHARS=200000`, incluido en los ejemplos de configuración; las observaciones admiten 10 000 caracteres. Se rechazan referencias vacías o compuestas solo por espacios. Se exceptúan ambos campos del recorte automático de espacios de Laravel para preservar la transcripción recibida. El navegador representa los saltos de línea del textarea como LF; el guardado AJAX usa JSON para evitar una conversión adicional a CRLF. Esta representación no modifica los textos automáticos almacenados. Sin JavaScript se mantiene el guardado HTML con su codificación habitual de formularios.

## Acceso seguro al original

Nuevas rutas, todas bajo autenticación:

| Ruta | Función |
| --- | --- |
| `GET /documentos/{uuid}/revision?pagina=N` | Revisión y referencia de la página |
| `GET /documentos/{uuid}/original` | Original privado para el visor autenticado |
| `GET /documentos/{uuid}/texto` | Texto automático completo |
| `POST /documentos/{uuid}/referencia` | Guardado de una versión humana con CSRF |

No se acepta una ruta de archivo enviada por el navegador. El controlador reconstruye la ubicación desde UUID y extensión, comprueba que coincida con el registro, resuelve su ruta dentro del disco privado y verifica tamaño y SHA-256. Un original ausente, alterado o fuera de la raíz no se sirve.

Se usan tipos MIME explícitos, `nosniff` y caché privada sin almacenamiento. El PDF admite solicitudes Range para el visor, sin saltarse la autenticación. Los originales no se copiaron a `public`, no se creó un enlace de almacenamiento y no se cambió la clave Python ni se expone en el visor. El nuevo JavaScript solo recibe datos de esa página, URLs locales y versiones de referencia.

Un documento pendiente, procesando o con error muestra un mensaje y un enlace al listado. No se guarda una referencia ni se sirve la vista previa antes de completarse la extracción. Los números de página inexistentes se rechazan. El HTML de documentos y referencias se escapa tanto en vistas como al construir datos JSON.

El mecanismo de acceso sigue siendo el del bloque 2: todos los operadores locales habilitados pueden revisar documentos. No se añadieron roles, clasificación por departamentos ni permisos documentales adicionales.

## Archivos principales

- `app/Http/Controllers/RevisionDocumentoController.php`: revisión, original privado, texto completo y versiones de referencia.
- `app/Models/EvaluacionOcr.php`: relación con el usuario que guardó la referencia.
- `database/migrations/2026_10_14_000003_add_reference_author.php`: autor e índice, sin pérdida de datos.
- `resources/views/documentos/revision.blade.php`: paneles, controles, variantes y referencia.
- `resources/views/documentos/texto.blade.php`: texto completo ordenado.
- `resources/views/documentos/sin-resultados.blade.php`: estado previo a la revisión.
- `public/revision.js`: PDF.js, zoom, borradores, variantes y guardado AJAX.
- `public/documentos.js` y listado: enlace Revisar al completarse un documento.
- `public/vendor/pdfjs`: distribución local y licencia.
- `tests/Feature/RevisionDocumentoTest.php`: pruebas nuevas de backend.
- `scripts/test-revision-browser.cjs`: comprobaciones de navegador con Playwright.

En una instalación nueva ejecutar migraciones con `artisan migrate`, como en los bloques anteriores. No usar `migrate:fresh` en la base de aplicación. La dependencia del visor ya está incluida como archivos estáticos; no es necesario instalar Node para ejecutar Laravel o revisar documentos.

## Pruebas realizadas

Backend:

```powershell
Set-Location .\laravel
..\scripts\php.cmd vendor\bin\phpunit
Set-Location ..
.\scripts\php.cmd .\scripts\test-postgres.php
```

Resultado final: **38 pruebas y 212 aserciones aprobadas en SQLite y PostgreSQL**, incluido todo lo anterior. Se ejecutaron Pint sobre PHP modificado, comprobación de sintaxis de ambos archivos JS, compilación Blade y comprobación del estado de migraciones.

Cobertura nueva: acceso autenticado, página seleccionada, escape de HTML, original privado con MIME y caché adecuados, Range, ruta o hash alterados, conservación de espacios, autor, extracción intacta, historial, guardado idéntico, edición concurrente, referencia vacía/larga, página inexistente, documento no completado, texto completo ordenado y guardado sin JavaScript.

Chrome real, mediante Playwright 1.64.1 y una instancia temporal de Laravel en 8011:

- Login y enlace Revisar en el listado.
- PDF renderizado en canvas, navegación sincronizada y zoom.
- Extracción de solo lectura y selección de variante OCR.
- Copia explícita como borrador en la primera ejecución, sin guardado automático.
- Advertencia antes de abandonar cambios pendientes.
- Guardado con CSRF, persistencia exacta de la transcripción tras recargar y rechazo 419 sin token.
- Dos pestañas: rechazo 409 de la segunda edición y conservación de su borrador.
- Texto completo separado de la referencia.
- Vista previa y zoom de PNG.
- Escritorio 1600×1100 y móvil 390×844, sin desbordamiento horizontal.
- Sin errores JavaScript ni solicitudes a orígenes externos durante la revisión.

Se inspeccionaron visualmente las capturas de escritorio y móvil. Los artefactos están en `.tools/revision-desktop.png`, `.tools/revision-mobile.png` y `.tools/revision-browser-report.json`. JPEG está admitido por el controlador y el visor de imágenes; la comprobación de navegador de este bloque utilizó PNG, no se afirma una prueba visual JPEG adicional.

La primera compilación de la vista detectó una expresión compleja incompatible con `@json`; se movió la preparación de datos al controlador y las pruebas posteriores pasaron. Las comprobaciones de navegador detectaron también la diferencia de finales de línea CRLF/LF de los textarea, corregida en el guardado y seguimiento de borradores.

El aislamiento bloqueó el almacenamiento de sesiones del servidor temporal. Se repitieron el servidor de prueba y los controles finales con autorización fuera del sandbox, sin cambiar permisos globales. La instancia temporal se detuvo al terminar. No se detuvieron los servidores anteriores del usuario.

Para repetir las pruebas Chrome en esta máquina, iniciar Laravel en 8011 y ejecutar desde la raíz:

```powershell
# Dependencias opcionales solo para estas pruebas; ya están instaladas aquí.
npm.cmd install --prefix .tools/revision-web --save-exact --ignore-scripts pdfjs-dist@6.4.299 playwright@1.64.1
node .\scripts\test-revision-browser.cjs
```

El script usa Chrome instalado en `C:\Program Files\Google\Chrome\Application\chrome.exe`, las credenciales privadas locales y los UUID de `.tools/review-browser-fixtures.json`. Es una prueba local preparada para esta instalación, no un alta de datos institucionales. Repetirla crea otra versión de referencia únicamente en su ejemplo sintético. Para otro equipo se deben preparar sus cuentas/ejemplos y ajustar la ruta del navegador; las pruebas PHPUnit generan sus propias muestras sin esa preparación.

## Ejemplos conservados

Se crearon fichas independientes para las pruebas de revisión, copiando originales y resultados reales sintéticos de los bloques anteriores, sin volver a ejecutar OCR ni modificar las fichas fuente:

- `prueba-revision-bloque6-pdf.pdf`, UUID `f784276c-fc65-47eb-9ff6-e9c9c68db62a`: PDF mixto con dos páginas y variantes OCR. La referencia de prueba está solo en la página 2 y lleva observaciones que la identifican como prueba automatizada, no evaluación institucional.
- `prueba-revision-bloque6-imagen.png`, UUID `ba81deb4-fdbf-4572-95f1-8b0b43808756`: muestra PNG para el visor.

La verificación final en PostgreSQL confirmó que originales, extracción y variantes de las fichas de revisión coinciden con los resultados fuente y que las referencias se atribuyeron solo a la página revisada. No se añadieron referencias a documentos institucionales.

## Limitaciones y siguiente bloque

- No hay CER ni WER, porcentajes de precisión o evaluación automática de calidad. Las referencias están preparadas para el bloque 7.
- No hay rotación manual del visor, corrección del original, anotaciones PDF ni edición de la extracción. El zoom solo afecta a la vista.
- Se verificó Chrome en Windows; otros navegadores y Ubuntu siguen pendientes. Se necesita un navegador moderno con módulos JavaScript para PDF.js. Sin JavaScript funcionan el texto, la navegación y el guardado básico, pero el PDF debe abrirse con el enlace al original y no hay zoom integrado.
- Una vista previa de PDF complejo puede fallar aunque la extracción exista; se informa y se mantiene la alternativa de abrir el original. Los límites de canvas no son una garantía sobre toda la memoria del parser.
- Los borradores no se guardan automáticamente. El historial de referencias se conserva, pero no existe una acción de restauración automática de una versión anterior.

Referencia técnica oficial del visor: [ejemplos PDF.js](https://mozilla.github.io/pdf.js/examples/).
