import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pymupdf
import pytest
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.normalization import normalize_pdf
from app.ocr import automatic_profile
from app.main import create_app
from test_ocr import text_image, image_bytes, scanned_pdf
from test_service import make_pdf, TEXT


def test_automatic_decision_clean_low_contrast_noise_and_small_image():
    settings = Settings(api_token='x' * 40)
    clean = Image.new('RGB', (1800, 1000), 'white')
    ImageDraw.Draw(clean).rectangle((300, 300, 900, 500), fill='black')
    mode, profile, note = automatic_profile(clean, settings)
    assert mode == 'original'
    low = Image.new('RGB', clean.size, (210, 210, 210))
    ImageDraw.Draw(low).rectangle((300, 300, 900, 500), fill=(170, 170, 170))
    mode, profile, note = automatic_profile(low, settings)
    assert mode == 'preprocesado' and profile.preprocess_contrast
    assert 'contraste bajo' in note
    rng = np.random.default_rng(7)
    noisy = Image.fromarray(rng.integers(0, 256, (800, 1800), dtype=np.uint8))
    assert automatic_profile(noisy, settings)[1].preprocess_denoise
    small = clean.resize((800, 444))
    assert automatic_profile(small, settings)[1].preprocess_upscale
    assert settings.preprocess_binarize is False


@pytest.mark.parametrize('kind', ['PNG', 'JPEG'])
def test_image_pdf_preserves_dimensions_and_original(kind, tmp_path):
    source = tmp_path / 'original.bin'
    source.write_bytes(image_bytes(text_image(), kind))
    before = source.read_bytes()
    settings = Settings(api_token='x' * 40, input_mime='image/png' if kind == 'PNG' else 'image/jpeg')
    target = tmp_path / 'output.pdf'
    normalize_pdf(source, target, settings, 1)
    assert source.read_bytes() == before
    with pymupdf.open(target) as document:
        assert document.page_count == 1
        assert document[0].rect.width / document[0].rect.height == pytest.approx(1.8)
        assert document[0].get_pixmap().samples


def test_input_pdf_retained_without_rasterization(tmp_path):
    source, target = tmp_path / 'source.pdf', tmp_path / 'output.pdf'
    source.write_bytes(make_pdf([TEXT, TEXT]))
    normalize_pdf(source, target, Settings(api_token='x' * 40), 2)
    assert target.read_bytes() == source.read_bytes()
    with pymupdf.open(target) as document:
        assert '001-2026' in document[0].get_text()


@pytest.mark.parametrize('case', ['digital', 'png', 'jpg', 'mixto'])
def test_real_automatic_pdf_and_transcription_bundle(case):
    local = load_settings()
    settings = Settings(api_token='x' * 40, tesseract_cmd=local.tesseract_cmd, tessdata_dir=local.tessdata_dir)
    mime = {'png': 'image/png', 'jpg': 'image/jpeg'}.get(case, 'application/pdf')
    data = make_pdf([TEXT]) if case == 'digital' else scanned_pdf(mixed=True) if case == 'mixto' else image_bytes(text_image(), 'JPEG' if case == 'jpg' else 'PNG')
    with TestClient(create_app(settings), client=('127.0.0.1', 1234)) as client:
        response = client.post('/procesar?modo=automatico&normalizar=true', content=data,
            headers={'Content-Type': mime, 'X-Processor-Token': settings.api_token})
    assert response.status_code == 200, response.text[:200] if response.status_code != 200 else ''
    assert response.headers['content-type'] == 'application/zip'
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {'resultado.json', 'documento.pdf'}
        result = json.loads(archive.read('resultado.json'))
        with pymupdf.open(stream=archive.read('documento.pdf'), filetype='pdf') as pdf:
            assert pdf.page_count == result['numero_paginas']
        assert 'IMANTAG' in result['texto_completo'].upper()
        assert all(len(page['variantes_ocr']) == 1 for page in result['paginas'] if page['metodo'] == 'ocr')
        assert all(any('automática v4' in note for note in page['observaciones']) for page in result['paginas'] if page['metodo'] == 'ocr')
