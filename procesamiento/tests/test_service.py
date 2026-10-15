from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import subprocess

import httpx
import pymupdf
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.extraction import DocumentError, extract_pdf
from app.main import create_app, run_worker
from app.schemas import ProcessingResult

TOKEN = 'clave-de-prueba-local-de-32-caracteres'
TEXT = ('GAD Parroquial Rural de Imantag\nOficio N.º 001-2026-GADPRI\n'
        'Imantag, 14 de octubre de 2026\nSeñora María Pérez:\n'
        'Se convoca a la reunión de planificación institucional y revisión de documentos.\n')


def make_pdf(texts):
    with pymupdf.open() as document:
        for text in texts:
            page = document.new_page()
            if text is not None:
                page.insert_text((40, 50), text, fontsize=11)
        return document.tobytes()


@pytest.fixture
def settings():
    return Settings(api_token=TOKEN, ocr_enabled=False)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings), client=('127.0.0.1', 42000),
                    headers={'X-Processor-Token': TOKEN}) as value:
        yield value


def post(client, content):
    return client.post('/procesar', content=content, headers={'Content-Type': 'application/pdf'})


def test_digital_spanish_preserves_numbers_dates_and_names(client):
    result = post(client, make_pdf([TEXT]))
    assert result.status_code == 200, result.text
    data = result.json()
    assert data['estado'] == 'completado'
    assert data['numero_paginas'] == 1
    assert data['paginas'][0]['metodo'] == 'digital'
    for expected in ['001-2026-GADPRI', '14 de octubre de 2026', 'María Pérez']:
        assert expected in data['paginas'][0]['texto']
    assert data['duracion_total_ms'] >= 0
    ProcessingResult.model_validate(data)


def test_multiple_pages_keep_separation(client):
    data = post(client, make_pdf([TEXT, TEXT.replace('001-2026', '002-2026')])).json()
    assert data['numero_paginas'] == 2
    assert [page['numero'] for page in data['paginas']] == [1, 2]
    assert data['texto_completo'] == '\f'.join(page['texto'] for page in data['paginas'])
    assert '002-2026' not in data['paginas'][0]['texto']


def test_blank_and_sparse_text_require_ocr(client):
    result = post(client, make_pdf([None, '123', TEXT])).json()
    assert result['estado'] == 'requiere_ocr'
    assert [page['metodo'] for page in result['paginas']] == ['requiere_ocr', 'requiere_ocr', 'digital']
    assert result['paginas'][0]['texto'] == ''
    assert '123' in result['paginas'][1]['texto']


def test_large_image_with_digital_footer_is_not_assumed_digital(client):
    with pymupdf.open() as document:
        page = document.new_page()
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
        pixmap.clear_with(255)
        page.insert_image(page.rect, pixmap=pixmap)
        page.insert_text((40, 50), TEXT)
        data = document.tobytes()
    result = post(client, data).json()
    assert result['paginas'][0]['metodo'] == 'requiere_ocr'
    assert any('imagen' in reason for reason in result['paginas'][0]['observaciones'])


@pytest.mark.parametrize('data', [b'', b'<?php echo 1;', b'%PDF-1.4\ncorrupto\n%%EOF'])
def test_empty_wrong_format_and_corrupt_pdf(client, data):
    assert post(client, data).status_code == 422


def test_encrypted_pdf(client):
    with pymupdf.open() as document:
        document.new_page()
        data = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='owner-test', user_pw='user-test')
    result = post(client, data)
    assert result.status_code == 422
    assert result.json()['detail']['codigo'] == 'pdf_cifrado'


def test_page_limit(settings):
    settings.max_pages = 1
    with TestClient(create_app(settings), client=('127.0.0.1', 1), headers={'X-Processor-Token': TOKEN}) as client:
        result = post(client, make_pdf([TEXT, TEXT]))
    assert result.status_code == 422
    assert result.json()['detail']['codigo'] == 'paginas_excedidas'


def test_file_size_limit_in_header_and_stream(settings):
    settings.max_bytes = 1024
    with TestClient(create_app(settings), client=('127.0.0.1', 1), headers={'X-Processor-Token': TOKEN}) as client:
        assert post(client, b'x' * 1025).status_code == 413
        assert post(client, iter([b'x' * 512, b'x' * 513])).status_code == 413
        assert client.get('/salud').status_code == 200


def test_text_output_limit(settings):
    settings.max_text_chars = 100
    with TestClient(create_app(settings), client=('127.0.0.1', 1), headers={'X-Processor-Token': TOKEN}) as client:
        assert post(client, make_pdf([TEXT])).json()['detail']['codigo'] == 'texto_excedido'


def test_credentials_loopback_and_no_arbitrary_paths(client, settings):
    assert client.get('/salud', headers={'X-Processor-Token': 'incorrecta'}).status_code == 401
    assert client.post('/procesar', json={'ruta': 'C:/Windows/win.ini'}).status_code == 415
    with TestClient(create_app(settings), client=('192.168.1.50', 1), headers={'X-Processor-Token': TOKEN}) as remote:
        assert remote.get('/salud').status_code == 403
    assert client.get('/docs').status_code == 404


def test_original_is_unchanged_and_thresholds_configurable(tmp_path, settings):
    source = tmp_path / 'original.pdf'
    original = make_pdf(['Oficio 001'])
    source.write_bytes(original)
    assert extract_pdf(source, settings).estado == 'requiere_ocr'
    settings.min_chars, settings.min_words = 1, 1
    assert extract_pdf(source, settings).estado == 'completado'
    assert source.read_bytes() == original


def test_worker_timeout(settings, tmp_path):
    with patch('app.main.subprocess.Popen') as process, patch('app.main.stop_process_tree'):
        process.return_value.communicate.side_effect = subprocess.TimeoutExpired('worker', 1)
        with pytest.raises(HTTPException) as caught:
            run_worker(tmp_path, settings)
    assert caught.value.status_code == 504


def test_concurrency_rejected_and_temporaries_cleaned(client):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from app.main import run_worker as original_worker
    entered, release = threading.Event(), threading.Event()
    directories = []

    def slow_worker(directory, settings):
        directories.append(directory)
        entered.set()
        assert release.wait(10)
        return original_worker(directory, settings)

    with patch('app.main.run_worker', side_effect=slow_worker), ThreadPoolExecutor() as pool:
        first = pool.submit(post, client, make_pdf([TEXT]))
        try:
            assert entered.wait(10)
            assert post(client, make_pdf([TEXT])).status_code == 503
            assert client.get('/salud').status_code == 200
        finally:
            release.set()
        assert first.result(timeout=15).status_code == 200
    assert directories and all(not directory.exists() for directory in directories)


def test_schema_rejects_inconsistent_page_count():
    with pytest.raises(ValidationError):
        ProcessingResult(estado='completado', numero_paginas=2, duracion_total_ms=1,
                         paginas=[], texto_completo='')


def test_repaired_pdf_is_rejected(client):
    data = make_pdf([TEXT])
    broken = data[:data.rfind(b'xref\n')]
    assert post(client, broken).status_code == 422


def test_lock_is_released_after_invalid_pdf(client):
    assert post(client, b'%PDF-1.4\nno valido\n%%EOF').status_code == 422
    assert post(client, make_pdf([TEXT])).status_code == 200


def test_configuration_requires_a_real_service_key():
    with pytest.raises(ValidationError):
        Settings(api_token='')
    with pytest.raises(ValidationError):
        Settings(api_token=TOKEN, max_pages=0)


def test_failed_worker_is_reported_without_internal_details(settings, tmp_path):
    with patch('app.main.subprocess.Popen') as process:
        process.return_value.returncode = 1
        with pytest.raises(HTTPException) as caught:
            run_worker(tmp_path, settings)
    assert caught.value.status_code == 500
    assert str(tmp_path) not in str(caught.value.detail)


def test_temporary_storage_failure_is_structured_and_releases_lock(client):
    with patch('app.main.TemporaryDirectory', side_effect=OSError('fallo interno de prueba')):
        response = post(client, make_pdf([TEXT]))
    assert response.status_code == 503
    assert 'fallo interno' not in response.text
    assert post(client, make_pdf([TEXT])).status_code == 200
