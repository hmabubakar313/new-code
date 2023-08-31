import cv2  # python-opencv
import numpy as np
import math


def draw_line_from_center(image, x, y):
    height, width, c = image.shape
    img_c1, img_c2 = int(width/2), int(height/2)
    distance = math.sqrt((x-img_c1)**2 + (y-img_c2)**2)
    score = str(int(((1/(1+distance))*1000)))
    cv2.line(image, (x, y), (img_c1, img_c2),
             (0, 255, 0), thickness=2)
    return image, score, distance
