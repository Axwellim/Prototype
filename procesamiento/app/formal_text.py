"""Correcciones acotadas de formato y consistencia, sin repertorio de nombres."""
from collections import Counter
import re
import unicodedata
from rapidfuzz.distance import Levenshtein


def folded(text):
    return ''.join(char for char in unicodedata.normalize('NFD', text.upper()) if not unicodedata.combining(char))


def consistent_role(text, context):
    words = re.findall(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}', context)
    counts = Counter(folded(word) for word in words)
    lexicon = {}
    for word, _ in Counter(word.upper() for word in words).most_common():
        if counts[folded(word)] >= 2:
            lexicon.setdefault(folded(word), word)
    def repair(match):
        token = match[0]
        key = folded(token)
        if re.match(r'PRESID|VICEPRESID|SECRETAR|TESOR|DIRECTOR|COORDINADOR|VOCAL', key) or key in {
                'PARROQUIAL', 'PROVINCIAL', 'COMUNIDAD', 'GOBIERNO', 'AUTONOMO', 'DESCENTRALIZADO', 'RURAL', 'PERIODO'}:
            return token
        if key in lexicon:
            return lexicon[key]
        limit = 1 if len(key) < 7 else 2
        candidates = [word for word in lexicon if Levenshtein.distance(key, word) <= limit]
        return lexicon[candidates[0]] if len(candidates) == 1 else token
    return re.sub(r'[A-ZÁÉÍÓÚÜÑ]{3,}', repair, text)


def formal_label(text):
    text = re.sub(r'^[IÍ]ng\.?\s+', 'Ing. ', text)
    text = re.sub(r'^[Cc][Il1][.:]\s*(?=\d)', 'CI. ', text)
    text = re.sub(r'(?<=\d)[\s.—–-]+$', '', text)
    return text


def email_from_ocr(text):
    # Solo delimitadores visualmente confundidos; no completa usuario ni dominio.
    text = re.sub(r'(?:M\)|\([QOD0]|\(2)\s*(?=[a-zA-Z0-9.-]+\.[A-Za-z]{2,})', '@', text)
    text = re.sub(r'\s*@\s*', '@', text)
    if '@' not in text:
        text = re.sub(r"(?<=[A-Za-z0-9])['’](?=[A-Za-z0-9.-]+\.[A-Za-z]{2,})", '@', text)
    if '@' not in text and '/' in text:
        suffix = text.rsplit('/', 1)[-1].strip()
        match = re.fullmatch(r'([A-Za-z0-9._%+-]+)\s+([A-Za-z0-9.-]+\.[A-Za-z]{2,})', suffix)
        if match:
            text = text.rsplit('/', 1)[0] + '/ ' + match[1] + '@' + match[2]
    matches = re.findall(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
    return matches[0] if len(matches) == 1 else None
