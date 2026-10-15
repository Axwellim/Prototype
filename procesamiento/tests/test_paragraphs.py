from app.paragraphs import reflow_paragraphs, format_ocr_letter
from app.layout import render_lines


def test_short_final_line_separates_paragraphs_even_in_same_ocr_group():
    lines=[{'text':'Un parrafo ocupa una linea larga y se extiende','x':10,'y':10,'w':450,'h':20,'group':(1,1)},
           {'text':'hasta una linea corta.','x':10,'y':40,'w':200,'h':20,'group':(1,1)},
           {'text':'Otro parrafo empieza aqui y continua','x':10,'y':70,'w':450,'h':20,'group':(1,1)},
           {'text':'en la siguiente linea.','x':10,'y':100,'w':200,'h':20,'group':(1,1)}]
    assert render_lines(lines)=='Un parrafo ocupa una linea larga y se extiende\nhasta una linea corta.\n\nOtro parrafo empieza aqui y continua\nen la siguiente linea.\n'


def test_wrapped_long_sentence_before_list_and_plus_bullets():
    source='De nuestra consideración:\n\nSe solicita apoyo con la disponibilidad del gobierno\nlocal para facilitar el siguiente equipo y mobiliario:\n+. Recurso primero.\n+ Recurso segundo.\n'
    result=format_ocr_letter(reflow_paragraphs(source))
    assert 'gobierno local para facilitar el siguiente equipo y mobiliario:' in result
    assert '- Recurso primero.\n- Recurso segundo.' in result


def test_issuer_titles_are_spaced_but_recipient_keeps_lines_and_subject_reflows():
    source='ENTIDAD EMISORA\nUNIDAD LOCAL\nPERIODO 2025-2026\n\nCiudad, fecha\n\nIngeniera\nNombre Apellido\nPRESIDENTA\n\nASUNTO: SOLICITUD DE APOYO\nPARA REUNION\n\nDe nuestra consideración:\n\nTexto.'
    result=format_ocr_letter(source)
    assert result.startswith('ENTIDAD EMISORA\n\nUNIDAD LOCAL\n\nPERIODO 2025-2026')
    assert 'Ingeniera\nNombre Apellido\nPRESIDENTA' in result
    assert 'ASUNTO: SOLICITUD DE APOYO PARA REUNION\n\nDe nuestra consideración:' in result


def test_false_blank_and_physical_wraps_join_without_changing_words():
    source='Encabezado\nDestinataria\nDe mi consideración. -\n\nReciba un saludo en sus\n\nfunciones diarias.\n\nSolicitamos el apoyo con\nla maquinaria para instalar tuberías de\n\nagua potable.\n\nAtentamente,\n\nSr. Juan Pérez\nPresidente\n'
    result=reflow_paragraphs(source)
    assert 'Reciba un saludo en sus funciones diarias.\n\nSolicitamos' in result
    assert 'con la maquinaria para instalar tuberías de agua potable.' in result
    assert source.split()==result.split()
    assert result.split('De mi consideración. -')[0]==source.split('De mi consideración. -')[0]
    assert result.split('Atentamente,')[1]==source.split('Atentamente,')[1]
    assert reflow_paragraphs(result)==result


def test_real_paragraphs_and_new_sentences_inside_a_paragraph():
    source='De nuestra consideración:\n\nPrimera oración.\nSegunda oración del mismo párrafo.\n\nOtro párrafo.\n'
    assert reflow_paragraphs(source)=='De nuestra consideración:\n\nPrimera oración. Segunda oración del mismo párrafo.\n\nOtro párrafo.\n'


def test_lists_labels_tables_and_uppercase_headings_stay_separate():
    source='De nuestra consideración:\n\nANTECEDENTES\nTexto descriptivo\ncon continuación.\n\nFecha: mañana\nHora: 09h00\n\n• Recurso uno\n• Recurso dos\n\n1. Primer requisito\n2. Segundo requisito\n\nCampo | Valor\nDato | Información\nAtentamente,\nFirma\n'
    result=reflow_paragraphs(source)
    assert 'ANTECEDENTES\nTexto descriptivo con continuación.' in result
    assert 'Fecha: mañana\nHora: 09h00' in result
    assert '• Recurso uno\n• Recurso dos' in result
    assert '1. Primer requisito\n2. Segundo requisito' in result
    assert 'Campo | Valor\nDato | Información' in result
    assert source.split()==result.split()


def test_no_letter_body_means_no_reflow():
    source='ASOCIACIÓN LOCAL\nCalle Nueva\nJuan Pérez\nPresidente\n'
    assert reflow_paragraphs(source)==source


def test_continuation_page_body_reflows_but_signers_stay_intact():
    source='La solicitud responde a la necesidad de contar con\nun espacio adecuado.\n\nOtro párrafo completo.\n\nAtentamente,\nNombre\nCargo\n'
    result=reflow_paragraphs(source)
    assert result.startswith('La solicitud responde a la necesidad de contar con un espacio adecuado.\n\n')
    assert result.endswith('Atentamente,\nNombre\nCargo\n')


def test_unknown_paragraph_boundary_is_preserved_conservatively():
    source='De mi consideración:\n\nTexto que parece incompleto\n\nOtro párrafo con inicial mayúscula.\n'
    assert reflow_paragraphs(source)==source
