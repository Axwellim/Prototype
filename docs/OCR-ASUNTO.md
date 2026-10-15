# Asuntos impresos fragmentados

El oficio circular fotografiado de Bienes presentaba una comilla en lugar del símbolo de número y la palabra «FERIA» fragmentada como «FER lA» en el asunto. La lectura automática regional ahora reúne las líneas consecutivas del asunto hasta su separación visual o el saludo. Cuando encuentra fragmentos con mezcla anómala de mayúsculas y minúsculas, vuelve a leer únicamente esa zona mediante el modelo español de precisión si está configurado.

Se acepta una lectura similar que elimine la fragmentación, conservando el prefijo ASUNTO. Si la lectura termina en coma, una lectura ampliada puede confirmar un punto, únicamente cuando coincide todo el resto del texto. No se utilizan repertorios de asuntos ni referencias humanas para generar palabras. El símbolo del número se normaliza solo detrás de OFICIO u OFICIO CIRCULAR y antes de un identificador documental.

Se conserva el OCR completo de respaldo. Número y fecha, tratamiento, nombre y cargo siguen en sus propias líneas conforme a la preferencia del usuario. El cuerpo no se reformula ni se eliminan tildes para imitar una referencia. La imagen original se mantiene intacta.

Artefactos privados: `.tools/diagnostico-bienes/asunto-corregido.json` y `texto-asunto-corregido.txt`. Reiniciar el servicio Python y cargar otra vez la imagen para aplicar el cambio a una ficha nueva.
