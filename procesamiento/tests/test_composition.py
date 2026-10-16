import io
import json
import zipfile
from unittest.mock import patch

import pymupdf
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.composition import archive_invitation, process_composition
from app.config import Settings
from app.extraction import DocumentError
from app.main import create_app
from app.schemas import PageResult, ProcessingResult


def pdf(label='DOCUMENTO'):
    with pymupdf.open() as doc:
        page=doc.new_page()
        for index in range(5):
            page.insert_text((50,80+index*20),label+' texto digital visible para verificar el orden de las paginas y su contenido.')
        return doc.tobytes()


def bundle(tmp_path, parts, invitation=None, compression=zipfile.ZIP_STORED):
    target=tmp_path/'entrada.zip'
    items=[{'archivo':name} for name,_ in parts]
    with zipfile.ZipFile(target,'w',compression=compression) as archive:
        archive.writestr('manifest.json',json.dumps({'documentos':items,'invitacion':{'archivo':invitation[0]} if invitation else None}))
        for name,content in parts+([invitation] if invitation else []):
            archive.writestr(name,content)
    return target


def test_independent_invitation_never_calls_extraction_or_ocr(tmp_path):
    source=tmp_path/'invitacion.pdf'; source.write_bytes(pdf('INVITACION'))
    settings=Settings(api_token='x'*40)
    with patch('app.composition.extract_document',side_effect=AssertionError('No transcribir')):
        with patch('app.extraction.recognize',side_effect=AssertionError('No OCR')):
            result=archive_invitation(source,tmp_path/'normalizado.pdf',settings)
    assert result.paginas[0].metodo=='sin_transcripcion'
    assert result.texto_completo==''
    assert (tmp_path/'normalizado.pdf').read_bytes()==source.read_bytes()


def test_pdf_and_images_preserve_order_and_invitation_is_separate(tmp_path):
    image=io.BytesIO(); Image.new('RGB',(200,100),'red').save(image,format='PNG')
    source=bundle(tmp_path,[('p000.png',image.getvalue()),('p001.pdf',pdf('CENTRO'))],('p002.pdf',pdf('INVITACION')))
    settings=Settings(api_token='x'*40,ocr_enabled=False)
    from app.extraction import extract_document
    def read(path,local):
        if local.input_mime=='image/png':
            return ProcessingResult(estado='completado',numero_paginas=1,duracion_total_ms=1,
                                    paginas=[PageResult(numero=1,metodo='digital',texto='PRIMERA IMAGEN',duracion_ms=1)],texto_completo='PRIMERA IMAGEN')
        return extract_document(path,local)
    with patch('app.composition.extract_document',side_effect=read) as engine:
        result=process_composition(source,tmp_path,settings)
    assert engine.call_count==2
    assert result.numero_paginas==2 and result.invitacion_paginas==1
    assert result.componentes_paginas==[1,1]
    assert result.paginas[0].texto=='PRIMERA IMAGEN'
    assert 'CENTRO' in result.paginas[1].texto
    assert 'INVITACION' not in result.texto_completo
    with pymupdf.open(tmp_path/'normalizado.pdf') as merged:
        assert len(merged)==2
        assert merged[0].get_images() and 'CENTRO' in merged[1].get_text()
    assert (tmp_path/'invitacion.pdf').read_bytes()==pdf_invitation_bytes(source)


def pdf_invitation_bytes(source):
    with zipfile.ZipFile(source) as archive:
        return archive.read('p002.pdf')


@pytest.mark.parametrize('parts,compression',[
    ([('p000.pdf',pdf()),('p001.pdf',pdf())],zipfile.ZIP_STORED),
    ([('../escape.pdf',pdf())],zipfile.ZIP_STORED),
    ([('p000.pdf',pdf())],zipfile.ZIP_DEFLATED),
])
def test_invalid_compositions_are_rejected_before_processing(tmp_path,parts,compression):
    source=bundle(tmp_path,parts,compression=compression)
    with patch('app.composition.extract_document',side_effect=AssertionError('No procesar')):
        with pytest.raises(DocumentError,match='composición'):
            process_composition(source,tmp_path,Settings(api_token='x'*40))


def test_http_invitation_only_and_composition_packages(tmp_path):
    settings=Settings(api_token='x'*40,ocr_enabled=False)
    with TestClient(create_app(settings),client=('127.0.0.1',42000),headers={'X-Processor-Token':'x'*40}) as client:
        original=pdf('INVITACION')
        response=client.post('/procesar?normalizar=true&transcribir=false',content=original,headers={'Content-Type':'application/pdf'})
        assert response.status_code==200,response.text
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            data=json.loads(archive.read('resultado.json'))
            assert data['texto_completo']=='' and data['paginas'][0]['metodo']=='sin_transcripcion'
            assert archive.read('documento.pdf')==original
        source=bundle(tmp_path,[('p000.pdf',pdf())],('p001.pdf',original))
        response=client.post('/procesar?normalizar=true',content=source.read_bytes(),headers={'Content-Type':'application/zip'})
        assert response.status_code==200,response.text
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            assert set(archive.namelist())=={'resultado.json','documento.pdf','invitacion.pdf'}
            data=json.loads(archive.read('resultado.json'))
            assert data['invitacion_paginas']==1 and 'INVITACION' not in data['texto_completo']
            assert archive.read('invitacion.pdf')==original
