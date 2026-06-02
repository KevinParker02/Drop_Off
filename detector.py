import cv2
import easyocr

reader = easyocr.Reader(['en'])

def detect_plate(frame):

    h, w = frame.shape[:2]

    roi = frame[
        int(h * 0.35):int(h * 0.65),
        int(w * 0.30):int(w * 0.70)
    ]

    roi = cv2.resize(
        roi,
        None,
        fx=1.5,
        fy=1.5,
        interpolation=cv2.INTER_CUBIC
    )

    results = reader.readtext(roi)

    if results:
        return results[0][1]

    return None