# PDF con texto digital y plantilla de fondo

Se revisó `Economicaproductiva-enviado.pdf` el 15 de octubre de 2026. La capa digital del PDF contiene correctamente el número, fecha, destinataria, cuerpo, nombre, cargo y contacto de la firmante. La plantilla ocupa casi toda la página como una imagen; las firmas y el sello son otras dos imágenes inferiores. El criterio anterior de cobertura de imágenes forzaba OCR aunque la capa visible ya fuera correcta, introduciendo el recorte de «Imantag» y ruido al intentar leer las rúbricas.

## Decisión de procesamiento

Ahora se mantiene la extracción digital cuando se cumplen conjuntamente las comprobaciones habituales de cantidad y legibilidad y una comprobación conservadora de fondo decorativo:

- Al menos 300 caracteres alfanuméricos visibles distribuidos en cuatro bandas verticales de la página. Se descartan texto oculto, transparente, blanco y glifos fuera de la página.
- Una imagen dominante que cubra al menos el 80 % de la página, sin rotación ni inclinación en su transformación. Debe contener toda la zona central analizada y no exceder el límite de píxeles.
- Menos del 0,01 % de píxeles con luminancia inferior a 180 en la zona central de esa imagen. Se analiza la imagen de fondo por separado, sin confundirla con las letras digitales dibujadas encima.
- Las otras imágenes deben ser pequeñas y estar situadas en la zona inferior de firma, o ser logotipos superiores repetidos y verificados dentro del mismo PDF. Una imagen adicional en el cuerpo impide la excepción.

Si falta evidencia, hay tinta rasterizada en el cuerpo, la capa solo es un pie de página, el texto es invisible o falla el análisis opcional, se mantiene el criterio anterior de OCR. Es una heurística acotada para fondos claros, no un detector universal de plantillas. No garantiza identificar todo contenido escaneado tenue o todos los problemas de codificación; los fondos oscuros y estructuras no admitidas continúan con OCR.

En este caso no se ejecuta Tesseract para transcribir la página. Los datos proceden del texto original del propio PDF. Se ajustan márgenes y líneas vacías y se conserva la reconstrucción de párrafos ya implementada. La capa anterior permanece en `texto_digital`. El PDF normalizado es idéntico, byte por byte, al original.

## Verificación

Referencia: transcripción revisada aportada por el usuario, sin el marcador descriptivo de firma y sello. Se compararon ambas salidas contra la misma referencia:

| Resultado | CER | WER |
| --- | ---: | ---: |
| Criterio anterior, con OCR forzado por el fondo | 2,60 % | 7,94 % |
| Extracción digital conservada | 0,00 % | 0,00 % |

La salida contiene «OFICIO N° GADPRI-288-2026», «Imantag, 01 de septiembre del 2026» y el bloque de la firmante sin los caracteres de las rúbricas. Esta medición corresponde únicamente al documento y referencia indicados; no representa precisión general.

El código de producción no lee la referencia ni los artefactos de evaluación. Se verificó también que esta página no llama al OCR. Los seis ejemplos anteriores se reprocesaron para comprobar que conservan palabras y método de extracción. El paquete HTTP real devolvió la transcripción digital, la capa previa y el PDF intacto.

Artefactos privados en `.tools/diagnostico-economico`: entrada, imagen renderizada, capa digital, referencia, salidas anterior y nueva, comparación, regresiones y paquete verificado. La salida anterior se reprodujo deshabilitando exclusivamente la nueva excepción de fondo en el diagnóstico. Las fichas previas y las referencias guardadas en la base no se modificaron.

Reiniciar el servicio Python y cargar nuevamente el PDF para aplicar el cambio. Las páginas escaneadas siguen utilizando la ruta OCR.

Validación final: 99 pruebas Python aprobadas, seis regresiones reales sin cambios de palabras ni método y paquete HTTP verificado.

Ampliación posterior: [convenios de varias páginas, logotipos repetidos y cierre con menos texto](CONVENIOS-MULTIPAGINA.md).
