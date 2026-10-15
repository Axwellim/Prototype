from unittest.mock import Mock, patch
from PIL import Image
from app.signature_columns import read_signature_columns
from test_signatures import line


def source():
    return [line('Párrafo final conservado.',100,600),line(' Atentamente,',400,1050),
            line('PRESIDENTA',100,1200),line('PRESIDENTE',600,1200),
            line('CI. 123456',100,1300),line('Cel: 0123456',600,1340)]


def test_two_columns_preserve_block_order_and_literal_uncertain_readings(tmp_path):
    left = [line('Ing. Ana Pérex',10,10),line('PRESIDENTA',10,40),line('CI. 123456',10,70)]
    right = [line('Sr. Luis Gómez',10,10),line('PRESIDENTE',10,40),line('Cel: 0123456',10,70)]
    with patch('app.signature_columns.tsv_lines',side_effect=[left,right]):
        text = read_signature_columns(Image.new('RGB',(1000,1600),'white'),source(),tmp_path,None,Mock(return_value='Atentamente,'))
    assert text.startswith('Párrafo final conservado.')
    assert text.index('Ana Pérex') < text.index('CI. 123456') < text.index('Luis Gómez')
    assert 'Pérez' not in text


def test_missing_name_or_missing_second_column_keeps_existing_reading(tmp_path):
    engine = Mock(return_value='')
    image = Image.new('RGB',(1000,1600),'white')
    with patch('app.signature_columns.tsv_lines',return_value=[line('PRESIDENTA',10,20)]):
        assert read_signature_columns(image,source(),tmp_path,None,engine) is None
    assert read_signature_columns(image,source()[:3],tmp_path,None,engine) is None


def test_configured_precision_model_refines_names_from_optical_output(tmp_path):
    from app.config import Settings
    (tmp_path/'spa.traineddata').write_bytes(b'modelo simulado')
    config = Settings(api_token='x'*40, refinement_tessdata_dir=str(tmp_path))
    left = [line('Ing. Ana Pérex',10,10),line('PRESIDENTA',10,40),line('CI. 123456',10,70)]
    right = [line('Sr. Luis Gómez',10,10),line('PRESIDENTE',10,40),line('Cel: 0123456',10,70)]
    def optical(path, settings, **kwargs):
        if path.name == 'precision-0-name.png':
            assert settings.tessdata_dir == str(tmp_path)
            return 'Ing. Ana Pérez'
        return 'Atentamente,'
    with patch('app.signature_columns.tsv_lines',side_effect=[left,right]):
        text = read_signature_columns(Image.new('RGB',(1000,1600),'white'),source(),tmp_path,config,optical)
    assert 'Ing. Ana Pérez' in text
    assert 'Ana Pérex' not in text
    assert text.startswith('Párrafo final conservado.')
