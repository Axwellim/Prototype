"""Composición secuencial de originales privados e invitación sin OCR."""
import json
import re
import zipfile
from pathlib import Path
from time import perf_counter

import pymupdf

from .extraction import DocumentError, extract_document
from .normalization import normalize_pdf
from .ocr import load_image
from .schemas import PageResult, ProcessingResult


def archive_invitation(source, target, settings):
    if source.stat().st_size > settings.max_bytes:
        raise DocumentError('tamano_excedido', 'La invitación supera el tamaño permitido.', 413)
    if settings.input_mime == 'application/pdf':
        try:
            with pymupdf.open(source) as doc:
                if not doc.is_pdf or doc.needs_pass or doc.is_repaired or not doc.page_count:
                    raise ValueError('PDF no utilizable')
                count=doc.page_count
                if count > settings.max_pages:
                    raise DocumentError('paginas_excedidas', 'La invitación supera el máximo de páginas.')
                for page in doc:
                    if page.rect.is_empty or page.rect.is_infinite:
                        raise ValueError('Página inválida')
        except DocumentError:
            raise
        except Exception:
            raise DocumentError('pdf_invalido', 'No se pudo leer el PDF de la invitación.')
    else:
        load_image(source,settings)
        count=1
    normalize_pdf(source,target,settings,count)
    pages=[PageResult(numero=i,metodo='sin_transcripcion',texto='',duracion_ms=0,
                      observaciones=['Invitación archivada sin transcripción por elección del usuario.'])
           for i in range(1,count+1)]
    return ProcessingResult(estado='completado',numero_paginas=count,duracion_total_ms=0,
                            paginas=pages,texto_completo='\f'.join(p.texto for p in pages))


def process_composition(source, directory, settings):
    started=perf_counter()
    if source.stat().st_size > settings.max_bytes:
        raise DocumentError('tamano_excedido','La carga supera el tamaño permitido.',413)
    try:
        archive=zipfile.ZipFile(source)
        with archive:
            entries=archive.infolist()
            names=[entry.filename for entry in entries]
            if len(entries)>21 or len(names)!=len(set(names)) or 'manifest.json' not in names:
                raise ValueError('Contenedor inválido')
            if any(entry.compress_type!=zipfile.ZIP_STORED or entry.flag_bits & 1 for entry in entries):
                raise ValueError('Solo entradas sin compresión ni cifrado')
            if sum(entry.file_size for entry in entries)>settings.max_bytes or archive.getinfo('manifest.json').file_size>20000:
                raise ValueError('Tamaño inválido')
            manifest=json.loads(archive.read('manifest.json'))
            parts=manifest['documentos']
            invitation=manifest.get('invitacion')
            if not isinstance(parts,list) or not 1<=len(parts)<=19 or not all(isinstance(p,dict) for p in parts):
                raise ValueError('Componentes inválidos')
            all_parts=parts+([invitation] if invitation is not None else [])
            if invitation is not None and not isinstance(invitation,dict):
                raise ValueError('Invitación inválida')
            expected=['manifest.json']
            pdfs=0
            for index,part in enumerate(all_parts):
                name=part['archivo']
                if not isinstance(name,str) or not re.fullmatch(r'p\d{3}\.(pdf|jpg|png)',name):
                    raise ValueError('Nombre interno inválido')
                mime={'pdf':'application/pdf','jpg':'image/jpeg','png':'image/png'}[name.rsplit('.',1)[1]]
                part['mime']=mime
                expected.append(name)
                if index<len(parts) and mime=='application/pdf':
                    pdfs+=1
            if pdfs>1 or len(expected)!=len(set(expected)) or set(expected)!=set(names):
                raise ValueError('Solo se admite un PDF en el documento')
            # Los nombres se validan; nunca se usa extractall ni rutas externas.
            for part in all_parts:
                (directory/part['archivo']).write_bytes(archive.read(part['archivo']))
    except (ValueError,KeyError,TypeError,zipfile.BadZipFile,UnicodeError,RuntimeError):
        raise DocumentError('composicion_invalida','La composición de archivos no es válida.')
    pages=[]
    component_pages=[]
    cumulative_chars=0
    with pymupdf.open() as merged:
        for index,part in enumerate(parts):
            local=settings.model_copy(update={'input_mime':part['mime']})
            path=directory/part['archivo']
            result=extract_document(path,local)
            component_pages.append(result.numero_paginas)
            if len(pages)+result.numero_paginas>settings.max_pages:
                raise DocumentError('paginas_excedidas','El documento compuesto supera el máximo de páginas.')
            cumulative_chars+=sum(len(p.texto)+len(p.texto_digital or '')+
                sum(len(v.texto)+len(v.texto_pagina_completa or '')+len(v.texto_lectura_inicial or '') for v in p.variantes_ocr)
                for p in result.paginas)
            if cumulative_chars>settings.max_text_chars:
                raise DocumentError('texto_excedido','La composición supera el límite de texto.')
            normalized=directory/f'parte-{index}.pdf'
            normalize_pdf(path,normalized,local,result.numero_paginas)
            with pymupdf.open(normalized) as doc:
                merged.insert_pdf(doc)
            for page in result.paginas:
                pages.append(page.model_copy(update={'numero':len(pages)+1}))
        merged.save(directory/'normalizado.pdf',deflate=True)
    if (directory/'normalizado.pdf').stat().st_size>settings.max_pdf_bytes:
        raise DocumentError('pdf_resultado_excedido','El PDF compuesto supera el límite.',413)
    invitation_pages=None
    if invitation is not None:
        local=settings.model_copy(update={'input_mime':invitation['mime']})
        result=archive_invitation(directory/invitation['archivo'],directory/'invitacion.pdf',local)
        invitation_pages=result.numero_paginas
        if (directory/'normalizado.pdf').stat().st_size+(directory/'invitacion.pdf').stat().st_size>settings.max_pdf_bytes:
            raise DocumentError('pdf_resultado_excedido','Los PDF resultantes superan el límite.',413)
    return ProcessingResult(estado='requiere_ocr' if any(p.metodo=='requiere_ocr' for p in pages) else 'completado',
                            numero_paginas=len(pages),duracion_total_ms=round((perf_counter()-started)*1000),
                            paginas=pages,texto_completo='\f'.join(p.texto for p in pages),invitacion_paginas=invitation_pages,
                            componentes_paginas=component_pages)
