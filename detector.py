import cv2
import easyocr
import re
import torch

reader = None

def detect_plate(frame):

    global reader

    if reader is None:
        print("Cargando EasyOCR...")
        reader = easyocr.Reader(
            ['en'],
            gpu=torch.cuda.is_available()
        )
        print("EasyOCR cargado")

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

    results = reader.readtext(
        roi,
        allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    )

    if results:

        plate = results[0][1].upper()

        plate = re.sub(
            r'[^A-Z0-9]',
            '',
            plate
        )

        if len(plate) not in (5, 6):
            return None

        # Debe contener al menos una letra y un número
        if not re.search(r'[A-Z]', plate):
            return None

        if not re.search(r'[0-9]', plate):
            return None

        return plate

    return None