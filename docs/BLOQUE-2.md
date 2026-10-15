# Bloque 2 — Base de datos y carga privada

Implementado y verificado el 14 de octubre de 2026. Se detiene antes de FastAPI, PyMuPDF y OCR.

## Qué quedó listo

- Base PostgreSQL `imantag_documental`, propiedad del rol `imantag_app`, sin permisos de superusuario, creación de bases ni creación de roles. La clave aleatoria está únicamente en `laravel/.env`; no se utiliza el administrador desde Laravel.
- Migraciones originales conservadas y ejecutadas, más la migración `2026_10_14_000001_create_documental_tables.php`: `documentos_prueba`, `extracciones_documento`, `evaluaciones_ocr`. UUID único, índices por hash, fecha y estado, claves foráneas que impiden borrar documentos con resultados; una extracción por página. Las evaluaciones y extracciones se conservan separadas.
- Modelos `DocumentoPrueba`, `ExtraccionDocumento`, `EvaluacionOcr` con relaciones Eloquent.
- Acceso mediante usuarios locales de Laravel, contraseña con hash, sesión regenerada al ingresar, invalidada al salir, CSRF y límite de intentos. No hay registro público. Todos los operadores habilitados pueden consultar el listado y cargar documentos; no hay roles ni autorización departamental en esta fase.
- Blade y Bootstrap 5.3.8 servido desde `public/vendor/bootstrap`, licencia MIT incluida y hash SHA-384 contrastado con documentación oficial. No requiere CDN, npm ni Vite al ejecutar.
- Selección y arrastre de un documento por solicitud, progreso real de transferencia, mensajes de validación, listado paginado.
- Carga PDF/JPG/JPEG/PNG con contenido identificado por fileinfo y extensión coherente. Las imágenes se decodifican con GD después de comprobar dimensiones (máximo 25 millones de píxeles configurable). El PDF exige cabecera y marcador final válidos.
- UUID, hash SHA-256, nombre original saneado, extensión de almacenamiento normalizada, tamaño, fecha, estado pendiente. Las imágenes registran una página; PDF queda con páginas desconocidas hasta el parser.
- Archivos fuera de `public`, en `laravel/storage/app/documentos/originales/<uuid>.<extensión>`. Disco independiente sin rutas automáticas ni enlaces públicos. Se desactivaron las rutas automáticas del disco local de la plantilla. El navegador no elige rutas ni estados.
- Si falla la escritura en base de datos se limpia solamente el archivo nuevo de esa carga. Se registra el error y se responde con un mensaje público sin detalles internos.
- Páginas de error comunes en español.

## Cómo abrirlo

Detener el servidor anterior con Ctrl+C y reiniciarlo desde la raíz del proyecto:

```powershell
.\scripts\php.cmd .\laravel\artisan serve --host=127.0.0.1 --port=8000
```

Abrir http://127.0.0.1:8000 . La raíz redirige al módulo y solicita ingreso.

Las credenciales del operador inicial están en `.tools/acceso-inicial.txt`, fuera de `public`, excluido de Git y protegido del acceso directo por Apache mediante el bloqueo de la raíz. No se imprimieron en registros ni en la documentación. Para crear una cuenta personal, ejecutar desde la raíz:

```powershell
.\scripts\php.cmd .\laravel\artisan documentos:crear-operador
```

La contraseña se solicita oculta, debe repetirse y tener al menos 12 caracteres. No hay credenciales predefinidas en el código. El comando no sobrescribe cuentas existentes.

Los lanzadores ahora usan `PHP_INI_SCAN_DIR` y `config/php/extensions.ini` para cargar zip, pdo_pgsql, pgsql y GD también en los procesos hijos de `artisan serve`; no se cambió el php.ini global. Para Ubuntu instalar esas extensiones mediante paquetes del sistema; el código del módulo no depende de rutas Windows.

Se ejecutaron ya las migraciones. Para una copia nueva, crear primero la base y el usuario exclusivos, configurar `.env` y ejecutar:

```powershell
.\scripts\php.cmd .\laravel\artisan migrate --no-interaction
```

No usar `migrate:fresh` sobre la base de aplicación. No iniciar trabajadores: todavía no existen tareas de procesamiento y cargar un archivo no despacha OCR.

## Qué comprobar en el navegador

1. Sin sesión, `/documentos` solicita ingreso.
2. Ingresar con la cuenta local y cargar un PDF o una imagen válida.
3. Observar el progreso y, tras guardar, su fila en el listado con estado **Pendiente**.
4. Una imagen muestra una página; PDF muestra **Por determinar**. Método y tiempo muestran **Sin extracción**, sin resultados inventados.
5. Probar un archivo de texto renombrado a `.pdf`: debe rechazarse.
6. Cerrar sesión: el listado deja de ser accesible.

Se dejó una imagen sintética de verificación HTTP llamada `prueba-carga-bloque2.png` (UUID `5379edbe-fddf-43d8-95df-c2f13f75c224`), conservada en almacenamiento privado. No es un documento institucional ni una prueba de OCR.

## Configuración

En `laravel/.env`:

```dotenv
DOCUMENTOS_MAX_UPLOAD_KB=20480
DOCUMENTOS_MAX_IMAGE_PIXELS=25000000
```

20 MB es el límite inicial de aplicación. Los límites PHP de XAMPP comprobados son 40 MB para archivo y solicitud. Si se modifican los valores, mantener post_max_size superior al límite de archivo más el sobrecoste multipart, y reiniciar el servidor. Ejecutar `artisan config:clear` si había configuración en caché.

El servicio actual escucha solo en loopback. Antes de habilitar acceso LAN, configurar HTTPS y cookies seguras (`SESSION_SECURE_COOKIE=true`); no enviar credenciales por una conexión LAN HTTP. Para Apache usar exclusivamente `laravel/public` como DocumentRoot y habilitar extensiones en su configuración PHP propia.

## Pruebas ejecutadas

```powershell
# SQLite en memoria: no toca PostgreSQL de aplicación
Set-Location .\laravel
..\scripts\php.cmd vendor\bin\phpunit
Set-Location ..

# PostgreSQL aislado, ya preparado en esta máquina
.\scripts\php.cmd .\scripts\test-postgres.php
```

Ambas ejecuciones: **13 pruebas, 87 aserciones, todas correctas**. La suite PostgreSQL usa exclusivamente `imantag_documental_test`, creada separadamente y propiedad de `imantag_app`; no usa la base de aplicación. Esta base de pruebas se reinicializa al ejecutar la suite: nunca almacenar documentos reales allí. Para otro equipo, crear explícitamente esa base de pruebas antes de ejecutar el script. El script fija su nombre y comprueba la conexión.

Cobertura: PNG, JPG y JPEG generados y decodificados realmente, PDF sintético válido de una página, persistencia y hash, estado pendiente, rutas controladas por servidor, ausencia de acceso público, archivos falsos/truncados, extensión incompatible, tamaño y píxeles, limpieza tras fallo simulado conservando archivos anteriores, relaciones y separación de referencia/extracción, acceso anónimo, login/logout y límite de intentos.

Además se comprobó mediante HTTP real: redirección de invitado, formulario, respuesta 419 sin CSRF, login contra PostgreSQL, listado autenticado, carga multipart con respuesta 201, logout y revocación de acceso. Las credenciales se leyeron localmente sin mostrarlas. No se realizó revisión visual automatizada ni captura de navegador.

Los intentos dentro del aislamiento del agente encontraron restricciones de escritura en sesiones, vistas, archivos de prueba y logs. La suite PostgreSQL y el servidor HTTP de verificación se repitieron con autorización fuera del aislamiento, sin alterar permisos globales.

## Límites y próximos bloques

- PDF tiene validación preliminar, no validación completa de objetos internos, páginas, cifrado o contenido malicioso. Un PDF con cabecera y final válidos pero objetos corruptos aún podría guardarse como pendiente. La validación profunda se implementará con PyMuPDF en el bloque 3 antes de procesarlo. No se ofrece vista previa ni descarga del original en este bloque.
- El máximo de páginas queda pendiente del parser. El tamaño y píxeles sí se limitan ahora.
- El máximo de píxeles reduce el consumo de decodificación; no representa una garantía contra todo archivo adversario. Los originales se conservan sin filtros ni ejecución.
- Ante la terminación abrupta del proceso entre escritura y registro podría quedar un archivo huérfano; no existe todavía una tarea de conciliación y no se borran documentos automáticamente.
- Todavía no hay FastAPI, extracción digital, OCR, consulta de progreso de procesamiento, reintentos, revisión, CER ni WER. Los estados se preparan en el esquema; las cargas únicamente generan `pendiente`.
- Las diez pruebas documentales de extracción del proyecto siguen pendientes. Esta suite comprueba la carga, no el reconocimiento de texto.

Fuentes oficiales consultadas: [validación Laravel](https://laravel.com/docs/12.x/validation), [descarga Bootstrap y hash oficial](https://getbootstrap.com/docs/5.3/getting-started/download/).
