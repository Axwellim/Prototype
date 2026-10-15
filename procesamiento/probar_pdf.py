"""Cliente local de comprobación: envía bytes, nunca rutas al servicio."""
import argparse
import json
import mimetypes
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import load_settings
from app.schemas import ProcessingResult


def main():
    parser = argparse.ArgumentParser(description='Extraer texto de PDF, JPG o PNG mediante el servicio OCR local.')
    parser.add_argument('archivo', type=Path)
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--modo', choices=['original', 'preprocesado', 'comparar'], default='original')
    parser.add_argument('--puerto', type=int, default=8002)
    args = parser.parse_args()
    if not 1024 <= args.puerto <= 65535:
        parser.error('El puerto debe estar entre 1024 y 65535.')
    settings = load_settings()
    if not args.archivo.is_file() or args.archivo.stat().st_size > settings.max_bytes:
        parser.error('El archivo no existe o supera el límite de tamaño.')
    if args.salida.exists():
        parser.error('El archivo de salida ya existe; elige otro para no sobrescribirlo.')
    mime = mimetypes.guess_type(args.archivo.name)[0]
    if mime not in ('application/pdf', 'image/jpeg', 'image/png'):
        parser.error('Selecciona un PDF, JPG, JPEG o PNG.')
    request = Request(f'http://127.0.0.1:{args.puerto}/procesar?modo=' + args.modo, data=args.archivo.read_bytes(),
                      headers={'Content-Type': mime, 'X-Processor-Token': settings.api_token})
    try:
        with urlopen(request, timeout=settings.timeout_seconds + 40) as response:
            result = ProcessingResult.model_validate_json(response.read())
    except HTTPError as error:
        print('El servicio rechazó el documento:', error.code, error.read().decode('utf-8'))
        return 1
    except URLError:
        print('No se pudo conectar con el servicio local. Inícialo en 127.0.0.1:8002.')
        return 1
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    with args.salida.open('x', encoding='utf-8') as target:
        target.write(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    print(f'Resultado: {result.estado}; páginas: {result.numero_paginas}; guardado en {args.salida}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
