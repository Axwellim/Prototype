"""PDF de entrega independiente; el archivo recibido nunca se modifica."""
import io
import shutil
from pathlib import Path

import pymupdf

from .extraction import DocumentError
from .ocr import load_image, white_background


def normalize_pdf(source: Path, target: Path, settings, expected_pages: int):
    if settings.input_mime == 'application/pdf':
        # El PDF ya validado se conserva byte a byte, sin rasterizar ni perder capas.
        shutil.copyfile(source, target)
    else:
        image = white_background(load_image(source, settings))
        stream = io.BytesIO()
        image.save(stream, format='PNG')
        with pymupdf.open() as document:
            page = document.new_page(width=image.width * 72 / settings.render_dpi,
                                     height=image.height * 72 / settings.render_dpi)
            page.insert_image(page.rect, stream=stream.getvalue())
            document.save(target, deflate=True)
    if target.stat().st_size > settings.max_pdf_bytes:
        raise DocumentError('pdf_resultado_excedido', 'El PDF resultante supera el límite permitido.', 413)
    with pymupdf.open(target) as document:
        if not document.is_pdf or document.needs_pass or document.page_count != expected_pages:
            raise DocumentError('normalizacion_fallida', 'El PDF generado no coincide con las páginas procesadas.')
