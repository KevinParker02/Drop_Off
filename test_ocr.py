import cv2
import easyocr

reader = easyocr.Reader(['en'])

img = cv2.imread("data/test.jpg")

# Escalar imagen al doble
img = cv2.resize(
    img,
    None,
    fx=2,
    fy=2,
    interpolation=cv2.INTER_CUBIC
)

results = reader.readtext(img)

for r in results:
    print(r[1])