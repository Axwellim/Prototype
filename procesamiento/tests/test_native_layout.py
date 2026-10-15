import pymupdf

from app.native_layout import render_structured_native, render_native_letter


def test_numbered_document_reflows_paragraphs_lists_and_signer_columns():
    with pymupdf.open() as doc:
        page = doc.new_page(width=600, height=800)
        def line(x, y, text, bold=False):
            page.insert_text((x, y), text, fontsize=10, fontname='hebo' if bold else 'helv')
        line(50, 100, '1. OBJETO', True)
        line(50, 130, 'Este convenio conserva las palabras del texto original y permite')
        line(50, 144, 'continuar el mismo parrafo.')
        line(50, 180, '- Primera responsabilidad que se desarrolla')
        line(65, 194, 'en una segunda linea.')
        line(50, 210, '- Segunda responsabilidad.')
        line(50, 260, '2. ACEPTACION', True)
        line(50, 290, 'Para constancia las partes suscriben el presente convenio en')
        line(50, 304, 'dos ejemplares.')
        for y, left, right in [(370, 'Por Entidad Uno', 'Por Entidad Dos'),
                               (390, 'Persona Alfa', 'Persona Beta'),
                               (410, 'Presidenta', 'Directora')]:
            line(50, y, left)
            line(330, y, right)
        result = render_structured_native(page)
    assert 'permite continuar el mismo parrafo.' in result
    assert '- Primera responsabilidad que se desarrolla en una segunda linea.\n- Segunda' in result
    assert 'convenio en dos ejemplares.' in result
    assert 'Por Entidad Uno\nPersona Alfa\nPresidenta\n\nPor Entidad Dos\nPersona Beta\nDirectora' in result


def test_ordinary_letter_keeps_existing_layout_path():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 100), 'De nuestra consideracion:')
        assert render_structured_native(page) is None


def test_continuation_letter_joins_list_items_but_keeps_signer_lines():
    with pymupdf.open() as doc:
        page=doc.new_page()
        for y,text in [(100,'Solicitud:'),(130,'1. Presentar el proyecto para su'),
                       (144,'revision y aprobacion.'),(180,'2. Entregar los documentos'),
                       (194,'en formato digital.'),(240,'Atentamente;'),
                       (300,'Persona Ejemplo'),(314,'PRESIDENTA')]:
            page.insert_text((50,y),text,fontsize=10)
        result=render_native_letter(page)
    assert '1. Presentar el proyecto para su revision y aprobacion.' in result
    assert '\n\n2. Entregar los documentos en formato digital.' in result
    assert 'Atentamente;\n\nPersona Ejemplo\nPRESIDENTA' in result


def test_letter_header_groups_identification_and_recipient_without_joining_sections():
    with pymupdf.open() as doc:
        page=doc.new_page()
        for y,text in [(80,'OFICIO No. ABC-42'),(94,'Ciudad, 03 de abril de 2026'),
                       (150,'Estimado'),(164,'Ing. Persona Ejemplo'),(178,'VOCAL DE LA COMISION'),
                       (220,'Presente. -'),(260,'De mi consideración:'),
                       (300,'El contenido debe mantenerse.'),(350,'Atentamente;')]:
            page.insert_text((50,y),text,fontsize=10)
        result=render_native_letter(page)
    assert result.startswith('OFICIO No. ABC-42\nCiudad, 03 de abril de 2026\n\nEstimado\nIng. Persona Ejemplo\nVOCAL DE LA COMISION\n\nPresente. -\n\nDe mi consideración:')


def test_wrapped_subject_and_comma_closing_preserve_single_line_breaks():
    with pymupdf.open() as doc:
        page=doc.new_page()
        for y,text in [(100,'ASUNTO: Invitacion a una reunion para revisar'),
                       (114,'las actividades del proyecto.'),(160,'De nuestra consideración:'),
                       (200,'El cuerpo permanece como un parrafo completo.'),
                       (250,'Atentamente,'),(300,'Ing. Persona Ejemplo'),
                       (314,'PRESIDENTA DEL GAD'),(328,'PARROQUIAL LOCAL'),
                       (342,'Cel: 0900000000'),(356,'contacto@example.org')]:
            page.insert_text((50,y),text,fontsize=10)
        result=render_native_letter(page)
    assert 'revisar\nlas actividades' in result
    assert result.endswith('Atentamente,\n\nIng. Persona Ejemplo\nPRESIDENTA DEL GAD\nPARROQUIAL LOCAL\nCel: 0900000000\ncontacto@example.org\n')
