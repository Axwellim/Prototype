# Ligaduras y codificación de texto en PDF

El 15 de octubre de 2026 se revisó visualmente `Ambiente-enviado.pdf`. Su apariencia muestra «Cristina», «constituye» y «colaborativa», pero la extracción devuelve «CrisƟna», «consƟtuye» y «colaboraƟva». Es un defecto de correspondencia entre glifo y texto Unicode de la fuente del PDF, no un error de reconocimiento de una fotografía. También aparecen ligaduras Unicode como «ﬁ».

La extracción digital expande únicamente las ligaduras tipográficas U+FB00–U+FB06 mediante sus equivalencias Unicode. No aplica NFKC a todo el documento: conserva superíndices, símbolos y otros caracteres.

Para el caso ambiguo Ɵ → ti, se exige una sola fuente para ese carácter, palabras alfabéticas latinas y al menos tres palabras distintas. Se renderizan tres recortes del PDF y se reconocen con Tesseract en modo de línea. Solo si las tres lecturas coinciden exactamente con la expansión propuesta se aplica la correspondencia a esa página. No se utiliza una referencia humana ni un listado de nombres. Los símbolos aislados, otras fuentes, evidencia insuficiente, OCR deshabilitado y errores de la comprobación conservan Ɵ y generan una observación de revisión. La comprobación es una heurística acotada; no resuelve todos los defectos posibles de fuentes PDF.

Cuando cambia el texto, la capa previa se conserva en `texto_digital` y se muestra como **Capa digital original antes del procesamiento**. Ambas versiones cuentan para el límite de caracteres. La extracción sigue siendo digital: el OCR solo verifica tres palabras. No se altera el archivo original ni el PDF normalizado, por lo que tampoco se modifica su firma electrónica.

En este archivo se corrigieron las 14 apariciones de Ɵ tras verificar ópticamente Cristina, constituye y colaborativa. Se expandieron las ligaduras de palabras como «financiamiento». Se conserva la estructura de extracción de PyMuPDF. No se calculó CER/WER global porque no se dispone de una referencia independiente revisada de toda la página; la comprobación se centró en el defecto señalado.

Los artefactos privados están en `.tools/diagnostico-ambiente`: entrada, imagen renderizada, texto anterior, texto corregido y resultado JSON. No se incluyen en Git. Para nuevas cargas, reiniciar Python y volver a cargar el PDF; las extracciones ya guardadas no se sobrescriben automáticamente.
