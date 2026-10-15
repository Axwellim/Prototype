"""Encabezados impresos de color: localizar, alinear y leer sin borrar su tinta."""
import math
import re
from datetime import date
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from .layout import project_box, tsv_lines, render_lines
from rapidfuzz.distance import Levenshtein
from .formal_text import email_from_ocr
from .signatures import NAME, ROLE

MONTHS = 'enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre'.split()


def normalize_optical_date(text):
    pattern = r'^(.*?,\s*)([0-9OoUuIiLl]{1,2})(\s+de\s+(' + '|'.join(MONTHS) + r')\s+de\s+(\d{4}))([.,]?)$'
    match = re.fullmatch(pattern, text.strip(), re.I)
    if not match:
        return None
    day = match[2].translate(str.maketrans('OoUuIiLl', '00001111'))
    try:
        date(int(match[5]), MONTHS.index(match[4].lower())+1, int(day))
    except ValueError:
        return None
    prefix = match[1][:1].upper() + match[1][1:]
    return prefix + day.zfill(2) + match[3] + match[6]


def refine_address_words(path, folder, settings, recognize):
    lines = tsv_lines(recognize(path, settings, tsv=True, psm=7))
    attempts = 0
    with Image.open(path) as image:
        for line in lines:
            for word in line['words']:
                original = word['text']
                if attempts >= 6 or not original.isalpha() or len(original) < 4 or not 0 <= word['conf'] < 90:
                    continue
                attempts += 1
                patch = folder / f'palabra-encabezado-{attempts}.png'
                image.crop((max(0,word['x']-12),max(0,word['y']-12),min(image.width,word['x']+word['w']+12),min(image.height,word['y']+word['h']+12))).save(patch)
                candidates = [recognize(patch, settings, psm=mode).strip() for mode in (8,13)]
                if candidates[0] == candidates[1] and candidates[0].isalpha() and Levenshtein.distance(original,candidates[0]) == 1:
                    word['text'] = candidates[0]
            line['text'] = ' '.join(word['text'] for word in line['words'])
    return render_lines(lines).strip()


def heading_region(image):
    array = np.asarray(image.convert('RGB'))
    height, width = array.shape[:2]
    hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array([85, 25, 20]), np.array([140, 255, 245]))
    mask[int(height * .24):] = 0
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    valid = ((stats[:,3] >= 3) & (stats[:,3] < height*.045) &
             (stats[:,2] >= 2) & (stats[:,2] < width*.8) & (stats[:,4] >= 4))
    valid[0] = False
    selected = (valid[labels].astype(np.uint8) * 255)
    merged = cv2.dilate(selected, np.ones((3, max(5, round(width * .023))), np.uint8))
    _, _, stats, _ = cv2.connectedComponentsWithStats(merged)
    boxes = [(int(x), int(y), int(w), int(h)) for x, y, w, h, _ in stats[1:]
             if width * .1 < w and h < height * .07 and x > width * .2]
    if not 3 <= len(boxes) <= 6 or sum(w > width * .2 for _, _, w, _ in boxes) < 2:
        return None
    box = (max(0, min(x for x, y, w, h in boxes) - 8), max(0, min(y for x, y, w, h in boxes) - 8),
           min(width, max(x+w for x, y, w, h in boxes) + 8), min(height, max(y+h for x, y, w, h in boxes) + 8))
    return box, selected


def refine_heading(base, prepared, lines, operations, folder, settings, recognize):
    region = heading_region(base)
    if region is None:
        return lines, False
    box, mask = region
    x0, y0, x1, y1 = box
    ink = Image.fromarray(mask[y0:y1, x0:x1])
    scores = []
    for angle in np.arange(-5, 5.01, .25):
        projection = (np.asarray(ink.rotate(float(angle), expand=True)) > 0).sum(axis=1).astype(float)
        scores.append((float(np.sum(projection * projection)), -abs(float(angle)), float(angle)))
    angle = max(scores)[2]
    red = np.asarray(base.convert('RGB'))[:, :, 0]
    flat = cv2.divide(red, cv2.GaussianBlur(red, (0, 0), max(8, base.width / 80)), scale=245)
    strip = Image.fromarray(flat[y0:y1, x0:x1])
    factor = min(3, 2400 / strip.width, math.sqrt(min(2000000, settings.max_image_pixels) / (strip.width * strip.height)))
    size = (max(1, round(strip.width * factor)), max(1, round(strip.height * factor)))
    strip = strip.resize(size, Image.Resampling.BICUBIC).rotate(angle, expand=True, fillcolor=255)
    ink = ink.resize(size, Image.Resampling.NEAREST).rotate(angle, expand=True, fillcolor=0)
    projection = (np.asarray(ink) > 0).sum(axis=1)
    active = (projection > max(5, ink.width * .015)).astype(np.uint8).reshape(-1, 1)
    active = cv2.morphologyEx(active, cv2.MORPH_CLOSE, np.ones((max(3, round(factor * 2)), 1), np.uint8)).ravel()
    edges = np.diff(np.pad(active.astype(int), (1, 1)))
    rows = [(int(start), int(end)) for start, end in zip(np.where(edges == 1)[0], np.where(edges == -1)[0])
            if end-start >= factor * 3]
    if not 3 <= len(rows) <= 6:
        return lines, False
    texts = []
    for number, (start, end) in enumerate(rows):
        path = folder / f'encabezado-color-{number}.png'
        row = strip.crop((0, max(0, start-8), strip.width, min(strip.height, end+8)))
        ImageOps.expand(row, border=20, fill=255).save(path)
        text = recognize(path, settings, psm=7).strip()
        if not text:
            return lines, False
        if re.match(r'direcci[oó]n\s*:', text, re.I):
            text = refine_address_words(path, folder, settings, recognize)
        if re.search(r'contact|\b\d{9,13}\b', text, re.I):
            email = email_from_ocr(text)
            if email:
                # Mantener el rótulo y teléfono; sustituir solo el fragmento de correo.
                prefix = text.split('/', 1)[0].rstrip() if '/' in text else None
                if prefix:
                    text = prefix + ' / ' + email
        texts.append(text)
    if not any(re.search(r'direcci[oó]n|contactos|@', text, re.I) for text in texts):
        return lines, False
    projected = project_box(box, base.size, prepared.size, operations)
    above = [line for line in lines if line.get('y', 0)+line.get('h', 0) < projected[1]]
    retained = [line for line in lines if line.get('y', prepared.height) >= projected[3]]
    # Fechas próximas al encabezado: lectura local, sin inferir el día.
    best = settings
    if settings.refinement_tessdata_dir and (Path(settings.refinement_tessdata_dir)/'spa.traineddata').is_file():
        best = settings.model_copy(update={'tessdata_dir': settings.refinement_tessdata_dir})
    for line in retained:
        if line.get('y', prepared.height) > prepared.height * .35:
            continue
        if not re.search(r'\bde\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}', line['text'], re.I):
            continue
        path = folder/'fecha-encabezado-color.png'
        prepared.crop((max(0,line['x']-12),max(0,line['y']-12),min(prepared.width,line['x']+line['w']+12),min(prepared.height,line['y']+line['h']+12))).save(path)
        candidate = normalize_optical_date(recognize(path, best, psm=7).strip())
        if candidate:
            line = dict(line)
            line['text'] = candidate[:1].upper()+candidate[1:]
            retained = [line if (old.get('x'), old.get('y')) == (line['x'], line['y']) else old for old in retained]
    return above + [{'text':'\n'.join(texts), 'group':('encabezado','color')}] + retained, True


def omit_single_signature(base, prepared_size, lines, operations):
    """Aparta solo trazos azules entre despedida y un firmante impreso identificado."""
    closings = [line for line in lines if re.fullmatch(r'Atentamente[,.:]?', line['text'], re.I)
                and line.get('y', 0) > prepared_size[1] * .5]
    if len(closings) != 1:
        return lines, False
    closing = closings[0]
    names = [line for line in lines if line.get('y', 0) > closing['y'] and NAME.match(line['text'])]
    if len(names) != 1 or not any(ROLE.match(line['text']) for line in lines if line.get('y',0) > names[0]['y']):
        return lines, False
    aligned = base
    for operation in operations:
        match = re.search(r'inclinación (-?[\d.]+) grados', operation)
        if match:
            aligned = aligned.rotate(float(match[1]), expand=True, fillcolor='white')
    aligned = aligned.resize(prepared_size)
    result = []
    removed = False
    for line in lines:
        if closing['y']+closing['h'] < line.get('y',0) < names[0]['y'] and len(line['text'].split()) <= 3 and not any(char.isdigit() for char in line['text']):
            patch = np.asarray(aligned.crop((line['x'],line['y'],line['x']+line['w'],line['y']+line['h'])).convert('RGB'))
            hsv = cv2.cvtColor(patch,cv2.COLOR_RGB2HSV)
            mask = cv2.inRange(hsv,np.array([85,30,20]),np.array([170,255,230]))
            if np.count_nonzero(mask) > mask.size * .005:
                removed = True
                continue
        result.append(line)
    return result, removed
