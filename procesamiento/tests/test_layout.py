import pytest
from PIL import Image, ImageDraw
from app.layout import tsv_lines, render_lines, letter_bounds, body_copy, merge_fragments

HEADER = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'


def line(text,x,y,w=150,h=20,group=('1','1')):
    return {'text':text,'x':x,'y':y,'w':w,'h':h,'group':group,
            'words':[{'text':text,'x':x,'y':y,'w':w,'h':h}]}


def test_tsv_quotes_and_physical_lines_are_not_swallowed_by_csv():
    raw = HEADER + '5\t1\t1\t1\t1\t1\t20\t30\t80\t20\t90\t“Texto\n'
    raw += '5\t1\t1\t1\t1\t2\t110\t30\t80\t20\t90\t"literal\n'
    raw += '5\t1\t1\t1\t2\t1\t20\t60\t80\t20\t90\tSiguiente\n'
    raw += '5\t1\t2\t1\t1\t1\t20\t100\t80\t20\t90\tPárrafo\n'
    assert render_lines(tsv_lines(raw)) == '“Texto "literal\nSiguiente\n\nPárrafo\n'
    with pytest.raises(ValueError):
        tsv_lines('resultado no estructurado')


def sample_lines():
    return [line('GAD Parroquial Imantag',100,120),line('OFICIO',450,250),
            line('GADPRI-015-2026',650,240),line('Imantag, 12 de octubre de 2026',450,280),
            line('Destinatario',70,400),line('Texto principal',70,700),line('Último párrafo',70,1150),
            line('contacto@example.test www.example.test',80,1500,h=15)]


def test_known_letter_preserves_number_date_and_body_and_excludes_contact_footer():
    lines = sample_lines()
    bounds = letter_bounds(lines,(900,1600))
    assert bounds is not None
    assert bounds[1] < 240
    assert 1170 < bounds[3] < 1500
    assert letter_bounds([line('Contrato sin membrete',50,100),line('Cláusula',50,1500)],(900,1600)) is None


def test_colored_stamp_exclusion_uses_only_copy_and_preserves_unknown_layout():
    image = Image.new('RGB',(900,1600),'white')
    ImageDraw.Draw(image).rectangle((550,320,800,420),outline=(80,65,130),width=4)
    before = image.tobytes()
    body, exclusions = body_copy(image,image,sample_lines()+[line('ASUNTO: Prueba',70,500)],[])
    assert body is not None and len(exclusions)==3
    assert image.tobytes()==before
    assert body_copy(image,image,[line('Sin formato conocido',10,100)],[]) == (None,[])


def test_line_fragments_merge_horizontally_but_distinct_rows_stay_separate():
    lines = [line('ASUNTO: Invitación',30,100,300),line('A LA FERIA',350,98,150),
             line('SALUD Y NUTRICIÓN',30,140,300)]
    result = merge_fragments(lines,900)
    assert len(result)==2
    assert result[0]['text']=='ASUNTO: Invitación A LA FERIA'
    assert result[1]['text']=='SALUD Y NUTRICIÓN'


def test_gad_in_recipient_does_not_authorize_template_cropping():
    lines=[line('COMITÉ CENTRAL DE PADRES DE FAMILIA',200,80),line('UNIDAD EDUCATIVA IMANTAG',200,110),
           line('Imantag, 29 de septiembre de 2026',500,220),line('Oficio Nro. CCPFI-2026',600,300),
           line('PRESIDENTA DEL GAD PARROQUIAL DE IMANTAG',100,400),line('Sillas suficientes',100,1400)]
    assert letter_bounds(lines,(1200,1600)) is None
    image=Image.new('RGB',(1200,1600),'white')
    assert body_copy(image,image,lines,[]) == (None,[])


def test_word_positions_detect_letterhead_when_logo_and_office_share_a_line():
    rows = sample_lines()
    rows[0] = line('GAD Parroquial',100,120)
    shared = rows[1]
    shared['words'].append({'text':'Imantag','x':100,'y':235,'w':150,'h':30})
    shared['text'] = 'Imantag OFICIO'
    assert letter_bounds(rows,(900,1600)) is not None


def test_stamp_candidate_in_body_is_never_masked():
    from unittest.mock import patch
    image = Image.new('RGB',(900,1600),'white')
    ImageDraw.Draw(image).rectangle((550,800,800,900),fill=(80,65,130))
    rows = sample_lines()+[line('ASUNTO: Prueba',70,500)]
    with patch('app.layout.stamp_boxes',return_value=[(550,800,800,900)]):
        body, exclusions = body_copy(image,image,rows,[])
    bounds = letter_bounds(rows,image.size)
    assert body.getpixel((600,850-bounds[1])) == (80,65,130)
    assert len(exclusions) == 2
