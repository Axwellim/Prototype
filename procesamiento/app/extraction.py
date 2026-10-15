from pathlib import Path
from time import perf_counter
import pymupdf
import math
import re
from collections import Counter
from PIL import Image
from .ocr import OcrError, load_image, recognize, tesseract
from .digital_text import repair_digital_text
from .paragraphs import reflow_paragraphs
from .pdf_background import has_clear_background_with_visible_text
from .native_layout import render_structured_native, render_native_letter

from .config import Settings
from .schemas import PageResult, ProcessingResult


class DocumentError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def extract_pdf(path: Path, settings: Settings) -> ProcessingResult:
    started = perf_counter()
    pymupdf.TOOLS.mupdf_display_errors(False)
    pymupdf.TOOLS.mupdf_display_warnings(False)
    if path.stat().st_size > settings.max_bytes:
        raise DocumentError('tamano_excedido', 'El archivo supera el tamaño permitido.', 413)
    with path.open('rb') as source:
        if not source.read(8).startswith(b'%PDF-'):
            raise DocumentError('formato_invalido', 'El contenido recibido no es un PDF.')
    try:
        with pymupdf.open(path) as document:
            if not document.is_pdf:
                raise DocumentError('formato_invalido', 'El contenido recibido no es un PDF.')
            if document.needs_pass:
                raise DocumentError('pdf_cifrado', 'El PDF está protegido con contraseña.')
            if document.is_repaired:
                raise DocumentError('pdf_corrupto', 'El PDF requiere reparación y no se procesará.')
            count = document.page_count
            if count < 1:
                raise DocumentError('pdf_vacio', 'El PDF no contiene páginas.')
            if count > settings.max_pages:
                raise DocumentError('paginas_excedidas', 'El PDF supera el máximo de páginas permitido.')
            pages, total_chars = [], 0
            verified_backgrounds = set()
            image_pages = Counter()
            for candidate_page in document:
                image_pages.update({item['xref'] for item in candidate_page.get_image_info(xrefs=True) if item['xref']})
            repeated_headers = {xref for xref, occurrences in image_pages.items() if occurrences >= 2}
            for number, page in enumerate(document, start=1):
                page_started = perf_counter()
                text = page.get_text('text', sort=True)
                total_chars += len(text)
                if total_chars > settings.max_text_chars:
                    raise DocumentError('texto_excedido', 'El texto extraído supera el límite permitido.')
                compact = ''.join(text.split())
                words = text.split()
                printable = sum(char.isprintable() for char in compact) / max(1, len(compact))
                alnum = sum(char.isalnum() for char in compact) / max(1, len(compact))
                image_area = 0.0
                for image in page.get_image_info():
                    rect = pymupdf.Rect(image['bbox']) & page.rect
                    if not rect.is_empty:
                        image_area += rect.get_area()
                coverage = min(1.0, image_area / max(1, page.rect.get_area()))
                reasons = []
                if len(compact) < settings.min_chars:
                    reasons.append('Texto digital insuficiente en cantidad de caracteres.')
                if len(words) < settings.min_words:
                    reasons.append('Texto digital insuficiente en cantidad de palabras.')
                if printable < settings.min_printable_ratio or alnum < settings.min_alnum_ratio:
                    reasons.append('La capa de texto contiene demasiados caracteres no recuperables.')
                decorative_background = False
                if coverage >= settings.max_image_coverage and not reasons:
                    try:
                        decorative_background = has_clear_background_with_visible_text(page, settings, verified_backgrounds, repeated_headers)
                    except Exception:
                        # Análisis opcional: ante duda se mantiene el criterio conservador de OCR.
                        decorative_background = False
                if coverage >= settings.max_image_coverage and not decorative_background:
                    reasons.append('La página contiene una imagen de gran cobertura; requiere revisión OCR.')
                variants = []
                digital = None
                method = 'requiere_ocr' if reasons else 'digital'
                if reasons and settings.ocr_enabled:
                    scale = settings.render_dpi / 72
                    if math.ceil(page.rect.width * scale + 1) * math.ceil(page.rect.height * scale + 1) > settings.max_image_pixels:
                        raise DocumentError('pixeles_excedidos', 'La página renderizada supera el límite de píxeles; reduce PROCESSOR_RENDER_DPI.')
                    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), colorspace=pymupdf.csRGB, alpha=False)
                    image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
                    variants, notes = recognize(image, settings, temporary_parent=path.parent)
                    digital = text
                    # La comparación mantiene el OCR original como principal, sin concatenar capas.
                    text = variants[0].texto
                    method = 'ocr'
                    reasons.extend(notes)
                    total_chars += sum(len(variant.texto) + len(variant.texto_pagina_completa or '') + len(variant.texto_lectura_inicial or '') for variant in variants)
                    if total_chars > settings.max_text_chars:
                        raise DocumentError('texto_excedido', 'Los resultados del documento superan el límite de texto.')
                if method == 'digital':
                    if decorative_background:
                        reasons.append('Se conserva texto digital visible y distribuido: la imagen dominante tiene un fondo central claro sin texto rasterizado detectable. Firmas y sellos permanecen en el PDF.')
                    structured = render_structured_native(page) if decorative_background else None
                    if structured is None and decorative_background:
                        structured = render_native_letter(page)
                    corrected, normalization_notes = repair_digital_text(page, structured if structured is not None else text, settings, tesseract, path.parent)
                    if structured is not None:
                        normalization_notes.append('Se reconstruyeron cláusulas, viñetas, párrafos y bloques de firmantes mediante posiciones del texto digital.')
                    if decorative_background:
                        cleaned = re.sub(r'\n{3,}', '\n\n', '\n'.join(line.strip() for line in corrected.splitlines())).strip()
                        if cleaned != corrected:
                            normalization_notes.append('Se normalizaron márgenes de texto y líneas vacías de la capa digital; se conserva su versión previa.')
                        corrected = cleaned
                    formatted = reflow_paragraphs(corrected)
                    if formatted != corrected:
                        normalization_notes.append('Se reconstruyeron los párrafos del cuerpo conservando el texto digital previo.')
                        corrected = formatted
                    reasons.extend(normalization_notes)
                    if corrected != text:
                        digital, text = text, corrected
                        total_chars += len(text)
                        if total_chars > settings.max_text_chars:
                            raise DocumentError('texto_excedido', 'Los resultados del documento superan el límite de texto.')
                pages.append(PageResult(numero=number, metodo=method,
                                        texto=text, texto_digital=digital, variantes_ocr=variants,
                                        duracion_ms=round((perf_counter() - page_started) * 1000),
                                        observaciones=reasons))
            return ProcessingResult(estado='requiere_ocr' if any(p.metodo == 'requiere_ocr' for p in pages) else 'completado',
                                    numero_paginas=count, duracion_total_ms=round((perf_counter() - started) * 1000),
                                    paginas=pages, texto_completo='\f'.join(p.texto for p in pages))
    except OcrError as error:
        raise DocumentError(error.code, error.message, error.status) from error
    except DocumentError:
        raise
    except Exception as error:
        raise DocumentError('pdf_invalido', 'No se pudo leer la estructura o el contenido del PDF.') from error


def extract_document(path: Path, settings: Settings) -> ProcessingResult:
    if settings.input_mime == 'application/pdf':
        return extract_pdf(path, settings)
    started = perf_counter()
    if path.stat().st_size > settings.max_bytes:
        raise DocumentError('tamano_excedido', 'El archivo supera el tamaño permitido.', 413)
    if not settings.ocr_enabled:
        raise DocumentError('ocr_deshabilitado', 'El OCR está deshabilitado para imágenes.', 503)
    try:
        image = load_image(path, settings)
        variants, notes = recognize(image, settings, temporary_parent=path.parent)
        if sum(len(variant.texto) + len(variant.texto_pagina_completa or '') + len(variant.texto_lectura_inicial or '') for variant in variants) > settings.max_text_chars:
            raise DocumentError('texto_excedido', 'Los resultados superan el límite de texto.')
    except OcrError as error:
        raise DocumentError(error.code, error.message, error.status) from error
    elapsed = round((perf_counter() - started) * 1000)
    page = PageResult(numero=1, metodo='ocr', texto=variants[0].texto,
                      duracion_ms=elapsed, variantes_ocr=variants, observaciones=notes)
    return ProcessingResult(estado='completado', numero_paginas=1, duracion_total_ms=elapsed,
                            paginas=[page], texto_completo=page.texto)
