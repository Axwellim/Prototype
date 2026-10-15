"""Reflujo conservador del cuerpo de oficios; conserva encabezado y firmantes."""
import re

GREETING = re.compile(r'^De\s+(?:mi|nuestra)\s+consideraci[oó]n[\s.,:;—–-]*$', re.I)
CLOSING = re.compile(r'^A[tf]entamente[\s.,:;—–-]*$', re.I)
LABEL = re.compile(r'^(?:Antecedentes?|Asunto|Fecha|Lugar|Direcci[oó]n|Hora|Anexos?|Observaciones|Nota)\s*:', re.I)


def structural(line):
    return (line.isupper() or bool(LABEL.match(line)) or (line.endswith(':') and len(line.split()) <= 4) or
            bool(re.match(r'^(?:[•*▪+-][.]?\s|\d+[.)]\s)', line)) or '\t' in line or '|' in line)


def reflow_paragraphs(text):
    lines = text.splitlines()
    greeting = next((index for index, line in enumerate(lines) if GREETING.fullmatch(line.strip())), None)
    closing = next((index for index, line in enumerate(lines) if CLOSING.fullmatch(line.strip())), len(lines))
    if greeting is not None:
        start = greeting + 1
    elif closing < len(lines) and lines and len(lines[0].split()) >= 6 and not structural(lines[0]):
        # Continuación de un oficio en una página que empieza directamente con prosa.
        start = 0
    else:
        return text
    if closing <= start:
        return text
    output = ''
    previous = None
    blank = False
    for raw in lines[start:closing]:
        line = raw.strip()
        if not line:
            blank = True
            continue
        if previous is not None:
            if structural(previous) or structural(line):
                separator = '\n\n' if blank else '\n'
            else:
                terminal = bool(re.search(r'[.!?:;][”"\')]*$', previous))
                connector = bool(re.search(r'\b(?:de|del|la|el|y|a|con|sus|un|una|para|los|las|por|en|al)$', previous, re.I))
                continuation = not terminal and (line[:1].islower() or connector)
                separator = '\n\n' if blank and not continuation else ' '
            output += separator
        output += line
        previous, blank = line, False
    if not output:
        return text
    prefix = '\n'.join(lines[:start]).rstrip()
    suffix = '\n'.join(lines[closing:]).strip('\n')
    result = (prefix + '\n\n' if prefix else '') + output
    if suffix:
        result += '\n\n' + suffix
    return result + ('\n' if text.endswith('\n') else '')


def format_ocr_letter(text):
    """Separa títulos del emisor y viñetas; reúne únicamente el asunto."""
    lines=text.splitlines()
    greeting=next((i for i,line in enumerate(lines) if GREETING.fullmatch(line.strip())),None)
    if greeting is None:
        return text
    subject=next((i for i,line in enumerate(lines[:greeting]) if re.match(r'^ASUNTO\s*:',line,re.I)),None)
    if subject is not None:
        lines[subject:greeting]=[' '.join(line.strip() for line in lines[subject:greeting] if line.strip()),'']
    # Solo los títulos consecutivos al comienzo: no modifica los datos del destinatario.
    title_end=0
    while title_end<len(lines) and lines[title_end].strip() and lines[title_end].isupper():
        title_end+=1
    if title_end>=2 and not re.search(r'OFICIO|ASUNTO', ' '.join(lines[:title_end]),re.I):
        lines[:title_end]='\n\n'.join(lines[:title_end]).splitlines()
    output=[]
    for line in lines:
        if re.match(r'^\s*\+[.]?\s+',line):
            line=re.sub(r'^\s*\+[.]?\s+','- ',line)
        if line.startswith('- ') and output and not output[-1] and len(output)>=2 and output[-2].startswith('- '):
            output.pop()
        elif line.startswith('- ') and output and output[-1] and not output[-1].startswith('- '):
            output.append('')
        output.append(line)
    return '\n'.join(output)+ ('\n' if text.endswith('\n') else '')
