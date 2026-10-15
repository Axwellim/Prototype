from app.signatures import closing_region, printed_lines
from app.signatures import read_closing
from PIL import Image


def line(text, x, y, h=20, confidence=95):
    words = [{'text': word, 'x': x + index * 60, 'y': y, 'w': 55, 'h': h, 'conf': confidence}
             for index, word in enumerate(text.split())]
    return {'text': text, 'x': x, 'y': y, 'w': max(60, len(words) * 60), 'h': h,
            'words': words, 'group': ('1', '1')}


def closing():
    return [line('Atentamente,', 100, 650), line('Ing. Ana Pérez', 100, 800),
            line('DIRECTORA', 100, 830), line('Sr. Luis Gómez', 100, 1000),
            line('SECRETARIO', 100, 1030), line('RECIBIDO', 700, 1400)]


def test_closing_region_requires_multiple_signers_and_one_column():
    rows = closing()
    assert closing_region(rows, (1200, 1600))[1][3] < 1400
    assert closing_region(rows[:3], (1200, 1600)) is None
    rows[3]['x'] = 750
    assert closing_region(rows, (1200, 1600)) is None


def test_body_mentions_and_many_signers_do_not_trigger_exclusions():
    rows = closing()
    rows[0]['text'] = 'Solicitamos atentamente su colaboración'
    assert closing_region(rows, (1200, 1600)) is None
    rows = closing() + [line('Sr. Otro Firmante', 100, 1100 + index * 20) for index in range(7)]
    assert closing_region(rows, (1200, 1600)) is None


def test_printed_labels_preserve_literal_names_and_partial_roles_without_reconstruction():
    rows = [line('Ing. Ximena Ñacato', 100, 800), line('PRESIDE', 100, 830),
            line('7-2 Ear', 100, 860, confidence=30), line('CENTRO DE ESTUDIOS', 100, 900)]
    assert [item['text'] for item in printed_lines(rows)] == [
        'Ing. Ximena Ñacato', 'PRESIDE', 'CENTRO DE ESTUDIOS']


def test_handwritten_suffix_is_not_attached_to_printed_name():
    row = line('Sra. Ana Pérez - < 2000 texto', 100, 800)
    assert printed_lines([row])[0]['text'] == 'Sra. Ana Pérez'


def test_without_colored_interference_keeps_complete_ocr(tmp_path):
    def unexpected_ocr(*args, **kwargs):
        raise AssertionError('No debe ejecutar pasadas adicionales sin tinta de color')
    assert read_closing(Image.new('RGB', (1200, 1600), 'white'), (1200, 1600),
                        closing(), [], tmp_path, None, unexpected_ocr) is None
