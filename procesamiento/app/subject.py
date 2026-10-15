"""Relectura local del asunto impreso, sin vocabulario de documentos particulares."""
import re
from pathlib import Path

from rapidfuzz.distance import Levenshtein

def refine_subject(image, lines, directory, settings, engine):
    start = next((i for i, line in enumerate(lines) if re.match(r'^ASUNTO\s*:', line['text'], re.I)), None)
    if start is None:
        return lines
    selected = [lines[start]]
    for line in lines[start+1:]:
        previous = selected[-1]
        if ('y' not in line or 'y' not in previous or
                line['y']-previous['y']-previous['h'] > max(line['h'],previous['h'])*1.5 or
                re.match(r'^De (?:mi|nuestra) consideraci', line['text'], re.I)):
            break
        selected.append(line)
    old = ' '.join(line['text'] for line in selected)
    text = old
    # Una letra aislada dentro de un asunto en mayúsculas indica posible fragmentación.
    suspicious = re.search(r'\b[A-ZÁÉÍÓÚÜÑ]{2,}\s+[a-z][A-ZÁÉÍÓÚÜÑ]{1,}\b', old)
    if suspicious:
        left=min(line['x'] for line in selected)
        top=min(line['y'] for line in selected)
        right=max(line['x']+line['w'] for line in selected)
        bottom=max(line['y']+line['h'] for line in selected)
        path=Path(directory)/'asunto.png'
        crop=image.crop((max(0,left-12),max(0,top-12),min(image.width,right+12),min(image.height,bottom+12)))
        crop.save(path)
        precise=settings
        if settings.refinement_tessdata_dir and (Path(settings.refinement_tessdata_dir)/'spa.traineddata').is_file():
            precise=settings.model_copy(update={'tessdata_dir':settings.refinement_tessdata_dir})
        candidate=' '.join(engine(path,precise,psm=6).split())
        if candidate.endswith(',') and crop.width*crop.height*4 <= settings.max_image_pixels:
            crop.resize((crop.width*2,crop.height*2)).save(path)
            enlarged=' '.join(engine(path,precise,psm=6).split())
            if enlarged.endswith('.') and enlarged[:-1] == candidate[:-1]:
                candidate=enlarged
        if (re.match(r'^ASUNTO\s*:',candidate,re.I) and
                Levenshtein.normalized_distance(old,candidate)<.15 and
                not re.search(r'\b[A-ZÁÉÍÓÚÜÑ]{2,}\s+[a-z][A-ZÁÉÍÓÚÜÑ]{1,}\b',candidate)):
            text=candidate
    return lines[:start]+[{**selected[0],'text':text}]+lines[start+len(selected):]


def normalize_office_number(text):
    return re.sub(r'(\bOFICIO(?:\s+CIRCULAR)?\s+N)[”"*?º](?=\s+[A-Z]{2,}-\d)',r'\1°',text,flags=re.I)
