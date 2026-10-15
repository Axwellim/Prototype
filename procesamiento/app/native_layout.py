"""Estructura de documentos digitales numerados mediante líneas y distancias del PDF."""
import re
import statistics

NUMBERED = re.compile(r'^\d+(?:\.\d+)*\.?\s+')
BULLET = re.compile(r'^[•▪●-]\s+')
CONTACT = re.compile(r'^(?:Para\s+(?:(?:el|la)\s+)?[A-ZÁÉÍÓÚÜÑ]{3,}|(?i:A la atenci[oó]n\b|Tel[eé]fono\b|Email\b))')


def native_rows(page):
    fragments = []
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            spans = [span for span in line['spans'] if span['text'].strip()]
            if not spans:
                continue
            text = ''.join(span['text'] for span in line['spans']).strip()
            x0,y0,x1,y1 = line['bbox']
            fragments.append({'text':re.sub(r'\s+', ' ',text), 'x':x0, 'right':x1,
                              'y':y0, 'h':y1-y0, 'base':spans[0]['origin'][1],
                              'bold':any(span['flags'] & 16 for span in spans)})
    rows = []
    for fragment in sorted(fragments,key=lambda item:(item['base'],item['x'])):
        if rows and abs(fragment['base']-rows[-1]['base']) <= 2:
            rows[-1]['parts'].append(fragment)
        else:
            rows.append({'base':fragment['base'],'parts':[fragment]})
    for row in rows:
        row['parts'].sort(key=lambda item:item['x'])
        row.update(text=' '.join(part['text'] for part in row['parts']),
                   x=min(part['x'] for part in row['parts']), right=max(part['right'] for part in row['parts']),
                   h=max(part['h'] for part in row['parts']), bold=any(part['bold'] for part in row['parts']))
    return rows


def signature_columns(rows, width):
    for index,row in enumerate(rows):
        parts=row['parts']
        if len(parts)!=2 or not all(re.match(r'^Por\s',part['text'],re.I) for part in parts):
            continue
        if not parts[0]['right'] < parts[1]['x'] or parts[1]['x'] < width*.45:
            continue
        tail=rows[index:]
        if len(tail)<3 or any(len(item['parts'])!=2 for item in tail):
            continue
        split=(parts[0]['right']+parts[1]['x'])/2
        if any(item['parts'][0]['right'] >= split or item['parts'][1]['x'] <= split for item in tail):
            continue
        blocks=['\n'.join(item['parts'][column]['text'] for item in tail) for column in (0,1)]
        return rows[:index], '\n\n'.join(blocks)
    return rows, None


def render_structured_native(page):
    rows=native_rows(page)
    if not any(NUMBERED.match(row['text']) and row['text'].isupper() for row in rows):
        return None
    rows, signers=signature_columns(rows,page.rect.width)
    if not rows:
        return None
    typical=statistics.median(row['h'] for row in rows)
    flow_right=max(row['right'] for row in rows)
    output=''
    previous=None
    in_bullet=False
    for row in rows:
        text=BULLET.sub('- ',row['text'])
        if previous is not None:
            gap=row['base']-previous['base']
            heading=bool(NUMBERED.match(text)) or row['bold'] or text.isupper()
            prev_heading=bool(NUMBERED.match(previous['text'])) or previous['bold'] or previous['text'].isupper()
            new_bullet=bool(BULLET.match(row['text']))
            previous_bullet=bool(BULLET.match(previous['text']))
            wrapped_bullet=previous_bullet and not new_bullet and row['x'] > previous['x']+typical*.5
            short_end=previous['right'] < flow_right-typical*2 and bool(re.search(r'[.!?]["”]?$',previous['text']))
            title_wrap=(heading and prev_heading and not NUMBERED.match(text) and not NUMBERED.match(previous['text'])
                        and gap <= typical*2.5)
            if new_bullet:
                separator='\n' if in_bullet and gap<=typical*2.5 else '\n\n'
            elif title_wrap or (wrapped_bullet and gap<=typical*2.5):
                separator=' '
            elif gap>typical*2.5 or heading or prev_heading or CONTACT.match(text) or CONTACT.match(previous['text']) or short_end:
                separator='\n\n'
            else:
                separator=' '
            output+=separator
            if new_bullet:
                in_bullet=True
            elif heading or gap>typical*2.5 or CONTACT.match(text):
                in_bullet=False
        output+=text
        if previous is None:
            in_bullet=bool(BULLET.match(row['text']))
        previous=row
    if signers:
        output+='\n\n'+signers
    return output+'\n'


def render_native_letter(page):
    """Une líneas físicas de oficios digitales sin mezclar listas ni firmantes."""
    rows = native_rows(page)
    greeting = next((i for i, row in enumerate(rows) if re.fullmatch(r'De (?:mi|nuestra) consideraci[oó]n[\s:;.\-]*', row['text'], re.I)), None)
    closing = next((i for i, row in enumerate(rows) if re.fullmatch(r'Atentamente[\s:;,.\-]*', row['text'], re.I)), None)
    if greeting is None and closing is None:
        return None
    start = greeting + 1 if greeting is not None else 0
    end = closing if closing is not None else len(rows)
    typical = statistics.median(row['h'] for row in rows)
    flow_right = max(row['right'] for row in rows)
    output = ''
    previous_header = None
    header_boundary = re.compile(r'^(?:Presente\b|De (?:mi|nuestra) consideraci[oó]n\b|Asunto\s*:)', re.I)
    for row in rows[:start]:
        if previous_header is not None:
            separate = (row['base']-previous_header['base'] > typical*2.5
                        or header_boundary.match(row['text'])
                        or re.match(r'^(?:Presente\b|De (?:mi|nuestra) consideraci[oó]n\b)', previous_header['text'], re.I))
            output += '\n\n' if separate else '\n'
        output += row['text']
        previous_header = row
    previous = None
    for row in rows[start:end]:
        label = row['text'].endswith(':') and len(row['text'].split()) <= 4
        item = bool(re.match(r'^(?:\d+[.)]|[a-z][)])\s+', row['text']))
        if previous is None:
            separator = '\n\n' if output else ''
        elif (item or label or (previous['text'].endswith(':') and len(previous['text'].split()) <= 4)
              or row['base']-previous['base'] > typical*2.5
              or (previous['right'] < flow_right-typical*2 and re.search(r'[.;!?]$', previous['text']))):
            separator = '\n\n'
        else:
            separator = ' '
        output += separator + row['text']
        previous = row
    if closing is not None:
        output += '\n\n' + rows[closing]['text']
        if rows[closing+1:]:
            output += '\n\n' + '\n'.join(row['text'] for row in rows[closing+1:])
    return output + '\n'
