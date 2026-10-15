"""Señal de lectura incompleta a partir de componentes y cajas, no de precisión."""
import cv2
import numpy as np
from PIL import Image


def text_components(image):
    sample = image.convert('L')
    sample.thumbnail((1200,1800))
    array = np.array(sample)
    binary = cv2.adaptiveThreshold(array,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,51,12)
    count, _, stats, centers = cv2.connectedComponentsWithStats(binary,8)
    components = []
    for index in range(1,count):
        x,y,w,h,area = stats[index]
        if (2 <= w <= sample.width*.06 and max(4,sample.height*.004) <= h <= sample.height*.04
                and area >= 5 and .06 < w/h < 6 and x > sample.width*.015 and x+w < sample.width*.985):
            components.append((centers[index][0]/sample.width,centers[index][1]/sample.height,float(area)**.5))
    return np.asarray(components[:25000],dtype=float).reshape((-1,3))


def coverage(lines, size, components):
    if len(components) < 30:
        return 1.0
    width,height = size
    covered = np.zeros(len(components),dtype=bool)
    for line in lines:
        for word in line.get('words',[]):
            if word['h'] > height*.06 or word['w'] > width*.8:
                continue
            covered |= ((components[:,0] >= word['x']/width-.002)
                        & (components[:,0] <= (word['x']+word['w'])/width+.002)
                        & (components[:,1] >= word['y']/height-.002)
                        & (components[:,1] <= (word['y']+word['h'])/height+.002))
    return float(components[covered,2].sum()/components[:,2].sum())


def illumination_copy(image):
    gray = np.array(image.convert('L'))
    background = cv2.GaussianBlur(gray,(0,0),max(8,image.width/80))
    flat = cv2.divide(gray,background,scale=245)
    return Image.fromarray(flat)
