"""Lectura local de dos bloques de firmantes; sin completar datos por contexto."""
import re
import cv2
import numpy as np
from PIL import Image

from .layout import render_lines, tsv_lines
from .signatures import NAME, ROLE
from .formal_text import consistent_role, formal_label, email_from_ocr
from pathlib import Path


def read_signature_columns(image, lines, folder, settings, recognize, detection_lines=None, context_text=None):
    width, height = image.size
    detection = detection_lines if detection_lines is not None else lines
    closing = [word for line in detection for word in line.get('words', [])
               if re.fullmatch(r'A[tf]entamente[,.:]?', word['text'].strip(), re.I) and word['y'] > height * .5]
    roles = [word for line in detection for word in line.get('words', [])
             if ROLE.match(word['text']) and word['y'] > height * .65]
    if len(closing) != 1:
        return None
    anchor = closing[0]
    left = [word for word in roles if word['x'] < width * .45 and word['y'] > anchor['y']]
    right = [word for word in roles if word['x'] > width * .5 and word['y'] > anchor['y']]
    if not left or not right or abs(left[0]['y'] - right[0]['y']) > height * .04:
        return None
    contacts = [line for line in detection if line.get('y', -1) > min(left[0]['y'], right[0]['y']) and
                re.search(r'\bC[Il1][.:]|\bCel\s*:|gmail\.com', line['text'], re.I)
                and line['y'] < height * .94]
    if not contacts:
        return None
    bottom = min(height, max(line['y'] + line['h'] for line in contacts) + 10)
    top = max(anchor['y'] + anchor['h'], int(min(left[0]['y'], right[0]['y']) - height * .025))
    array = np.asarray(image.convert('RGB')).astype(np.float32)
    blue = array[:, :, 2]
    flat = blue / np.maximum(1, cv2.GaussianBlur(blue, (0, 0), max(8, width / 100))) * 245
    flat += np.maximum(0, blue - array[:, :, 0]) * 3
    flat = Image.fromarray(np.clip(flat, 0, 255).astype(np.uint8))
    precise = None
    model_dir = getattr(settings, 'refinement_tessdata_dir', '')
    if model_dir and (Path(model_dir) / 'spa.traineddata').is_file():
        precise = settings.model_copy(update={'tessdata_dir': model_dir})
    context = context_text if context_text is not None else render_lines(detection)
    row_y = max(left[0]['y'], right[0]['y'])
    row_h = min(left[0]['h'], right[0]['h'])
    softer = Image.fromarray(np.clip(blue / np.maximum(1, cv2.GaussianBlur(blue, (0, 0), max(8, width / 100))) * 245
                                    + np.maximum(0, blue - array[:, :, 0]), 0, 255).astype(np.uint8)) if precise else None
    blocks = []
    for index, (x0, x1) in enumerate(((int(width * .1), int(width * .49)), (int(width * .51), int(width * .96)))):
        path = folder / f'firmas-columna-{index}.png'
        flat.crop((x0, top, x1, bottom)).save(path)
        recognized = tsv_lines(recognize(path, settings, tsv=True, psm=6))
        kept = []
        active = False
        for line in recognized:
            text = line['text']
            if NAME.match(text) or ROLE.match(text):
                active = True
            if active and (NAME.match(text) or ROLE.match(text) or
                           text.isupper() or re.search(r'\bC[Il1][.:]|\bCel\s*:|@|gmail\.com', text, re.I)):
                kept.append(line)
        if not any(NAME.match(line['text']) for line in kept) or not any(ROLE.match(line['text']) for line in kept):
            return None
        if precise is not None:
            role = left[0] if index == 0 else right[0]
            bands = [('name', row_y - row_h * 1.5, row_y - row_h * .1),
                     ('role', row_y - row_h * .2, row_y + row_h * .95),
                     ('continuation', row_y + row_h * .85, row_y + row_h * 2.15)]
            for kind, y0, y1 in bands:
                path = folder / f'precision-{index}-{kind}.png'
                xx0 = max(x0, int(role['x'] + row_h if kind == 'name' else role['x'] - row_h * 1.5))
                xx1 = int(x1 - (x1 - x0) * .1)
                strip = softer.crop((xx0, max(0, int(y0)), xx1, min(height, int(y1))))
                strip.resize((strip.width * 2, strip.height * 2), Image.Resampling.BICUBIC).save(path)
                candidate = recognize(path, precise, psm=7).strip().rstrip(' .,:;"“”*\'')
                if kind == 'name' and NAME.match(candidate):
                    target = next((line for line in kept if NAME.match(line['text'])), None)
                elif kind == 'role' and ROLE.match(candidate):
                    target = next((line for line in kept if ROLE.match(line['text'])), None)
                elif kind == 'continuation' and len(candidate.split()) >= 1 and candidate.isupper():
                    target = next((line for line in kept if line['text'].isupper() and not ROLE.match(line['text'])), None)
                else:
                    target = None
                if target is not None:
                    target['text'] = candidate
        for line in kept:
            text = line['text']
            if ROLE.match(text) or text.isupper():
                text = consistent_role(text, context).rstrip(' *\'"')
                text = re.sub(r'\s+[a-záéíóúüñ]{1,2}$', '', text)
                text = re.sub(r'(?<=\s)[¡¿](?=[A-Z])', '', text)
            line['text'] = formal_label(text)
        emails = [line for line in contacts if re.search(r'@|gmail\.com', line['text'], re.I)
                  and x0 <= line['x'] < x1]
        for email in emails:
            if any(re.search(r'@|gmail\.com', line['text'], re.I) for line in kept):
                continue
            path = folder / f'contacto-columna-{index}.png'
            flat.crop((x0, max(top, email['y'] - 5), x1, min(bottom, email['y'] + email['h'] + 5))).save(path)
            contact = recognize(path, settings, psm=7).strip()
            contact = email_from_ocr(contact) or email_from_ocr(email['text']) or email['text']
            kept.append({'text': contact, 'group': ('contacto', str(index))})
        blocks.append(render_lines(kept).strip())
    prefix = [line for line in lines if 'y' not in line or (line['y'] + line['h'] < anchor['y'] and
              (len(line.get('words', [])) >= 3 or
               any(word.get('conf', 0) >= 80 and len(word['text']) > 2 for word in line.get('words', []))))]
    path = folder / 'despedida-columnas.png'
    image.crop((max(0, anchor['x'] - 8), max(0, anchor['y'] - 8),
                min(width, anchor['x'] + anchor['w'] + 8), min(height, anchor['y'] + anchor['h'] + 8))).save(path)
    goodbye = recognize(path, settings, psm=7).strip()
    if not re.fullmatch(r'A[tf]entamente[,.:]?', goodbye, re.I):
        goodbye = anchor['text'].strip()
    if re.fullmatch(r'A[tf]entamente[,.:]?', goodbye, re.I):
        goodbye = 'Atentamente,'
    prefix_text = render_lines(prefix).rstrip()
    prefix_text = re.sub(r'(\bOFICIO\s+N)[?*º]', r'\1°', prefix_text, flags=re.I)
    return prefix_text + '\n\n' + goodbye + '\n\n' + '\n\n'.join(blocks) + '\n'
