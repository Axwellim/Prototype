from unittest.mock import Mock
from PIL import Image, ImageDraw
from app.colored_heading import heading_region, refine_heading, normalize_optical_date, omit_single_signature, refine_address_words
from app.config import Settings
from test_signatures import line
from test_layout import HEADER


def colored_letterhead():
    image = Image.new('RGB',(1000,1600),'white')
    draw = ImageDraw.Draw(image)
    for y in (60,120,180):
        for x in range(300,860,20):
            draw.rectangle((x,y,x+12,y+18),fill=(30,90,140))
    return image


def test_blue_text_is_located_but_black_headers_and_one_logo_are_not():
    image = colored_letterhead()
    assert heading_region(image) is not None
    assert heading_region(image.convert('L').convert('RGB')) is None
    logo = Image.new('RGB',image.size,'white')
    ImageDraw.Draw(logo).rectangle((300,60,850,80),fill=(30,90,140))
    assert heading_region(logo) is None


def test_refinement_keeps_body_and_contact_header_and_reads_date(tmp_path):
    image = colored_letterhead()
    rows = [line('Emisor impreso en negro',250,10),line('Encabezado anterior',300,60),line('Ciudad, 0i de junio de 2026',600,400),
            line('Texto del cuerpo conservado',100,650)]
    def optical(path, config, **kwargs):
        return {'encabezado-color-0.png':'ASOCIACIÓN LOCAL','encabezado-color-1.png':'SEDE CENTRAL',
                'encabezado-color-2.png':'Contactos: 0123456789 / oficina ejemplo.org',
                'fecha-encabezado-color.png':'ciudad, Ul de junio de 2026'}[path.name]
    revised, changed = refine_heading(image,image,rows,[],tmp_path,Settings(api_token='x'*40),optical)
    assert changed
    assert revised[0] is rows[0]
    assert 'oficina@ejemplo.org' in revised[1]['text']
    assert revised[-1] is rows[-1]
    assert revised[2]['text']=='Ciudad, 01 de junio de 2026'
    assert rows[2]['text']=='Ciudad, 0i de junio de 2026'


def test_date_normalization_rejects_invalid_or_missing_data():
    assert normalize_optical_date('Ciudad, 0i de junio de 2026')=='Ciudad, 01 de junio de 2026'
    assert normalize_optical_date('Ciudad, 31 de febrero de 2026') is None
    assert normalize_optical_date('Ciudad, de junio de 2026') is None
    assert normalize_optical_date('Ciudad, xx de junio de 2026') is None


def test_only_blue_rubric_between_closing_and_one_printed_signer_is_omitted():
    image=Image.new('RGB',(1000,1600),'white')
    ImageDraw.Draw(image).rectangle((100,1150,180,1170),fill=(30,50,140))
    rows=[line('Atentamente,',100,1050),line('VIA',100,1150),
          line('Sr. Juan Pérez',100,1250),line('Presidente',100,1300),line('Organización local',100,1350)]
    revised, removed=omit_single_signature(image,image.size,rows,[])
    assert removed and 'VIA' not in [item['text'] for item in revised]
    assert revised[-3:]==rows[-3:]
    assert omit_single_signature(Image.new('RGB',image.size,'white'),image.size,rows,[])==(rows,False)


def test_address_word_changes_only_when_two_optical_modes_agree(tmp_path):
    path=tmp_path/'fila.png';Image.new('L',(150,60),255).save(path)
    raw=HEADER+'5\t1\t1\t1\t1\t1\t20\t15\t80\t20\t70\tRoca\n'
    engine=Mock(side_effect=[raw,'Boca','Boca'])
    assert refine_address_words(path,tmp_path,None,engine)=='Boca'
    engine=Mock(side_effect=[raw,'Boca','Roca'])
    assert refine_address_words(path,tmp_path,None,engine)=='Roca'
