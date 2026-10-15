# Historial de documentos y eliminación

El listado tiene una altura de 32 rem (512 px con la fuente predeterminada), limitada a 65 % de la altura de la ventana en pantallas pequeñas. Tiene desplazamiento interno vertical/horizontal y encabezado fijo. Conserva la paginación de 15 documentos; el panel no crece al añadir filas.

Para retirar un documento, marcar **Retirar del historial** y pulsar **Eliminar**. La confirmación es obligatoria y funciona también sin JavaScript. Es eliminación lógica: el registro recibe `deleted_at`, deja de aparecer en el listado y sus enlaces del módulo dejan de ser accesibles. Los archivos originales, PDF, transcripciones, referencias y métricas se conservan. No hay todavía una interfaz de papelera o restauración ni borrado físico.

La acción requiere sesión, CSRF y está limitada a veinte solicitudes por minuto. Todos los operadores actuales tienen el mismo acceso provisional. No se permite retirar un documento mientras esté procesándose; el servidor verifica ese estado dentro de una transacción con bloqueo. Una tarea pendiente retirada se omite cuando el trabajador actualizado intenta ejecutarla.

La migración `2026_10_14_000006_add_document_soft_deletes.php` ya se aplicó en este equipo y las vistas se compilaron. Reiniciar el trabajador Laravel al terminar su tarea actual para cargar el modelo actualizado. Para otra instalación, aplicar `artisan migrate` antes de usar esta versión.

Verificado: **51 pruebas Laravel y 286 aserciones aprobadas en PostgreSQL de pruebas**. Incluyen confirmación, acceso autenticado, conservación de archivos/textos, bloqueo de procesamiento y omisión de tareas retiradas. Chrome comprobó altura de 512 px, scroll interno, confirmación y altura constante al reducir las filas visibles. Captura local: `.tools/historial-fijo.png`. La comprobación visual no eliminó registros de la base de aplicación.
