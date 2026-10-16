# Instalación y ejecución en Windows

Ampliación de carga: [documentos compuestos e invitaciones](CARGA-COMPUESTA.md). La migración `000007` ya está aplicada en este equipo. Reiniciar Laravel, Python y el trabajador antes de usar el nuevo formulario.

OCR v3: [distinción entre membrete y destinatario, y recuperación de iluminación](OCR-SIN-PLANTILLA.md). Reiniciar Python y el trabajador tras actualizar; no requiere migraciones adicionales.

OCR actualizado para [oficios con membrete y sello](OCR-REGIONES.md): reiniciar Python y el trabajador después de actualizar; no requiere otra migración.

Actualización del historial: [eliminación lógica y listado con altura fija](HISTORIAL.md). La migración documental `000006` ya está aplicada en este equipo; el total actual es seis. Reiniciar el trabajador para cargar el modelo actualizado.

Actualización posterior al bloque 7: las cargas ahora usan [digitalización automática y PDF de entrega](DIGITALIZACION-AUTOMATICA.md). La migración `000005` también está aplicada en este equipo; hay cinco migraciones documentales, además de las iniciales de Laravel. No se necesita seleccionar un modo OCR al cargar.

Estado final de los bloques 1–7, verificado en Windows con PHP 8.2.12, Laravel 12.70.0, PostgreSQL 18.6, Python 3.12.10 y Tesseract 5.5.3. Las versiones Python exactas están en `procesamiento/requirements.txt`; las PHP, en `laravel/composer.lock`.

## Esta instalación

No hace falta recrear la base, las claves ni el operador. Están configurados localmente y las cinco migraciones documentales están aplicadas. Para cargar la versión actual, detener con Ctrl+C las instancias anteriores al terminar sus tareas y arrancar tres terminales desde `C:\xampp\htdocs\Prototype`:

```powershell
# Terminal 1: FastAPI, solo loopback, un proceso
.\scripts\procesamiento.cmd
```

```powershell
# Terminal 2: Laravel
.\scripts\php.cmd .\laravel\artisan serve --host=127.0.0.1 --port=8000
```

```powershell
# Terminal 3: un trabajador de la cola OCR
.\scripts\cola-documentos.cmd
```

Abrir http://127.0.0.1:8000. La cuenta inicial está en el archivo privado `.tools/acceso-inicial.txt`. Para otra cuenta personal, `scripts\php.cmd laravel\artisan documentos:crear-operador`; pide una contraseña oculta y no sobrescribe usuarios existentes.

La carga guarda el documento y su tarea. Cuando termine, **Revisar** permite ver el original y el texto, corregir una referencia independiente y evaluar CER/WER. El [bloque 7](BLOQUE-7.md) explica el procedimiento. El ejemplo `prueba-sintetica-calidad-bloque7.pdf` sirve únicamente para verificar el flujo.

Después de copiar una actualización a otra instalación existente:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements.txt
.\scripts\php.cmd .\laravel\artisan migrate --no-interaction
.\scripts\php.cmd .\laravel\artisan config:clear
.\scripts\php.cmd .\laravel\artisan view:cache
```

Reiniciar los tres procesos después. No usar `migrate:fresh` en la base de aplicación.

## Instalación nueva

Estos pasos son para un equipo o copia nuevos; no ejecutarlos para reinicializar esta instalación.

1. Instalar PHP 8.2 compatible con Laravel y PostgreSQL. Los lanzadores usan `C:\xampp\php\php.exe`; para otra ruta establecer `IMANTAG_PHP` antes de ejecutarlos. `config/php/extensions.ini` agrega zip, pdo_pgsql, pgsql y gd a las extensiones estándar necesarias de Laravel. Comprobar requisitos con Composer; no editar permisos globales para resolver errores.
2. Instalar Composer mediante su [instalador oficial](https://getcomposer.org/download/) y verificarlo conforme a esa página. Si se instala globalmente, usar `composer install --working-dir=laravel`. El auxiliar `scripts\composer.cmd` espera un `composer.phar` local en la raíz, como en este equipo.
3. Instalar PostgreSQL. Desde una sesión administrativa psql, crear un rol exclusivo sin privilegios administrativos y su base; elegir una contraseña propia en lugar del marcador:

```sql
CREATE ROLE imantag_app LOGIN PASSWORD 'REEMPLAZAR_CON_CLAVE_PROPIA';
CREATE DATABASE imantag_documental OWNER imantag_app ENCODING 'UTF8';
```

4. Solo si no existen, copiar `laravel/.env.example` a `laravel/.env` y `procesamiento/.env.example` a `procesamiento/.env`. Ajustar DB_HOST/PORT/DATABASE/USERNAME/PASSWORD en Laravel. No usar el administrador PostgreSQL como cuenta de aplicación. Mantener `APP_DEBUG=false`.
5. Instalar Python 3.12 de 64 bits desde [python.org](https://www.python.org/downloads/windows/), incluyendo pip. Crear el entorno e instalar versiones fijadas:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

En este equipo el intérprete base está en `.tools/python312/python.exe`; la ejecución cotidiana utiliza `.venv` y no depende de `py`.

6. Instalar Tesseract desde las opciones Windows de [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), verificando el instalador descargado. Instalar español y datos de orientación. `spa.traineddata` puede obtenerse de [tessdata_fast 4.1.0](https://github.com/tesseract-ocr/tessdata_fast/tree/4.1.0); `osd.traineddata` debe estar en el mismo directorio de datos. Configurar en Python `.env` las rutas reales, por ejemplo:

```dotenv
PROCESSOR_TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
PROCESSOR_TESSDATA_DIR=C:/Program Files/Tesseract-OCR/tessdata
```

Comprobar `tesseract.exe --version` y `tesseract.exe --list-langs` usando su ruta completa. Deben aparecer `spa` y `osd`. En esta instalación las rutas apuntan a `.tools/tesseract`; la [guía OCR](BLOQUE-4.md) conserva sus verificaciones de descarga.

7. Generar una clave aleatoria local con `.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"` y copiarla a **PROCESSOR_API_TOKEN en ambos .env**. Guardarla privadamente, sin publicarla ni incluirla en Git. Laravel utiliza `PROCESSOR_URL=http://127.0.0.1:8002`. No exponer el puerto de Python a la red.
8. Preparar Laravel y un operador:

```powershell
.\scripts\php.cmd .\laravel\artisan key:generate
.\scripts\php.cmd .\laravel\artisan migrate --no-interaction
.\scripts\php.cmd .\laravel\artisan documentos:crear-operador
.\scripts\php.cmd .\laravel\artisan config:clear
```

Arrancar los tres procesos como se indica al principio. Bootstrap y PDF.js están incluidos en `laravel/public/vendor`; no se necesita npm, Vite, CDN ni servicios de OCR externos para ejecutar el sistema.

## Límites y datos

Los ejemplos de ambos `.env` documentan los límites. Por defecto: 20 MB por archivo, 100 páginas, renderizado de hasta 12 millones de píxeles, OCR global 120 s y una operación pesada a la vez. La evaluación admite hasta 10 000 caracteres por texto; el guardado de referencias permite hasta 200 000. PHP debe admitir el tamaño de carga más el sobrecoste multipart. Mantener los tiempos HTTP/Job/reintento coherentes; el trabajador comprueba esa relación al arrancar.

Los originales están en `laravel/storage/app/documentos`, fuera de `public`; no crearles enlaces públicos. Respaldar la base, ese almacenamiento y las claves de configuración privadas de forma coherente. No borrar archivos al resolver problemas de procesamiento: utilizar el reintento del listado tras corregir su causa. Los documentos completados no se vuelven a encolar desde esa acción.

El `.htaccess` de la raíz niega acceso directo al código bajo XAMPP. Para Apache, el DocumentRoot debe apuntar exclusivamente a `laravel/public`; no eliminar ese bloqueo para abrir el proyecto. Antes de habilitar acceso de red, configurar HTTPS, cookies seguras y el servidor correspondiente. La instalación entregada escucha solo en loopback y tiene autenticación provisional de operadores, sin roles por departamento.

## Pruebas

Instalar dependencias de pruebas Python y ejecutar desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\procesamiento\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -c .\procesamiento\pytest.ini .\procesamiento\tests -q
```

En `laravel`, ejecutar `..\scripts\php.cmd vendor\bin\phpunit`. Por defecto utiliza SQLite en memoria y datos sintéticos. La verificación PostgreSQL requiere una base **exclusiva de pruebas**, aquí `imantag_documental_test`, y variables DB que la seleccionen; PHPUnit usa RefreshDatabase y recrea sus tablas. No apuntar pruebas a la base de aplicación. No ejecutar dos suites Laravel simultáneamente porque comparten el disco temporal simulado.

Las pruebas de navegador son opcionales y usan Chrome/Playwright con fichas sintéticas independientes. Su preparación y alcance están documentados en [bloque 6](BLOQUE-6.md) y [bloque 7](BLOQUE-7.md). Los archivos `.tools` incluyen secretos y artefactos locales, están excluidos de Git y no forman parte de una instalación nueva.

Falta medir resultados con referencias revisadas por personas sobre documentos institucionales reales. Ubuntu, otros navegadores y despliegue productivo no han sido verificados. Los detalles de seguridad, límites y pruebas se encuentran en las guías de cada bloque.
