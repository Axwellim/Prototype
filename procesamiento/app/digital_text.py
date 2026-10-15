"""Normalización de ligaduras y comprobación óptica de una codificación ambigua."""
import re
from tempfile import TemporaryDirectory
from pathlib import Path
import unicodedata

import pymupdf


def expand_ligatures(text):
    return ''.join(unicodedata.normalize('NFKC', char) if '\ufb00' <= char <= '\ufb06' else char for char in text)


def repair_digital_text(page, text, settings, recognize, parent=None):
    normalized = expand_ligatures(text)
    notes = []
    if normalized != text:
        notes.append('Se expandieron ligaduras tipográficas Unicode en la transcripción; se conserva la capa de texto previa.')
    if '\u019f' not in text:
        return normalized, notes
    warning = 'La capa digital contiene Ɵ sin correspondencia óptica suficiente; requiere revisión contra el PDF.'
    if not settings.ocr_enabled:
        return normalized, notes + [warning]
    fonts = {span['font'] for block in page.get_text('dict')['blocks'] if 'lines' in block
             for line in block['lines'] for span in line['spans'] if '\u019f' in span['text']}
    words = [word for word in page.get_text('words') if '\u019f' in word[4]]
    # No alterar símbolos aislados, fórmulas o usos de otra fuente en la página.
    if len(fonts) != 1 or sum(word[4].count('\u019f') for word in words) != text.count('\u019f') or any(
            not re.fullmatch(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñƟ]+[,.;:!?]?", word[4]) for word in words):
        return normalized, notes + [warning]
    samples = list({word[4]: word for word in words}.values())[:3]
    if len(samples) < 3:
        return normalized, notes + [warning]
    with TemporaryDirectory(prefix='imantag-glyph-', dir=parent) as folder:
        for index, word in enumerate(samples):
            rect = (pymupdf.Rect(word[:4]) + (-2, -2, 2, 2)) & page.rect
            if rect.is_empty or rect.width * rect.height * 25 > min(settings.max_image_pixels, 1000000):
                return normalized, notes + [warning]
            path = Path(folder) / f'palabra-{index}.png'
            page.get_pixmap(matrix=pymupdf.Matrix(5, 5), clip=rect, colorspace=pymupdf.csRGB, alpha=False).save(path)
            try:
                optical = expand_ligatures(recognize(path, settings, psm=7)).strip()
            except Exception:
                # Es una comprobación opcional: no perder una capa digital legible.
                return normalized, notes + [warning]
            expected = expand_ligatures(word[4]).replace('\u019f', 'ti')
            if optical != expected:
                return normalized, notes + [warning]
    notes.append('Correspondencia Ɵ → ti confirmada ópticamente en tres palabras distintas de una misma fuente; se conserva la capa de texto previa. No es una corrección por referencia humana.')
    return normalized.replace('\u019f', 'ti'), notes
