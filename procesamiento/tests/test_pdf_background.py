import io
from unittest.mock import patch

import pymupdf
from PIL import Image, ImageDraw

from app.config import Settings
from app.extraction import extract_document
from app.pdf_background import has_clear_background_with_visible_text
from app.schemas import OcrVariant


def make_document(scanned=False, hidden=False, footer_only=False, extra_body=False, signature=False):
    image=Image.new('RGB',(1200,1600),(235,242,239))
    if scanned:
        ImageDraw.Draw(image).rectangle((250,500,950,520),fill='black')
    stream=io.BytesIO();image.save(stream,format='PNG')
    document=pymupdf.open();page=document.new_page(width=600,height=800)
    page.insert_image(page.rect,stream=stream.getvalue())
    text='Texto digital visible para comprobar el contenido completo del documento institucional.'
    for index in range(7):
        y=650+index*8 if footer_only else 110+index*100
        page.insert_text((50,y),text,fontsize=10,render_mode=3 if hidden else 0)
    if extra_body or signature:
        small=io.BytesIO();Image.new('RGB',(100,60),'black').save(small,format='PNG')
        box=pymupdf.Rect(200,300,300,360) if extra_body else pymupdf.Rect(200,620,300,660)
        page.insert_image(box,stream=small.getvalue())
    return document


def test_visible_text_and_clear_background_keep_native_text_even_with_signature(tmp_path):
    settings=Settings(api_token='x'*40)
    with make_document(signature=True) as doc:
        assert has_clear_background_with_visible_text(doc[0],settings)
        path=tmp_path/'native.pdf';doc.save(path)
    with patch('app.extraction.recognize',side_effect=AssertionError('No debe sustituir texto nativo por OCR')):
        result=extract_document(path,settings)
    assert result.paginas[0].metodo=='digital'
    assert 'Texto digital visible' in result.texto_completo
    assert not result.paginas[0].variantes_ocr


def test_hidden_text_does_not_authorize_background_exception():
    with make_document(hidden=True) as doc:
        assert not has_clear_background_with_visible_text(doc[0],Settings(api_token='x'*40))


def test_text_only_in_footer_does_not_authorize_background_exception():
    with make_document(footer_only=True) as doc:
        assert not has_clear_background_with_visible_text(doc[0],Settings(api_token='x'*40))


def test_rasterized_ink_in_body_still_requires_ocr(tmp_path):
    settings=Settings(api_token='x'*40)
    with make_document(scanned=True) as doc:
        assert not has_clear_background_with_visible_text(doc[0],settings)
        path=tmp_path/'scan.pdf';doc.save(path)
    variant=OcrVariant(modo='original',texto='Contenido OCR',duracion_ms=1)
    with patch('app.extraction.recognize',return_value=([variant],[])) as engine:
        result=extract_document(path,settings)
    assert engine.call_count==1
    assert result.paginas[0].metodo=='ocr'


def test_additional_image_in_body_is_not_ignored():
    with make_document(extra_body=True) as doc:
        assert not has_clear_background_with_visible_text(doc[0],Settings(api_token='x'*40))


def test_optional_background_analysis_failure_falls_back_to_ocr(tmp_path):
    settings=Settings(api_token='x'*40)
    with make_document() as doc:
        path=tmp_path/'fallback.pdf';doc.save(path)
    variant=OcrVariant(modo='original',texto='Contenido OCR',duracion_ms=1)
    with patch('app.extraction.has_clear_background_with_visible_text',side_effect=ValueError('No concluyente')):
        with patch('app.extraction.recognize',return_value=([variant],[])) as engine:
            result=extract_document(path,settings)
    assert engine.call_count==1
    assert result.paginas[0].metodo=='ocr'


def test_repeated_small_header_requires_document_evidence():
    settings=Settings(api_token='x'*40)
    with make_document() as doc:
        small=io.BytesIO();Image.new('RGB',(60,30),'black').save(small,format='PNG')
        xref=doc[0].insert_image(pymupdf.Rect(50,20,110,50),stream=small.getvalue())
        assert not has_clear_background_with_visible_text(doc[0],settings)
        assert has_clear_background_with_visible_text(doc[0],settings,set(),{xref})


def test_sparse_final_page_needs_verified_background_and_visible_text():
    settings=Settings(api_token='x'*40)
    with make_document() as doc:
        background=doc[0].get_images()[0][0]
        page=doc.new_page(width=600,height=800)
        page.insert_image(page.rect,xref=background)
        for index in range(3):
            page.insert_text((50,300+index*100),'Texto visible de las partes del convenio y sus representantes legales.',fontsize=10)
        assert not has_clear_background_with_visible_text(doc[1],settings,set())
        verified=set()
        assert has_clear_background_with_visible_text(doc[0],settings,verified)
        assert has_clear_background_with_visible_text(doc[1],settings,verified)
        hidden=doc.new_page(width=600,height=800)
        hidden.insert_image(hidden.rect,xref=background)
        hidden.insert_text((50,300),'Texto oculto que nunca debe autorizar lectura digital.',render_mode=3)
        assert not has_clear_background_with_visible_text(doc[2],settings,verified)


def test_signature_above_lower_zone_requires_verified_background_and_closing():
    settings=Settings(api_token='x'*40)
    with make_document() as doc:
        verified=set()
        assert has_clear_background_with_visible_text(doc[0],settings,verified)
        page=doc[0]
        small=io.BytesIO();Image.new('RGB',(60,30),'black').save(small,format='PNG')
        page.insert_image(pymupdf.Rect(50,410,110,440),stream=small.getvalue())
        assert not has_clear_background_with_visible_text(page,settings,verified)
        page.insert_text((50,390),'Atentamente;',fontsize=10)
        assert not has_clear_background_with_visible_text(page,settings,set())
        assert has_clear_background_with_visible_text(page,settings,verified)
