"""Métricas reproducibles; nunca modifica los textos almacenados."""
import re
import unicodedata
from importlib.metadata import version

import jiwer
from pydantic import BaseModel, ConfigDict, Field


class QualityInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    referencia: str = Field(min_length=1, max_length=10000)
    variantes: dict[str, str] = Field(min_length=1, max_length=3)


def normalize(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def evaluate(data: QualityInput):
    reference = normalize(data.referencia)
    if not reference:
        raise ValueError('La referencia no puede estar vacía.')
    if any(len(text) > 10000 for text in data.variantes.values()):
        raise ValueError('Cada texto admite un máximo de 10 000 caracteres.')
    results = {}
    for name, text in data.variantes.items():
        hypothesis = normalize(text)
        word = jiwer.process_words(reference, hypothesis)
        char = jiwer.process_characters(reference, hypothesis)
        results[name] = {}
        for key, output, rate in [('wer', word, word.wer), ('cer', char, char.cer)]:
            results[name][key] = {'tasa': rate, 'sustituciones': output.substitutions,
                                 'eliminaciones': output.deletions, 'inserciones': output.insertions,
                                 'unidades_referencia': output.hits + output.substitutions + output.deletions}
    return {'motor': 'jiwer', 'version': version('jiwer'), 'politica': 'nfc-espacios-v1', 'variantes': results}
