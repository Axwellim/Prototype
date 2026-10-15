import pytest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.quality import QualityInput, evaluate


def test_known_edit_counts_and_rates():
    result = evaluate(QualityInput(referencia='hola mundo', variantes={'principal': 'hola munda'}))['variantes']['principal']
    assert result['wer'] == {'tasa': .5, 'sustituciones': 1, 'eliminaciones': 0, 'inserciones': 0, 'unidades_referencia': 2}
    assert result['cer']['tasa'] == .1
    assert result['cer']['unidades_referencia'] == 10


def test_insertions_are_not_clamped_and_empty_hypothesis_is_total_deletion():
    result = evaluate(QualityInput(referencia='a', variantes={'original': 'a b c', 'preprocesado': ''}))['variantes']
    assert result['original']['wer']['tasa'] == 2
    assert result['original']['cer']['tasa'] == 4
    assert result['preprocesado']['cer']['tasa'] == 1
    assert result['preprocesado']['wer']['tasa'] == 1


def test_normalization_preserves_meaningful_differences():
    result = evaluate(QualityInput(referencia='María\n  123', variantes={'same': 'Mari\u0301a 123', 'different': 'maria 124'}))['variantes']
    assert result['same']['cer']['tasa'] == 0
    assert result['different']['wer']['tasa'] == 1


@pytest.mark.parametrize('reference', ['', ' \n\t'])
def test_empty_reference_rejected(reference):
    with pytest.raises(ValueError):
        evaluate(QualityInput(referencia=reference, variantes={'principal': ''}))


def test_authenticated_bounded_api():
    token = 'x' * 40
    client = TestClient(create_app(Settings(api_token=token)), client=('127.0.0.1', 50000))
    data = {'referencia': 'hola', 'variantes': {'principal': 'hola'}}
    assert client.post('/evaluar', json=data).status_code == 401
    headers = {'X-Processor-Token': token}
    assert client.post('/evaluar', json=data, headers=headers).json()['variantes']['principal']['wer']['tasa'] == 0
    data['variantes']['principal'] = 'a' * 10001
    assert client.post('/evaluar', json=data, headers=headers).status_code == 422
    assert client.post('/evaluar', content=b' ' * 250001, headers=headers).status_code == 413
    assert client.post('/evaluar', json={'ruta': 'C:/secreto'}, headers=headers).status_code == 422
    assert client.post('/evaluar', json={'referencia': 'hola', 'variantes': {'principal': ''}}, headers=headers).status_code == 200


def test_quality_and_ocr_share_concurrency_lock():
    token = 'x' * 40
    client = TestClient(create_app(Settings(api_token=token)), client=('127.0.0.1', 50000))
    entered, release = threading.Event(), threading.Event()
    def blocked(data):
        entered.set()
        assert release.wait(5)
        return evaluate(data)
    headers = {'X-Processor-Token': token}
    with patch('app.main.evaluate', side_effect=blocked), ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(client.post, '/evaluar', json={'referencia': 'a', 'variantes': {'principal': 'a'}}, headers=headers)
        try:
            assert entered.wait(5)
            assert client.post('/procesar', content=b'%PDF-', headers={**headers, 'Content-Type': 'application/pdf'}).status_code == 503
            assert client.post('/evaluar', json={}, headers=headers).status_code == 503
        finally:
            release.set()
        assert future.result().status_code == 200
