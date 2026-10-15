"""Distingue un fondo decorativo claro de una página escaneada con texto en píxeles."""
import io
import re

import numpy as np
import pymupdf
from PIL import Image


def has_clear_background_with_visible_text(page, settings, verified_backgrounds=None, repeated_headers=None):
    rect = page.rect
    visible = 0
    bands = set()
    for span in page.get_texttrace():
        if span['type'] not in (0, 1) or span.get('opacity', 1) < .5:
            continue
        color = span.get('color', ())
        if color and all(channel > .9 for channel in color):
            continue
        for char in span['chars']:
            if not chr(char[0]).isalnum():
                continue
            box = pymupdf.Rect(char[3])
            if box.is_empty or (box & rect).get_area() < box.get_area()*.9:
                continue
            middle = (box.y0+box.y1)/2
            if rect.y0 + rect.height*.1 < middle < rect.y0 + rect.height*.9:
                visible += 1
                bands.add(int((middle-rect.y0)/rect.height*6))
    images = page.get_image_info(xrefs=True)
    if not images:
        return False
    dominant = max(images, key=lambda image: pymupdf.Rect(image['bbox']).get_area())
    dense = visible >= max(300, settings.min_chars) and len(bands) >= 4
    shared = (verified_backgrounds is not None and dominant['xref'] in verified_backgrounds and
              visible >= max(120, settings.min_chars) and len(bands) >= 2)
    if not dense and not shared:
        return False
    box = pymupdf.Rect(dominant['bbox'])
    if (box & rect).get_area() < rect.get_area()*.8 or not dominant['xref']:
        return False
    transform = dominant['transform']
    if abs(transform[1]) > .001 or abs(transform[2]) > .001 or transform[0] <= 0 or transform[3] <= 0:
        return False
    closings = [line['bbox'][3] for block in page.get_text('dict')['blocks'] for line in block.get('lines', [])
                if re.fullmatch(r'Atentamente[\s;:,.\-]*', ''.join(span['text'] for span in line['spans']).strip(), re.I)]
    closing = min(closings) if closings else None
    for image in images:
        if image is dominant:
            continue
        other = pymupdf.Rect(image['bbox']) & rect
        repeated_logo = (repeated_headers is not None and image['xref'] in repeated_headers and
                         other.y1 <= rect.y0+rect.height*.15 and other.get_area() <= rect.get_area()*.03)
        if repeated_logo:
            continue
        verified_closing = (verified_backgrounds is not None and dominant['xref'] in verified_backgrounds
                            and closing is not None and closing > rect.y0+rect.height*.35
                            and other.y0 >= closing and other.get_area() <= rect.get_area()*.04)
        if not verified_closing and (other.y0 < rect.y0+rect.height*.6 or other.get_area() > rect.get_area()*.08):
            return False
    if dominant['width']*dominant['height'] > settings.max_image_pixels:
        return False
    region = pymupdf.Rect(rect.x0+rect.width*.1, rect.y0+rect.height*.2,
                          rect.x0+rect.width*.9, rect.y0+rect.height*.8)
    if not box.contains(region):
        return False
    source = page.parent.extract_image(dominant['xref'])
    with Image.open(io.BytesIO(source['image'])) as image:
        if image.width*image.height > settings.max_image_pixels:
            return False
        crop = ((region.x0-box.x0)/box.width*image.width, (region.y0-box.y0)/box.height*image.height,
                (region.x1-box.x0)/box.width*image.width, (region.y1-box.y0)/box.height*image.height)
        sample = image.crop(tuple(round(value) for value in crop)).convert('L')
        dark_fraction = float(np.mean(np.asarray(sample) < 180))
    clear = dark_fraction < .0001
    if clear and dense and verified_backgrounds is not None:
        verified_backgrounds.add(dominant['xref'])
    return clear
