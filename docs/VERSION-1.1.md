# Versión 1.1.0

Esta versión amplía la carga de documentos y facilita revisar todas sus páginas sin recargar la pestaña.

- Documento compuesto por un PDF, varias imágenes o un PDF y varias imágenes, con orden editable y un único PDF resultante. Se transcriben todas las páginas del documento.
- Invitación independiente o asociada, limitada a un archivo PDF o imagen, conservada como PDF sin transcripción.
- Casillas editables, documento seleccionado por defecto, un único selector visible y avisos antes de incorporar el segundo componente.
- Conservación privada de los originales, su orden y sus hashes; validaciones de archivos y límites en el servidor.
- Vista previa continua del conjunto y texto completo con desplazamiento interno. La página elegida sincroniza el visor y la transcripción; referencias y métricas permanecen por página.
- Navegación sin recargar, protección de borradores y barra de rutas compacta.

Los detalles de uso, límites, pruebas y actualización están en [CARGA-COMPUESTA.md](CARGA-COMPUESTA.md). La instalación general está en [EJECUCION.md](EJECUCION.md).

## Actualización

Aplicar las migraciones pendientes y reiniciar Laravel, el servicio Python y el trabajador. La migración `2026_10_15_000007_add_composicion_documental` conserva los registros anteriores. No se añadieron dependencias ni modelos de IA.

```powershell
.\scripts\php.cmd .\laravel\artisan migrate
```

## Alcance de la validación

La comprobación final aprobó 60 pruebas Laravel con 349 aserciones y 119 pruebas Python, además de la revisión de sintaxis JavaScript. También se realizaron comprobaciones de navegador con documentos sintéticos para carga híbrida, invitaciones, orden de páginas, navegación y protección de referencias.

Las pruebas realizadas por el usuario con documentos de las comisiones han producido transcripciones coherentes; aún pueden aparecer errores de OCR o saltos de línea. Queda pendiente una segunda ronda con documentos nuevos cuando estén disponibles. Esta versión no acredita precisión perfecta ni sustituye esa evaluación independiente.

Configuraciones locales, credenciales, documentos institucionales cargados, bases de datos y artefactos privados de pruebas quedan excluidos del repositorio.

Identificador de versión: `1.1.0`. Etiqueta Git: `v1.1.0`.
