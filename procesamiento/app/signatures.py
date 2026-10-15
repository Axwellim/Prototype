"""Lectura conservadora de cierres impresos con tinta de color superpuesta.

No recibe referencias ni reconstruye nombres o cargos mediante diccionarios.
"""
import re

import cv2
import numpy as np
from PIL import Image

from .layout import render_lines, tsv_lines

NAME = re.compile(r'^[^\w\s]*(?:Sra?\.?|[Llt1]?ic\.?|[IÍ]ng\.?|Dr[a]?\.?)\s+', re.I)
ROLE = re.compile(r'^(?:PRESID|VICEPRESID|SECRETAR|TESOR|DIRECTOR|COORDINADOR|VOCAL)', re.I)


def closing_region(lines, size):
    width, height = size
    closings = [line for line in lines if re.fullmatch(r'Atentamente\s*[,.:]?', line['text'], re.I)
                and height * .25 < line['y'] < height * .85]
    if len(closings) != 1:
        return None
    closing = closings[0]
    tail = [line for line in lines if line['y'] > closing['y'] + closing['h']]
    names = [line for line in tail if NAME.match(line['text'])]
    roles = [line for line in tail if ROLE.match(line['text'])]
    if not 2 <= len(names) <= 8 or len(roles) < 2:
        return None
    left = min(line['x'] for line in names + roles)
    # Solo una columna de firmantes. Otros diseños conservan la lectura completa.
    if max(line['x'] for line in names + roles) - left > width * .12:
        return None
    bottom = max(line['y'] + line['h'] for line in names + roles)
    labels = [line for line in tail if line['y'] <= bottom and
              (NAME.match(line['text']) or ROLE.match(line['text']) or line['text'].isupper())]
    right = max(line['x'] + line['w'] for line in labels)
    return closing, (max(0, int(left - width * .035)),
                     closing['y'] + closing['h'], min(width, int(right + width * .05)),
                     min(height, int(bottom + height * .015)))


def printed_lines(lines):
    """Conserva rótulos impresos; no convierte rúbricas en palabras."""
    result = []
    for line in lines:
        words = list(line['words'])
        while len(words) > 1 and (words[-1]['conf'] < 45 or not any(char.isalpha() or char.isdigit() for char in words[-1]['text'])):
            words.pop()
        if NAME.match(' '.join(word['text'] for word in words)):
            for index, word in enumerate(words[1:], start=1):
                if not any(char.isalpha() for char in word['text']) or not all(char.isalpha() or char in "'-’" for char in word['text'].rstrip('.')):
                    words = words[:index]
                    break
        text = ' '.join(word['text'] for word in words)
        kind = ('name' if NAME.match(text) else 'role' if ROLE.match(text) else
                'heading' if text.isupper() and len(text.split()) >= 2 else None)
        if kind is None:
            continue
        score = sum(word['conf'] * len(word['text']) for word in words) / max(1, sum(len(word['text']) for word in words))
        if score < (80 if kind == 'heading' else 45):
            continue
        result.append(dict(line, text=text, kind=kind, score=score))
    return result


def read_closing(base, prepared_size, lines, operations, folder, settings, recognize):
    region = closing_region(lines, prepared_size)
    if region is None:
        return None
    closing, box = region
    aligned = base
    for operation in operations:
        match = re.search(r'inclinación (-?[\d.]+) grados', operation)
        if match:
            aligned = aligned.rotate(float(match[1]), expand=True, fillcolor='white')
    sx, sy = aligned.width / prepared_size[0], aligned.height / prepared_size[1]
    aligned = aligned.crop(tuple(round(value * (sx if index % 2 == 0 else sy)) for index, value in enumerate(box)))
    array = np.asarray(aligned).astype(np.float32)
    blue = array[:, :, 2]
    flat = blue / np.maximum(1, cv2.GaussianBlur(blue, (0, 0), max(8, aligned.width / 80))) * 245
    # El canal azul atenúa tinta azul; la diferencia cromática atenúa su resto.
    rgb = array.astype(np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array([85, 35, 20]), np.array([170, 255, 230]))
    if np.count_nonzero(mask) < mask.size * .0005:
        return None
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clean = cv2.inpaint(gray, mask, 3, cv2.INPAINT_TELEA)
    clean = cv2.divide(clean, cv2.GaussianBlur(clean, (0, 0), max(8, aligned.width / 80)), scale=245)
    candidates = []
    copies = []
    for index, pixels in enumerate((flat, flat + np.maximum(0, blue - array[:, :, 0]) * 3, clean)):
        path = folder / f'cierre-{index}.png'
        copy = Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8)).resize(
            (box[2] - box[0], box[3] - box[1]), Image.Resampling.BICUBIC)
        copy.save(path)
        copies.append(copy)
        candidates.extend(printed_lines(tsv_lines(recognize(path, settings, tsv=True, psm=6))))
    # Una pasada de línea evita que una rúbrica se fusione con el tratamiento.
    for number, name in enumerate(line for line in lines if line['y'] > closing['y'] and NAME.match(line['text'])):
        local = (max(0, int(name['x'] - box[0] - prepared_size[0] * .02)),
                 max(0, int(name['y'] - box[1] - name['h'] * .3)),
                 min(copies[0].width, int(name['x'] + name['w'] - box[0] + prepared_size[0] * .02)),
                 min(copies[0].height, int(name['y'] + name['h'] * 1.3 - box[1])))
        for index, copy in enumerate(copies):
            path = folder / f'firmante-{number}-{index}.png'
            copy.crop(local).save(path)
            for candidate in printed_lines(tsv_lines(recognize(path, settings, tsv=True, psm=7))):
                if candidate['kind'] == 'name':
                    candidate['y'] += local[1]
                    candidates.append(candidate)
    chosen = []
    for line in sorted(candidates, key=lambda item: item['y']):
        matches = [old for old in chosen if old['kind'] == line['kind'] and
                   abs(old['y'] - line['y']) < max(old['h'], line['h']) * .7]
        if matches:
            old = matches[0]
            more_complete_role = (line['kind'] in ('role', 'name') and all(char.isalpha() or char in '. ' for char in line['text']) and
                                  line['text'].startswith(old['text']) and len(line['text']) > len(old['text']))
            shorter_role = (line['kind'] in ('role', 'name') and old['text'].startswith(line['text']) and len(old['text']) > len(line['text']))
            if more_complete_role or (not shorter_role and line['score'] > old['score']):
                chosen.remove(old)
                chosen.append(line)
        else:
            chosen.append(line)
    if sum(line['kind'] == 'name' for line in chosen) != sum(NAME.match(line['text']) is not None for line in lines if line['y'] > closing['y']):
        return None
    if sum(line['kind'] == 'role' for line in chosen) < 2:
        return None
    chosen.sort(key=lambda item: item['y'])
    prefix = render_lines([line for line in lines if line['y'] <= closing['y']])
    return prefix.rstrip() + '\n\n' + render_lines(chosen)
