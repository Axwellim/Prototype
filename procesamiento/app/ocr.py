"""OCR secuencial sobre copias; nunca modifica el documento original."""
import math
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from .schemas import OcrVariant
from .layout import tsv_lines, render_lines, body_copy, letter_bounds, identification_copy, merge_fragments
from .coverage import text_components, coverage, illumination_copy
from .signatures import read_closing
from .signature_columns import read_signature_columns
from .colored_heading import refine_heading, omit_single_signature
from .paragraphs import reflow_paragraphs, format_ocr_letter
from .subject import refine_subject, normalize_office_number


class OcrError(Exception):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def tesseract(image_path, settings, osd=False, tsv=False, psm=3):
    command = [settings.tesseract_cmd, str(image_path), 'stdout', '-l', 'osd' if osd else 'spa',
               '--psm', '0' if osd else str(psm)]
    if settings.tessdata_dir:
        command += ['--tessdata-dir', settings.tessdata_dir]
    if not osd:
        command += ['--dpi', str(settings.render_dpi)]
    if tsv:
        command += ['tsv']
    env = dict(os.environ, OMP_THREAD_LIMIT='1')
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=settings.ocr_timeout_seconds, env=env, check=False,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except FileNotFoundError:
        raise OcrError('tesseract_no_disponible', 'No se encontró Tesseract en el servidor.', 503)
    except subprocess.TimeoutExpired:
        raise OcrError('ocr_tiempo_excedido', 'Tesseract superó el tiempo permitido.', 504)
    if result.returncode:
        if b'Error opening data file' in result.stderr or b'Failed loading language' in result.stderr:
            raise OcrError('idioma_no_disponible', 'No se encontró el idioma requerido de Tesseract.', 503)
        raise OcrError('ocr_fallido', 'Tesseract no pudo reconocer esta imagen.')
    return result.stdout.decode('utf-8', errors='replace')


def load_image(path, settings):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as image:
                expected = {'image/jpeg': 'JPEG', 'image/png': 'PNG'}[settings.input_mime]
                if image.format != expected or image.width * image.height > settings.max_image_pixels:
                    raise OcrError('imagen_invalida', 'El contenido o las dimensiones de la imagen no son válidos.')
                if getattr(image, 'n_frames', 1) != 1:
                    raise OcrError('imagen_animada', 'Las imágenes animadas no están permitidas.')
                image.verify()
            with Image.open(path) as image:
                # EXIF se aplica en una copia, incluida en las dos variantes comparables.
                return ImageOps.exif_transpose(image).convert('RGBA')
    except OcrError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise OcrError('imagen_invalida', 'La imagen está dañada, no es compatible o supera el límite de píxeles.')


def white_background(image):
    rgba = image.convert('RGBA')
    background = Image.new('RGBA', rgba.size, 'white')
    return Image.alpha_composite(background, rgba).convert('RGB')


def rotated_copy(image, degrees, settings):
    angle = math.radians(degrees)
    width = math.ceil(abs(image.width * math.cos(angle)) + abs(image.height * math.sin(angle)))
    height = math.ceil(abs(image.height * math.cos(angle)) + abs(image.width * math.sin(angle)))
    if width * height > settings.max_image_pixels:
        return image, False
    return image.rotate(degrees, expand=True, fillcolor='white'), True


def preprocess(image, settings):
    operations = []
    array = np.array(image.convert('RGB'))
    if settings.preprocess_grayscale or settings.preprocess_contrast or settings.preprocess_deskew or settings.preprocess_binarize or settings.preprocess_denoise:
        array = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
        operations.append('escala de grises')
    if settings.preprocess_contrast:
        array = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(array)
        operations.append('contraste local moderado')
    if settings.preprocess_denoise:
        array = cv2.medianBlur(array, 3)
        operations.append('reducción de ruido mediana 3x3')
    result = Image.fromarray(array)
    if settings.preprocess_deskew:
        ratio = min(1, 1400 / result.width)
        small = cv2.resize(array, None, fx=ratio, fy=ratio) if ratio < 1 else array
        edges = cv2.Canny(small, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=70, minLineLength=max(40, small.shape[1] // 8), maxLineGap=20)
        angles = []
        if lines is not None:
            for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                if abs(angle) <= 5:
                    angles.append(angle)
        if len(angles) >= 3:
            angle = float(np.median(angles))
            if abs(angle) >= 0.2:
                result, applied = rotated_copy(result, angle, settings)
                if applied:
                    operations.append(f'corrección de inclinación {angle:.2f} grados')
    if settings.preprocess_binarize:
        gray = np.array(result.convert('L'))
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        result = Image.fromarray(binary)
        operations.append('binarización Otsu')
    if settings.preprocess_upscale and result.width < 1600:
        target = 2400 if settings.ocr_mode == 'automatico' else 1600
        factor = min(2.5 if settings.ocr_mode == 'automatico' else 2, target / result.width, math.sqrt(settings.max_image_pixels / (result.width * result.height)))
        if factor > 1.05:
            size = (int(result.width * factor), int(result.height * factor))
            result = Image.fromarray(cv2.resize(np.array(result), size, interpolation=cv2.INTER_CUBIC)) if settings.ocr_mode == 'automatico' else result.resize(size, Image.Resampling.LANCZOS)
            operations.append(f'ampliación {factor:.2f}x')
    return result, operations


def automatic_profile(image, settings):
    """Heurística de imagen, no estimación de precisión del reconocimiento."""
    sample = image.convert('L')
    sample.thumbnail((1400, 1400))
    array = np.array(sample)
    contrast = float(np.percentile(array, 99) - np.percentile(array, 1))
    median = cv2.medianBlur(array, 3)
    noise = float(np.mean(np.abs(array.astype(np.int16) - median.astype(np.int16)) > 35))
    lines = cv2.HoughLinesP(cv2.Canny(array, 50, 150), 1, np.pi / 180, 70,
                            minLineLength=max(40, sample.width // 8), maxLineGap=20)
    angles = []
    if lines is not None:
        for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if abs(angle) <= 5:
                angles.append(angle)
    skew = abs(float(np.median(angles))) if len(angles) >= 3 else 0
    reasons = []
    if contrast < 110:
        reasons.append('contraste bajo')
    if noise > .08:
        reasons.append('ruido elevado')
    if skew >= .4:
        reasons.append('inclinación leve')
    if image.width < 1400:
        reasons.append('resolución horizontal reducida')
    mode = 'preprocesado' if reasons else 'original'
    profile = settings.model_copy(update={
        'preprocess_grayscale': True, 'preprocess_contrast': contrast < 110,
        'preprocess_denoise': noise > .08, 'preprocess_deskew': skew >= .4,
        'preprocess_upscale': image.width < 1400, 'preprocess_binarize': False,
    })
    note = 'Selección automática v4: ' + mode + ' (' + (', '.join(reasons) or 'sin degradación detectada') + '). No es una medida de precisión.'
    return mode, profile, note


def recognize(image, settings, temporary_parent=None):
    if image.width * image.height > settings.max_image_pixels:
        raise OcrError('pixeles_excedidos', 'La imagen supera el límite de píxeles.')
    cv2.setNumThreads(1)
    base = white_background(image)
    notes = []
    with TemporaryDirectory(prefix='imantag-ocr-', dir=temporary_parent) as temporary:
        source = Path(temporary) / 'original.png'
        base.save(source)
        if settings.correct_orientation:
            try:
                osd = tesseract(source, settings, osd=True)
                rotation = re.search(r'Rotate:\s*(0|90|180|270)\b', osd)
                confidence = re.search(r'Orientation confidence:\s*([\d.]+)', osd)
                if rotation and confidence and float(confidence[1]) >= settings.osd_min_confidence and int(rotation[1]):
                    base, applied = rotated_copy(base, -int(rotation[1]), settings)
                    if applied:
                        base.save(source)
                        notes.append(f'Orientación corregida {rotation[1]} grados antes de ambas variantes.')
                elif not confidence or float(confidence[1]) < settings.osd_min_confidence:
                    notes.append('Orientación no concluyente; se conservó la orientación disponible.')
            except OcrError as error:
                if error.code == 'tesseract_no_disponible':
                    raise
                notes.append('No se pudo estimar la orientación; se continuó sin rotación OSD.')
        variants = []
        if settings.ocr_mode == 'automatico':
            selected, settings, decision = automatic_profile(base, settings)
            notes.append(decision)
            modes = [selected]
        else:
            modes = ['original', 'preprocesado'] if settings.ocr_mode == 'comparar' else [settings.ocr_mode]
        for mode in modes:
            started = perf_counter()
            operations = []
            path = source
            if mode == 'preprocesado':
                processed, operations = preprocess(base, settings)
                path = Path(temporary) / 'preprocesado.png'
                processed.save(path)
            full_text = None
            initial_text = None
            exclusions = []
            scope = 'pagina_completa'
            if settings.ocr_mode == 'automatico':
                raw = tesseract(path, settings, tsv=True)
                lines = tsv_lines(raw)
                text = render_lines(lines)
                if lines:
                    with Image.open(path) as prepared:
                        body, exclusions = body_copy(prepared, base, lines, operations)
                        bounds = letter_bounds(lines, prepared.size)
                        identification, identification_box = identification_copy(prepared, lines) if body is not None else (None,None)
                        if body is None:
                            components = text_components(prepared)
                            initial_coverage = coverage(lines,prepared.size,components)
                            if initial_coverage < .75:
                                recovery = illumination_copy(prepared)
                                recovery_path = Path(temporary) / 'iluminacion.png'
                                recovery.save(recovery_path)
                                recovered_lines = tsv_lines(tesseract(recovery_path,settings,tsv=True))
                                recovered_coverage = coverage(recovered_lines,recovery.size,components)
                                if recovered_coverage > initial_coverage + .08:
                                    initial_text = text
                                    lines = recovered_lines
                                    text = render_lines(lines)
                                    operations.append('corrección de iluminación tras detectar zonas sin lectura')
                                    notes.append('Se repitió la lectura de página completa por posibles omisiones. La cobertura de componentes no representa precisión OCR.')
                                if max(initial_coverage,recovered_coverage) < .75:
                                    notes.append('Persisten posibles zonas sin transcribir; coteja la página completa con el original.')
                    if body is not None:
                        full_text = text
                        body_path = Path(temporary) / 'contenido.png'
                        body.save(body_path)
                        body_lines = tsv_lines(tesseract(body_path, settings, tsv=True))
                        body_lines = merge_fragments(body_lines, body.width)
                        if identification is not None:
                            identification_path = Path(temporary) / 'identificacion.png'
                            identification.save(identification_path)
                            identity = render_lines(tsv_lines(tesseract(identification_path, settings, tsv=True, psm=6)))
                            source_codes = [word['text'] for line in lines for word in line.get('words', [])
                                            if identification_box[0] <= word['x'] and word['y'] < identification_box[3]
                                            and re.fullmatch(r'[A-Z]{3,12}-\d{1,6}-\d{4}', word['text'])]
                            if len(source_codes) == 1 and source_codes[0] not in identity:
                                identity = '\n'.join(' '.join(word['text'] for word in line.get('words', [])
                                    if word['x'] >= identification_box[0]) for line in lines
                                    if identification_box[1] <= line['y'] < identification_box[3])
                                operations.append('conservación del identificador reconocido en la pasada completa ante discrepancia local')
                            if re.search(r'OFICIO|CIRCULAR',identity,re.I) and re.search(r'\d',identity) and re.search(r'enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|\d{1,2}/\d{1,2}',identity,re.I):
                                cutoff = identification_box[3] - bounds[1]
                                body_lines = [line for line in body_lines if not
                                    (line['y'] < cutoff and line['x']+line['w'] > identification_box[0])
                                    and not (line['y'] < cutoff and re.search(r'Caminemos|GAD.*Parroquial',line['text'],re.I))]
                                body_lines.insert(0,{'text':identity.strip(),'group':('identificacion','local')})
                                operations.append('lectura local de identificación y fecha con inclinación corregida')
                        try:
                            body_lines = refine_subject(body, body_lines, temporary, settings, tesseract)
                        except OcrError:
                            notes.append('No se completó la relectura del asunto; se conserva su lectura previa.')
                        candidate = render_lines(body_lines)
                        try:
                            detection_lines = [dict(line, y=line['y'] - bounds[1],
                                words=[dict(word, y=word['y'] - bounds[1]) for word in line.get('words', [])])
                                for line in lines if bounds[1] <= line['y'] < bounds[3]]
                            columns = read_signature_columns(body, body_lines, Path(temporary), settings, tesseract, detection_lines, full_text)
                        except OcrError:
                            columns = None
                            notes.append('No se completó la lectura de columnas de firmas; se conserva la lectura regional para revisión.')
                        if columns is not None:
                            candidate = columns
                            operations.append('lectura separada de dos columnas de firmantes con atenuación de tinta azul')
                            operations.append('normalización acotada de abreviaturas, correo y cargos por consistencia con el propio documento')
                            if settings.refinement_tessdata_dir and (Path(settings.refinement_tessdata_dir) / 'spa.traineddata').is_file():
                                operations.append('segunda lectura de líneas impresas con modelo español de precisión configurado')
                            notes.append('Firmantes leídos por columnas. Se aplicaron reglas acotadas de formato y consistencia con el propio documento; cotejar los datos superpuestos con firmas y sellos.')
                        if candidate.strip():
                            text = candidate
                            scope = 'contenido_principal'
                            operations.append('lectura por regiones con saltos de línea TSV')
                            notes.append('Se excluyeron zonas auxiliares del texto principal; el OCR de página completa se conserva para revisión.')
                        else:
                            exclusions = []
                            notes.append('La lectura regional quedó vacía; se conservó la lectura de página completa.')
            else:
                text = tesseract(path, settings)
            if settings.ocr_mode == 'automatico' and scope == 'pagina_completa' and lines:
                with Image.open(path) as prepared:
                    try:
                        closing_text = read_closing(base, prepared.size, lines, operations, Path(temporary), settings, tesseract)
                    except OcrError as error:
                        if error.code == 'tesseract_no_disponible':
                            raise
                        closing_text = None
                        notes.append('No se completó la lectura local de firmas; se conservó el OCR completo para revisión.')
                if closing_text is not None:
                    full_text = text
                    text = closing_text
                    scope = 'contenido_principal'
                    exclusions.append('Rúbricas, anotaciones manuscritas y zonas auxiliares posteriores al bloque impreso de firmantes; consultar original y OCR completo.')
                    operations.append('lectura local del cierre impreso con atenuación de tinta azul y selección por confianza OCR')
                    notes.append('Cierre con firmas: se separó el texto impreso de las marcas manuscritas. Revisa nombres y cargos superpuestos; la confianza de Tesseract no garantiza exactitud. No se transcribieron firmas ni anotaciones manuscritas.')
                else:
                    try:
                        with Image.open(path) as prepared:
                            prepared_size = prepared.size
                            revised, heading_changed = refine_heading(base, prepared, lines, operations, Path(temporary), settings, tesseract)
                        revised, signature_removed = omit_single_signature(base, prepared_size, revised, operations)
                    except OcrError:
                        heading_changed = signature_removed = False
                        notes.append('No se completó la lectura localizada del encabezado; se conserva el OCR previo.')
                    if heading_changed or signature_removed:
                        full_text = text
                        text = render_lines(revised)
                        if heading_changed:
                            operations.append('lectura por líneas del encabezado impreso azul con alineación local y canal rojo')
                            operations.append('relectura óptica acotada de palabras de dirección y normalización de formato de fecha y correo')
                            notes.append('Se conserva el encabezado del emisor y se vuelve a leer su fecha sin completar datos desde referencias humanas.')
                        if signature_removed:
                            scope = 'contenido_principal'
                            exclusions.append('Trazos azules entre la despedida y un único firmante impreso; OCR previo conservado.')
                            operations.append('separación de rúbrica y firmante impreso sin modificar nombres ni cargos')
            if settings.ocr_mode == 'automatico':
                numbered = normalize_office_number(text)
                if numbered != text:
                    if full_text is None:
                        full_text = text
                    text = numbered
                    operations.append('normalización del símbolo de número en identificadores de oficio')
                formatted = format_ocr_letter(reflow_paragraphs(text))
                if formatted != text:
                    if full_text is None:
                        full_text = text
                    text = formatted
                    operations.append('reconstrucción de párrafos del cuerpo sin cambiar palabras, encabezados ni firmantes')
            if len(text) + len(full_text or '') + len(initial_text or '') > settings.max_text_chars:
                raise OcrError('texto_excedido', 'El texto OCR supera el límite permitido.')
            variants.append(OcrVariant(modo=mode, texto=text, duracion_ms=round((perf_counter() - started) * 1000), operaciones=operations,
                                       texto_pagina_completa=full_text, texto_lectura_inicial=initial_text, alcance=scope, exclusiones=exclusions))
        if not any(variant.texto.strip() for variant in variants):
            notes.append('No se reconoció texto en esta imagen; requiere revisión manual.')
        return variants, notes
