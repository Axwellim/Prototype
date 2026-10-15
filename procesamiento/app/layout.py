"""Lectura geométrica y exclusiones conservadoras para membretes reconocidos."""
import csv
import io
import math
import re
from collections import OrderedDict

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps


def tsv_lines(tsv):
    if not tsv.startswith('level\tpage_num\t'):
        raise ValueError('Tesseract no devolvió una tabla TSV válida.')
    groups = OrderedDict()
    for row in csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE):
        if row.get('level') != '5' or not row.get('text', '').strip():
            continue
        key = tuple(row[name] for name in ('block_num', 'par_num', 'line_num'))
        word = {'text': row['text'], 'x': int(row['left']), 'y': int(row['top']),
                'w': int(row['width']), 'h': int(row['height']), 'conf': float(row.get('conf', -1))}
        groups.setdefault(key, []).append(word)
    lines = []
    for key, words in groups.items():
        words.sort(key=lambda word: word['x'])
        x, y = min(w['x'] for w in words), min(w['y'] for w in words)
        lines.append({'text': ' '.join(w['text'] for w in words), 'x': x, 'y': y,
                      'w': max(w['x'] + w['w'] for w in words) - x,
                      'h': max(w['y'] + w['h'] for w in words) - y, 'group': key[:2], 'words': words})
    return lines


def render_lines(lines):
    output = []
    previous = None
    previous_line = None
    flow_width = max((line.get('x',0)+line.get('w',0) for line in lines), default=0)
    for line in lines:
        paragraph_end = (previous_line is not None and 'w' in previous_line and 'y' in line
                         and re.search(r'[.;,]$', previous_line['text'])
                         and previous_line.get('x',0)+previous_line['w'] < flow_width-2*previous_line['h']
                         and line['y'] > previous_line['y']+previous_line['h']*.8)
        if paragraph_end:
            output.append('')
        elif previous is not None and line['group'] != previous:
            if previous_line is None or 'y' not in previous_line or 'y' not in line or line['y'] - (previous_line['y']+previous_line['h']) > .8*max(line['h'],previous_line['h']):
                output.append('')
        output.append(line['text'])
        previous = line['group']
        previous_line = line
    return '\n'.join(output).strip() + ('\n' if output else '')


def letter_bounds(lines, size):
    width, height = size
    anchors = [word for line in lines for word in line.get('words', []) if word['y'] < height * .4
               and re.search(r'OFICIO|CIRCULAR', word['text'], re.I)]
    if not anchors:
        return None
    first = min(anchors,key=lambda word:word['y'])
    # El destinatario puede mencionar al GAD: solo un membrete situado ANTES
    # de la identificación del oficio puede autorizar exclusiones de plantilla.
    letterhead = ' '.join(word['text'] for line in lines for word in line.get('words', [])
                          if word['y'] < first['y'] and word['y'] + word['h'] < first['y'] + height * .02).upper()
    if not all(word in letterhead for word in ('GAD', 'PARROQUIAL', 'IMANTAG')):
        return None
    codes = [word for line in lines for word in line.get('words', [])
             if re.search(r'GADPR[I1L]',word['text'],re.I) and word['x'] >= min(w['x'] for w in anchors)-20
             and abs(word['y']-first['y']) < height*.06]
    top = max(0, min(word['y'] for word in anchors+codes) - 8)
    typical = float(np.median([line['h'] for line in lines if height*.35 < line['y'] < height*.8])) if any(height*.35 < line['y'] < height*.8 for line in lines) else 20
    bottom = height
    for line in sorted(lines, key=lambda line: line['y']):
        if line['y'] < height * .85 or not re.search(r'@|www\.|administraci[oó]n|facebook|\b25\d{2}\s*\d{3}', line['text'], re.I):
            continue
        before = [other['y'] + other['h'] for other in lines if other['y'] + other['h'] < line['y']]
        if before and line['y'] - max(before) > typical * 3:
            bottom = max(top + 1, line['y'] - 8)
            break
    if top >= height * .4 or bottom - top < height * .35:
        return None
    return (0, top, width, bottom)


def stamp_boxes(image):
    array = np.array(image.convert('RGB'))
    hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, np.array([85, 30, 20]), np.array([170, 255, 210]))
    scale = max(.5, image.width / 900)
    kernel = np.ones((max(3, round(13*scale)), max(3, round(23*scale))), np.uint8)
    merged = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if (x > image.width*.45 and y < image.height*.45 and image.width*.12 < w < image.width*.6
                and image.height*.035 < h < image.height*.16 and 1.4 < w/h < 5):
            # Un bloque rectangular de tinta azul/violeta en la cabecera es candidato,
            # no una detección universal de sellos. Se conserva siempre el OCR completo.
            hull = cv2.convexHull(contour)
            if cv2.contourArea(hull) > w*h*.45:
                margin_x, margin_y = round(w*.07), round(h*.3)
                boxes.append((max(0,x-margin_x), max(0,y-margin_y), min(image.width,x+w+margin_x), min(image.height,y+h+margin_y)))
    return boxes[:3]


def project_box(box, source_size, target_size, operations):
    width, height = source_size
    angle = 0
    for operation in operations:
        match = re.search(r'inclinación (-?[\d.]+) grados', operation)
        if match:
            angle = float(match[1])
    radians = math.radians(angle)
    expanded_w = math.ceil(abs(width*math.cos(radians)) + abs(height*math.sin(radians)))
    expanded_h = math.ceil(abs(height*math.cos(radians)) + abs(width*math.sin(radians)))
    points = []
    for x, y in [(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])]:
        dx, dy = x-width/2, y-height/2
        px = math.cos(radians)*dx + math.sin(radians)*dy + expanded_w/2
        py = -math.sin(radians)*dx + math.cos(radians)*dy + expanded_h/2
        points.append((px*target_size[0]/expanded_w, py*target_size[1]/expanded_h))
    return (max(0, math.floor(min(p[0] for p in points))-4), max(0,math.floor(min(p[1] for p in points))-4),
            min(target_size[0],math.ceil(max(p[0] for p in points))+4), min(target_size[1],math.ceil(max(p[1] for p in points))+4))


def body_copy(processed, base, lines, operations):
    bounds = letter_bounds(lines, processed.size)
    if bounds is None:
        return None, []
    result = processed.copy()
    excluded = ['Membrete decorativo anterior a la identificación del oficio.']
    if bounds[3] < processed.height:
        excluded.append('Pie de contacto separado del cuerpo del oficio.')
    draw = ImageDraw.Draw(result)
    subjects = [line['y'] for line in lines if re.search(r'\bASUNTO\s*:', line['text'], re.I)]
    for box in stamp_boxes(base):
        projected = project_box(box, base.size, processed.size, operations)
        if not subjects or projected[3] >= min(subjects):
            continue
        draw.rectangle(projected, fill='white')
        excluded.append('Región auxiliar de tinta azul/violeta compatible con sello; verificar el OCR completo si se superpone a texto.')
    return result.crop(bounds), excluded


def identification_copy(processed, lines):
    """Número/fecha inclinados: bloque local, sin reconstruir palabras por contexto."""
    words = [word for line in lines for word in line.get('words', [])
             if word['y'] < processed.height*.32]
    anchors = [word for word in words if re.search(r'OFICIO|CIRCULAR', word['text'], re.I)]
    if not anchors:
        return None, None
    left = max(0, min(word['x'] for word in anchors) - 20)
    anchors += [word for word in words if word['x'] >= left and re.search(r'GADPR[I1L]',word['text'],re.I)]
    top = max(0, min(word['y'] for word in anchors) - 12)
    heights = float(np.median([word['h'] for word in anchors]))
    dates = [word for word in words if word['x'] >= left and top < word['y'] < top + heights*4
             and re.search(r'Imantag|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|20\d{2}', word['text'], re.I)]
    bottom = max(word['y']+word['h'] for word in anchors+dates) + 12
    if left < processed.width*.3 or bottom - top > processed.height*.12:
        return None, None
    nearby = [word for word in words if word['x'] >= left and top <= word['y'] <= bottom]
    right = min(processed.width,max(word['x']+word['w'] for word in nearby)+20)
    box = (left, top, right, min(processed.height,bottom))
    strip = processed.crop(box)
    gray = np.array(strip.convert('L'))
    binary = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,51,12)
    strip = Image.fromarray(binary)
    sample = Image.fromarray(binary)
    sample.thumbnail((1000,300))
    def score(angle):
        rotated = np.array(sample.rotate(angle,expand=True,fillcolor=255)) < 128
        projection = rotated.sum(axis=1).astype(float)
        return float(np.sum(projection*projection))
    initial = score(0)
    candidates = [(score(float(angle)),float(angle)) for angle in np.arange(-6,6.01,.25)]
    best, angle = max(candidates,key=lambda item:(item[0],-abs(item[1])))
    if best > initial*1.05 and abs(angle) >= .25:
        strip = strip.rotate(angle,expand=True,fillcolor='white')
    return ImageOps.expand(strip,border=20,fill=255), box


def merge_fragments(lines, width):
    result = [dict(line) for line in lines]
    changed = True
    while changed:
        changed = False
        for i, first in enumerate(result):
            for j in range(i+1,len(result)):
                second = result[j]
                left, right = sorted([first,second],key=lambda line:line['x'])
                gap = right['x']-(left['x']+left['w'])
                overlap = min(first['y']+first['h'],second['y']+second['h'])-max(first['y'],second['y'])
                if 0 <= gap < width*.2 and overlap > min(first['h'],second['h'])*.15:
                    x,y = min(first['x'],second['x']), min(first['y'],second['y'])
                    result[i] = {**first,'text':left['text']+' '+right['text'],'x':x,'y':y,
                                 'w':max(first['x']+first['w'],second['x']+second['w'])-x,
                                 'h':max(first['y']+first['h'],second['y']+second['h'])-y}
                    result.pop(j)
                    changed=True
                    break
            if changed:
                break
    return sorted(result,key=lambda line:line['y'])
