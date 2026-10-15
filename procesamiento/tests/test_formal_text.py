from app.formal_text import consistent_role, formal_label, email_from_ocr


def test_repeated_document_words_fix_unique_acronym_and_place_without_names():
    context = 'GAD GAD Pucará Pucará Pucará'
    assert consistent_role('PRESIDENTA DEL GAL DE PUCARANS', context) == 'PRESIDENTA DEL GAD DE PUCARÁ'


def test_ambiguous_correction_and_absent_evidence_keep_literal_reading():
    assert consistent_role('GAL', 'GAD GAD GAS GAS') == 'GAL'
    assert consistent_role('GAL', 'Otro documento sin acrónimo') == 'GAL'


def test_correct_job_title_is_not_replaced_by_similar_body_word():
    assert consistent_role('PRESIDENTE PARROQUIAL', 'Presente presente parroquia parroquia') == 'PRESIDENTE PARROQUIAL'


def test_canonical_variant_uses_frequency_not_last_ocr_occurrence():
    assert consistent_role('PUCARA', 'Pucará Pucará PUCARA') == 'PUCARÁ'


def test_format_rules_preserve_identity_digits_and_literal_name():
    assert formal_label('Íng. Ana Pérex') == 'Ing. Ana Pérex'
    assert formal_label('Cl. 123456789-0 —-') == 'CI. 123456789-0'
    assert formal_label('Cel: 0123456789...') == 'Cel: 0123456789'


def test_email_delimiter_repair_does_not_invent_user_or_domain():
    assert email_from_ocr('oficinaM) ejemplo.org y') == 'oficina@ejemplo.org'
    assert email_from_ocr('oficina(Q ejemplo.org') == 'oficina@ejemplo.org'
    assert email_from_ocr('oficina sin dominio') is None
    assert email_from_ocr('a@uno.org b@dos.org') is None
    assert email_from_ocr('Contactos: 0123456789 / oficina ejemplo.org') == 'oficina@ejemplo.org'
    assert email_from_ocr('oficina ejemplo.org') is None
