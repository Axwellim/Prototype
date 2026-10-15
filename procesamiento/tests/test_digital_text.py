from unittest.mock import Mock

from PIL import Image
import pymupdf

from app.config import Settings
from app.digital_text import expand_ligatures, repair_digital_text


class Page:
    rect = pymupdf.Rect(0, 0, 600, 800)

    def __init__(self, words, fonts=('Fuente',)):
        self.words, self.fonts = words, fonts

    def get_text(self, kind):
        if kind == 'words':
            return [(10, 20 + i * 20, 130, 35 + i * 20, text) for i, text in enumerate(self.words)]
        return {'blocks': [{'lines': [{'spans': [{'font': font, 'text': 'Ɵ'} for font in self.fonts]}]}]}

    def get_pixmap(self, **kwargs):
        return Image.new('RGB', (600, 75), 'white')


def settings(**changes):
    return Settings(api_token='x' * 40, **changes)


def test_only_typographic_ligatures_expand_without_general_nfkc():
    assert expand_ligatures('ﬁ ﬂ ﬃ ﬀ ² ① Ɵ') == 'fi fl ffi ff ² ① Ɵ'


def test_mapping_requires_three_distinct_optically_matching_words(tmp_path):
    page = Page(['acƟvo', 'moƟvo', 'Ɵpo'])
    engine = Mock(side_effect=['activo\n', 'motivo\n', 'tipo\n'])
    text, notes = repair_digital_text(page, 'acƟvo moƟvo Ɵpo', settings(), engine, tmp_path)
    assert text == 'activo motivo tipo'
    assert len(notes) == 1
    assert engine.call_count == 3


def test_a_real_symbol_or_disagreement_is_preserved(tmp_path):
    page = Page(['acƟvo', 'moƟvo', 'Ɵpo'])
    engine = Mock(return_value='acƟvo')
    text, notes = repair_digital_text(page, 'acƟvo moƟvo Ɵpo', settings(), engine, tmp_path)
    assert text == 'acƟvo moƟvo Ɵpo'
    assert notes
    assert engine.call_count == 1


def test_isolated_symbols_mixed_fonts_and_repeated_word_do_not_authorize_mapping(tmp_path):
    engine = Mock(side_effect=AssertionError('No debe reconocer estas regiones'))
    for page, text in [(Page(['Ɵ']), 'Ɵ'), (Page(['acƟvo'] * 3), 'acƟvo acƟvo acƟvo'),
                       (Page(['acƟvo', 'moƟvo', 'Ɵpo'], ('Una', 'Otra')), 'acƟvo moƟvo Ɵpo')]:
        assert repair_digital_text(page, text, settings(), engine, tmp_path)[0] == text


def test_disabled_or_failed_optical_check_keeps_source_text(tmp_path):
    page = Page(['acƟvo', 'moƟvo', 'Ɵpo'])
    engine = Mock(side_effect=RuntimeError('OCR no disponible'))
    for config in [settings(ocr_enabled=False), settings()]:
        assert repair_digital_text(page, 'ﬁ acƟvo moƟvo Ɵpo', config, engine, tmp_path)[0] == 'fi acƟvo moƟvo Ɵpo'
