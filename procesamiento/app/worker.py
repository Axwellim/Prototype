"""Proceso aislado. Sus rutas son internas y nunca proceden del cliente HTTP."""
from pathlib import Path
import json
import sys

from .config import Settings
from .extraction import DocumentError, extract_document
from .normalization import normalize_pdf
from .composition import process_composition, archive_invitation


def main():
    source, target, config_path = map(Path, sys.argv[1:4])
    settings = Settings.model_validate_json(config_path.read_text(encoding='utf-8'))
    try:
        if settings.input_mime == 'application/zip':
            extracted = process_composition(source, target.parent, settings)
        elif not settings.transcribe:
            extracted = archive_invitation(source, target.parent / 'normalizado.pdf', settings)
        else:
            extracted = extract_document(source, settings)
        if settings.generate_pdf and settings.transcribe and settings.input_mime != 'application/zip':
            normalize_pdf(source, target.parent / 'normalizado.pdf', settings, extracted.numero_paginas)
        result = {'ok': True, 'resultado': extracted.model_dump()}
    except DocumentError as error:
        result = {'ok': False, 'codigo': error.code, 'mensaje': error.message, 'status': error.status}
    target.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
