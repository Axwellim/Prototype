# Gestión documental — GAD Parroquial Rural de Imantag

Versión **1.0.0**: [alcance y notas de la versión](docs/VERSION-1.0.md).

Oficios de varias páginas: [continuaciones sin membrete ni pie decorativo](docs/OFICIOS-MULTIPAGINA.md).

Convenios de varias páginas: [texto digital, viñetas y bloques de firmantes](docs/CONVENIOS-MULTIPAGINA.md).

PDF con plantilla: [conservar texto digital visible ante fondos decorativos](docs/PDF-CON-FONDO.md).

Formato de transcripción: [reconstrucción de párrafos sin cambiar palabras](docs/PARRAFOS.md).

OCR de imágenes: [encabezados impresos azules y separación de una rúbrica](docs/OCR-ENCABEZADOS-COLOR.md).

OCR actualizado: [lectura de precisión por líneas y normalización documentada de firmantes](docs/OCR-PRECISION.md).

Ajuste de OCR: [plantilla y firmas en dos columnas](docs/OCR-VIALIDAD.md), con protección del cuerpo y límites de lectura bajo sellos.

Corrección de PDF digitales: [ligaduras y codificación de fuentes con verificación óptica](docs/TEXTO-DIGITAL.md).

Actualización: [tratamiento del cierre impreso con firmas superpuestas](docs/OCR-FIRMAS.md), conservando el cuerpo y el OCR completo de respaldo.

Actualización posterior: [documentos recibidos sin plantilla y recuperación de zonas sin lectura](docs/OCR-SIN-PLANTILLA.md), con regresión comprobada sobre ambos oficios reales.

Actualización validada con el primer oficio real: [OCR por regiones, saltos de línea y conservación de página completa](docs/OCR-REGIONES.md).

**Los siete bloques y la digitalización automática están implementados.** Prototipo local con Laravel, PostgreSQL, FastAPI, PyMuPDF y Tesseract en español. Las cargas PDF/JPG/PNG eligen el tratamiento automáticamente y generan un PDF privado con su transcripción por página. Permite revisar el original y guardar referencias humanas independientes con evaluación CER/WER mediante jiwer. Consulta la [ampliación de OCR automático y PDF](docs/DIGITALIZACION-AUTOMATICA.md).

Consulta la [guía vigente de instalación y ejecución](docs/EJECUCION.md) y el [bloque 7: métricas y pruebas](docs/BLOQUE-7.md). Se han contrastado nueve documentos reales usados para ajustar las heurísticas; falta validación independiente con documentos nuevos.

Desde la raíz, ejecutar cada comando en una terminal distinta:

```powershell
.\scripts\procesamiento.cmd
.\scripts\php.cmd .\laravel\artisan serve --host=127.0.0.1 --port=8000
.\scripts\cola-documentos.cmd
```

Abrir http://127.0.0.1:8000. Reiniciar las instancias anteriores para cargar los cambios. La base y el operador ya están configurados en este equipo; no recrearlos. Las credenciales y claves están en archivos privados excluidos de Git.

```text
laravel/              Aplicación, modelos, migraciones, cola, vistas y pruebas PHP
procesamiento/app/    Extracción digital, OCR, API local y métricas jiwer
procesamiento/tests/  Pruebas con documentos sintéticos y Tesseract real
scripts/              Lanzadores Windows y pruebas de navegador
config/php/           Extensiones PHP locales del proyecto
docs/                 Instalación, decisiones, pruebas y limitaciones por bloque
```

Historial de implementación: [1: entorno](docs/BLOQUE-1.md), [2: carga segura](docs/BLOQUE-2.md), [3: FastAPI](docs/BLOQUE-3.md), [4: OCR](docs/BLOQUE-4.md), [5: cola](docs/BLOQUE-5.md), [6: revisión](docs/BLOQUE-6.md), [7: calidad](docs/BLOQUE-7.md). Las restricciones de alcance de cada registro histórico describen ese bloque, no el estado final del sistema.

## Registro histórico original del bloque 1

El contenido siguiente se conserva sin actualizar como evidencia de la inspección inicial; la guía vigente está enlazada arriba.

---

# Bloque 1 — Inspección y configuración del entorno

Fecha de inspección: 14 de octubre de 2026. Alcance: exclusivamente bloque 1.

## Resultado de la inspección

El directorio estaba vacío, sin Laravel, archivos existentes ni instrucciones AGENTS.md encontradas en el proyecto o sus directorios padre inspeccionados.

| Componente | Resultado real |
| --- | --- |
| PHP | XAMPP, C:\xampp\php\php.exe, 8.2.12; no está en PATH |
| php.ini | C:\xampp\php\php.ini; no se modificó |
| Extensiones | fileinfo, mbstring, OpenSSL, PDO y XML disponibles. zip, pdo_pgsql y pgsql funcionan al activarlas mediante el lanzador local |
| Composer | Instalado localmente: 2.10.3; instalador verificado mediante SHA-384 oficial |
| Laravel | Plantilla 12.12.2; framework instalado 12.70.0; versiones fijadas en composer.lock |
| PostgreSQL | psql 18.6; servicio postgresql-x64-18 activo; pg_isready confirma que 127.0.0.1:5432 acepta conexiones |
| Base y usuario de aplicación | No creados; credenciales y consulta SQL autenticada pendientes |
| Python / py | No encontrados en PATH ni en ubicaciones habituales inspeccionadas; no se afirma ausencia absoluta en el equipo |
| Dependencias Python | No verificables sin intérprete localizado |
| Tesseract / spa | No encontrados en PATH ni en ubicación habitual; instalación e idioma sin verificar |
| Node / npm | 24.21.0 / 11.19.0; no se instalaron paquetes frontend |
| Límites PHP actuales | upload_max_filesize=40M, post_max_size=40M, memory_limit=512M, max_execution_time=120 |

Laravel 12 admite PHP 8.2; Laravel 13 requiere PHP 8.3. Se eligió Laravel 12 para reutilizar PHP disponible. Según la política oficial, Laravel 12 recibe correcciones de seguridad hasta el 24/02/2027: planificar actualización de PHP y Laravel antes del despliegue definitivo. PHP 8.2.12 es una revisión antigua: actualizar a una revisión mantenida antes de producción.

## Estructura preparada

```text
Prototype/
  .htaccess                Bloqueo del acceso directo por Apache a esta raíz
  composer.phar            Herramienta local, ignorada por Git
  .tools/                  Caché/configuración local de Composer, ignorada
  scripts/
    php.cmd                PHP con zip y controladores PostgreSQL
    composer.cmd           Composer local
    php.ps1                Alternativa PowerShell (depende de su política)
    composer.ps1           Alternativa PowerShell (depende de su política)
  laravel/
    app/ bootstrap/ config/ routes/ resources/ public/
    database/migrations/   Solo migraciones originales de Laravel, sin ejecutar
    storage/ tests/ vendor/
    composer.json composer.lock
    .env.example           Configuración de ejemplo sin secretos
    .env                   Configuración local con APP_KEY generada, ignorada
  README.md
```

La interfaz actual es únicamente la bienvenida original de Laravel. No hay carga, OCR, autenticación del módulo ni servicio Python. No se han creado tablas, usuarios de base de datos, enlaces públicos de almacenamiento ni trabajadores.

Se configuraron español, America/Guayaquil, URL local, PostgreSQL y cola database. Sesiones y caché usan archivos provisionalmente para comprobar el arranque sin tablas. La cola no debe iniciarse hasta el bloque correspondiente. No usar composer run setup: la plantilla ejecutaría migraciones y preparación frontend fuera del alcance autorizado. No usar composer run dev: inicia servicios adicionales.

## Comandos para comprobar este bloque en Windows

Desde PowerShell, en C:\xampp\htdocs\Prototype:

```powershell
.\scripts\php.cmd --version
.\scripts\composer.cmd --version
.\scripts\composer.cmd check-platform-reqs --working-dir=laravel
.\scripts\php.cmd .\laravel\artisan about --only=environment,cache,drivers
.\scripts\php.cmd .\laravel\artisan route:list
Set-Location .\laravel
..\scripts\php.cmd vendor\bin\phpunit
..\scripts\php.cmd artisan serve --host=127.0.0.1 --port=8000
```

Abrir http://127.0.0.1:8000 y comprobar la bienvenida de Laravel; /up debe responder HTTP 200. Detener con Ctrl+C. Las pruebas ejecutadas verificaron la respuesta de bienvenida mediante el cliente HTTP interno de Laravel; no se realizó inspección visual en navegador.

Usar los lanzadores .cmd: la política actual de PowerShell impide ejecutar los .ps1. No es necesario cambiar esa política. Si PHP está en otra ubicación, definir $env:IMANTAG_PHP con la ruta a php.exe. El lanzador carga extensiones para este proceso; Apache no hereda estos parámetros. En una futura configuración Apache se debe apuntar DocumentRoot exclusivamente a laravel/public y habilitar sus extensiones PHP. La raíz del proyecto está bloqueada mediante .htaccess para evitar servir código o secretos por XAMPP; comprobar AllowOverride en la configuración de Apache. Para este bloque utilizar artisan serve en loopback.

## Dependencias pendientes para los siguientes bloques

1. Instalar Python 3.12 de 64 bits desde https://www.python.org/downloads/windows/ con pip y launcher py; verificar `py -3.12 --version` y `py -3.12 -m pip --version`. No se instaló globalmente desde esta sesión.
2. Preparar posteriormente un entorno aislado con `py -3.12 -m venv .venv`. La lista prevista es fastapi, uvicorn, python-multipart, PyMuPDF, pytesseract, Pillow, opencv-python-headless y jiwer; requirements.txt y versiones comprobadas se entregarán al implementar Python, no se afirma que estén instaladas.
3. Instalar Tesseract para Windows siguiendo los enlaces del proyecto oficial: https://tesseract-ocr.github.io/tessdoc/Installation.html . Instalar el idioma español. Comprobar con `tesseract --version` y `tesseract --list-langs`; debe aparecer spa. Si no está en PATH, usar la ruta completa al ejecutable. Los datos oficiales están en https://github.com/tesseract-ocr/tessdata ; no utilizar OCR en nube.
4. PostgreSQL ya existe: no reinstalar. En el bloque 2 crear un rol exclusivo sin privilegios administrativos y una base del proyecto, introducir credenciales solo en laravel/.env y verificar una consulta autenticada. No se solicitaron ni almacenaron contraseñas de administrador.
5. Bootstrap 5 se instalará localmente durante la interfaz, sin CDN para el funcionamiento LAN sin Internet.

Los límites definitivos del módulo (20 MB, máximo de páginas, tiempos, memoria y concurrencia de un trabajador) se configurarán al implementar sus componentes. Los 40 MB actuales de PHP permiten el futuro límite de aplicación de 20 MB; la validación del módulo aún no existe.

## Pruebas realizadas y pendientes

Realizadas: verificación SHA-384 del instalador Composer; instalación completa con composer.lock; Composer check-platform-reqs sin errores; descubrimiento de paquetes; generación de APP_KEY; artisan --version, about y route:list; pg_isready; dos pruebas originales PHPUnit con dos aserciones, ambas correctas. Composer informó que no encontró avisos de vulnerabilidad durante la instalación.

La primera ejecución PHPUnit dentro del aislamiento falló por permisos de escritura en registros/caché. Se repitió con autorización fuera del aislamiento y pasó; no se cambiaron permisos globales.

Pendientes: acceso autenticado a PostgreSQL, Python y sus bibliotecas, Tesseract y spa, revisión visual, pruebas de archivos y las diez pruebas documentales requeridas. Ningún PDF o imagen ha sido procesado. No hay métricas de calidad calculadas.

## Compatibilidad futura con Ubuntu

Conservar Laravel y el futuro servicio Python como componentes separados. En Ubuntu usar PHP compatible y extensiones pgsql/zip, Composer, PostgreSQL, python3-venv y tesseract-ocr con tesseract-ocr-spa. Ejecutar PHP directamente (los .cmd son auxiliares exclusivos de Windows). FastAPI deberá escuchar solo en 127.0.0.1. La instalación y las pruebas en Ubuntu están pendientes.

## Fuentes oficiales

- Compatibilidad y soporte: https://laravel.com/docs/12.x/releases
- Verificación del instalador: https://getcomposer.org/doc/faqs/how-to-install-composer-programmatically.md
- Controlador PostgreSQL: https://www.php.net/manual/en/ref.pdo-pgsql.php

Se detiene el trabajo al terminar este bloque. El bloque 2 requiere confirmación expresa del usuario, tal como indica la solicitud original.
