import io
from pathlib import Path
from unittest.mock import patch
import subprocess

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.config import ROOT, Settings, load_settings
from app.extraction import DocumentError, extract_document
from app.ocr import OcrError, preprocess, recognize, tesseract

TOKEN = 'clave-de-prueba-local-de-32-caracteres'


def text_image(invitation=False):
    image = Image.new('RGB', (1800, 1000), '#f1f7fa' if invitation else 'white')
    draw = ImageDraw.Draw(image)
    fonts = [Path('C:/Windows/Fonts/arial.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]
    font_path = next((path for path in fonts if path.exists()), None)
    if font_path is None:
        raise RuntimeError('Se requiere Arial o DejaVu Sans para las pruebas sintéticas.')
    font = ImageFont.truetype(str(font_path), 48)
    if invitation:
        draw.rectangle((0, 0, 1800, 110), fill='#174e49')
        draw.ellipse((1400, 200, 1700, 500), fill='#e6ac43')
    text = ['GAD PARROQUIAL RURAL DE IMANTAG', 'Oficio 001-2026-GADPRI',
            'Imantag, 14 de octubre de 2026', 'Señora María Pérez',
            'Invitación a reunión institucional', 'Revisión de documentos y planificación',
            'Lugar: salón parroquial. Hora: 10:00.']
    for index, line in enumerate(text):
        draw.text((80, 160 + index * 100), line, fill='black', font=font)
    return image


def image_bytes(image, kind='PNG', **kwargs):
    output = io.BytesIO()
    image.save(output, format=kind, **kwargs)
    return output.getvalue()


def scanned_pdf(pages=1, mixed=False):
    with pymupdf.open() as document:
        if mixed:
            page = document.new_page()
            page.insert_text((40, 50), 'GAD Parroquial Rural de Imantag\nOficio DIGITAL-2026\nSe convoca a la reunion institucional de planificacion y revision documental.\nFecha: 14 de octubre de 2026.\nSecretaria parroquial y autoridades invitadas.')
        picture = image_bytes(text_image())
        for _ in range(pages):
            page = document.new_page(width=720, height=400)
            page.insert_image(page.rect, stream=picture)
        return document.tobytes()


@pytest.fixture
def settings():
    local = load_settings()
    return Settings(api_token=TOKEN, tesseract_cmd=local.tesseract_cmd,
                    tessdata_dir=local.tessdata_dir, ocr_enabled=True)


@pytest.mark.parametrize('case,mime', [
    ('escaneado1','application/pdf'), ('escaneado2','application/pdf'),
    ('mixto','application/pdf'), ('jpg','image/jpeg'), ('png','image/png'), ('invitacion','image/png')])
def test_real_spanish_ocr_formats(case, mime, settings, tmp_path):
    if case.startswith('escaneado'):
        data = scanned_pdf(pages=2 if case.endswith('2') else 1)
    elif case == 'mixto':
        data = scanned_pdf(mixed=True)
    else:
        data = image_bytes(text_image(invitation=case == 'invitacion'), 'JPEG' if case == 'jpg' else 'PNG')
    path = tmp_path / 'original.bin'
    path.write_bytes(data)
    settings.input_mime = mime
    result = extract_document(path, settings)
    assert result.estado == 'completado'
    assert result.numero_paginas == (2 if case in ('escaneado2','mixto') else 1)
    ocr_pages = [page for page in result.paginas if page.metodo == 'ocr']
    assert ocr_pages
    assert all('IMANTAG' in page.texto.upper() for page in ocr_pages)
    assert all('001-2026' in page.texto for page in ocr_pages)
    if case == 'mixto':
        assert [page.metodo for page in result.paginas] == ['digital', 'ocr']
        assert 'DIGITAL-2026' not in result.paginas[1].texto
        assert result.texto_completo.count('DIGITAL-2026') == 1
    assert path.read_bytes() == data
    assert not list(tmp_path.glob('imantag-ocr-*'))


def test_real_comparison_returns_two_independent_results(settings, tmp_path):
    source = tmp_path / 'comparison.png'
    source.write_bytes(image_bytes(text_image()))
    settings.input_mime = 'image/png'
    settings.ocr_mode = 'comparar'
    result = extract_document(source, settings)
    page = result.paginas[0]
    assert [variant.modo for variant in page.variantes_ocr] == ['original', 'preprocesado']
    assert page.texto == page.variantes_ocr[0].texto
    assert page.variantes_ocr[1].operaciones
    assert all('IMANTAG' in variant.texto.upper() for variant in page.variantes_ocr)
    assert not any('precisión' in observation for observation in page.observaciones)


def test_blank_image_ocr_does_not_invent_text(settings, tmp_path):
    source = tmp_path / 'blank.png'
    source.write_bytes(image_bytes(Image.new('RGB', (1000, 600), 'white')))
    settings.input_mime = 'image/png'
    result = extract_document(source, settings)
    assert not result.paginas[0].texto.strip()
    assert any('No se reconoció texto' in note for note in result.paginas[0].observaciones)


def test_corrupt_mismatched_and_oversized_images(settings, tmp_path):
    settings.input_mime = 'image/png'
    source = tmp_path / 'bad.png'
    for data in [b'not an image', image_bytes(text_image(), 'JPEG')]:
        source.write_bytes(data)
        with pytest.raises(DocumentError):
            extract_document(source, settings)
    source.write_bytes(image_bytes(text_image()))
    settings.max_image_pixels = 10000
    with pytest.raises(DocumentError):
        extract_document(source, settings)


def test_exif_orientation_is_corrected_in_copy(settings, tmp_path):
    original = text_image()
    turned = original.transpose(Image.Transpose.ROTATE_90)
    exif = Image.Exif()
    exif[274] = 6
    data = image_bytes(turned, 'JPEG', exif=exif)
    source = tmp_path / 'exif.jpg'
    source.write_bytes(data)
    settings.input_mime = 'image/jpeg'
    result = extract_document(source, settings)
    assert 'IMANTAG' in result.paginas[0].texto.upper()
    assert source.read_bytes() == data


def test_optional_filters_keep_source_pixels(settings):
    original = text_image().resize((900, 500)).rotate(2, fillcolor='white')
    before = original.tobytes()
    settings.preprocess_denoise = True
    settings.preprocess_binarize = True
    processed, operations = preprocess(original, settings)
    assert original.tobytes() == before
    assert processed.width * processed.height <= settings.max_image_pixels
    assert any('binarización' in operation for operation in operations)
    assert any('ruido' in operation for operation in operations)
    assert any('inclinación' in operation for operation in operations)


def test_osd_rotation_is_applied_only_with_sufficient_confidence(settings):
    settings.ocr_mode = 'original'
    image = text_image()
    with patch('app.ocr.tesseract', side_effect=['Rotate: 90\nOrientation confidence: 12.0', 'texto OCR']) as engine:
        variants, notes = recognize(image, settings)
    assert variants[0].texto == 'texto OCR'
    assert any('Orientación corregida' in note for note in notes)


def test_missing_language_and_timeout_are_explicit(settings, tmp_path):
    mock = subprocess.CompletedProcess([], 1, stdout=b'', stderr=b'Failed loading language spa')
    with patch('app.ocr.subprocess.run', return_value=mock):
        with pytest.raises(OcrError) as error:
            tesseract(tmp_path/'image.png', settings)
    assert error.value.code == 'idioma_no_disponible'
    with patch('app.ocr.subprocess.run', side_effect=subprocess.TimeoutExpired('tesseract', 1)):
        with pytest.raises(OcrError) as error:
            tesseract(tmp_path/'image.png', settings)
    assert error.value.status == 504


def test_real_ocr_through_fastapi_worker(settings):
    with TestClient(__import__('app.main', fromlist=['create_app']).create_app(settings),
                    client=('127.0.0.1', 1), headers={'X-Processor-Token': TOKEN}) as client:
        result = client.post('/procesar?modo=comparar', content=image_bytes(text_image()), headers={'Content-Type':'image/png'})
        assert result.status_code == 200, result.text
        assert result.json()['paginas'][0]['metodo'] == 'ocr'
        assert len(result.json()['paginas'][0]['variantes_ocr']) == 2
        assert client.post('/procesar?modo=invalido', content=b'x', headers={'Content-Type':'image/png'}).status_code == 422


def test_render_pixel_limit_prevents_large_pdf_allocation(settings, tmp_path):
    source = tmp_path / 'large.pdf'
    with pymupdf.open() as document:
        document.new_page(width=5000, height=5000)
        source.write_bytes(document.tobytes())
    with pytest.raises(DocumentError) as error:
        extract_document(source, settings)
    assert error.value.code == 'pixeles_excedidos'


def test_animated_png_is_rejected(settings, tmp_path):
    source = tmp_path / 'animated.png'
    Image.new('RGB', (100,100), 'white').save(source, save_all=True, append_images=[Image.new('RGB',(100,100),'black')], format='PNG', duration=100)
    settings.input_mime = 'image/png'
    with pytest.raises(DocumentError) as error:
        extract_document(source, settings)
    assert error.value.code == 'imagen_animada'


def test_windows_timeout_cleanup_kills_descendant_processes(tmp_path):
    import os
    import sys
    import time
    import ctypes
    from app.main import stop_process_tree
    if os.name != 'nt':
        pytest.skip('La limpieza de procesos Windows se verifica solo en Windows.')
    pid_file = tmp_path / 'child.pid'
    code = ('import subprocess,sys,time,pathlib; '
            'p=subprocess.Popen([sys.executable,"-c","import time; time.sleep(30)"]); '
            'pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(30)')
    process = subprocess.Popen([sys.executable, '-c', code, str(pid_file)],
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists()
        child_pid = int(pid_file.read_text())
        stop_process_tree(process)
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x1000, False, child_pid)
        if handle:
            try:
                exit_code = ctypes.c_ulong()
                assert kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                assert exit_code.value != 259  # STILL_ACTIVE
            finally:
                kernel.CloseHandle(handle)
    finally:
        if process.poll() is None:
            stop_process_tree(process)
