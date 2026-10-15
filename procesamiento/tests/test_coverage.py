import numpy as np
from PIL import Image, ImageDraw
from app.coverage import text_components,coverage,illumination_copy


def test_missing_lower_text_is_detected_without_a_reference():
    image=Image.new('L',(600,800),230)
    draw=ImageDraw.Draw(image)
    words=[]
    for y in [100,350,650]:
        for x in range(40,550,20):
            draw.rectangle((x,y,x+4,y+12),fill=30)
            words.append({'x':x,'y':y,'w':5,'h':13})
    components=text_components(image)
    partial=coverage([{'words':words[:26]}],image.size,components)
    complete=coverage([{'words':words}],image.size,components)
    assert partial < .75
    assert complete > .95
    assert complete > partial+.08


def test_illumination_correction_preserves_source_and_reduces_background_variation():
    gradient=np.tile(np.linspace(80,200,600,dtype=np.uint8),(800,1))
    image=Image.fromarray(gradient)
    before=image.tobytes()
    result=illumination_copy(image)
    assert result.size==image.size
    assert image.tobytes()==before
    assert np.array(result)[400,50:-50].std() < gradient[400,50:-50].std()


def test_blank_page_does_not_trigger_recovery():
    image=Image.new('L',(600,800),255)
    assert coverage([],image.size,text_components(image))==1
