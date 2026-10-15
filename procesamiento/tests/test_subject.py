from PIL import Image

from app.config import Settings
from app.subject import normalize_office_number, refine_subject


def test_office_number_only_changes_symbol_before_document_identifier():
    assert normalize_office_number('OFICIO CIRCULAR N” XYZ-20-2026') == 'OFICIO CIRCULAR N° XYZ-20-2026'
    assert normalize_office_number('La letra N” se conserva') == 'La letra N” se conserva'


def test_subject_joins_lines_and_uses_similar_optical_reading(tmp_path):
    lines=[{'text':'ASUNTO: PARTICIPACION EN LA FER lA DE','x':10,'y':20,'w':350,'h':15,'group':1},
           {'text':'SALUD COMUNITARIA.','x':10,'y':40,'w':220,'h':15,'group':1},
           {'text':'De nuestra consideración:','x':10,'y':100,'w':250,'h':15,'group':2}]
    result=refine_subject(Image.new('RGB',(500,200),'white'),lines,tmp_path,Settings(api_token='x'*40),
                          lambda *args,**kwargs:'ASUNTO: PARTICIPACION EN LA FERIA DE SALUD COMUNITARIA.')
    assert result[0]['text']=='ASUNTO: PARTICIPACION EN LA FERIA DE SALUD COMUNITARIA.'
    assert result[1]==lines[2]


def test_subject_rejects_different_optical_content(tmp_path):
    lines=[{'text':'ASUNTO: ASISTENCIA A LA FER lA LOCAL','x':10,'y':20,'w':350,'h':15,'group':1}]
    result=refine_subject(Image.new('RGB',(500,200),'white'),lines,tmp_path,Settings(api_token='x'*40),
                          lambda *args,**kwargs:'ASUNTO: TEXTO COMPLETAMENTE DISTINTO')
    assert result[0]['text']==lines[0]['text']
