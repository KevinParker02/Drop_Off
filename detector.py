"""
Detector de patentes mediante EasyOCR, restringido a una zona central (ROI)
de cada frame de video. No analiza el resto de la imagen.
"""
import cv2
import easyocr

from config import ROI_WIDTH_RATIO, ROI_HEIGHT_RATIO
from plate_validator import extract_valid_plate

_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def compute_roi(frame_width: int, frame_height: int):
    """Calcula el rectángulo (x1, y1, x2, y2) de la zona central de lectura."""
    roi_w = int(frame_width * ROI_WIDTH_RATIO)
    roi_h = int(frame_height * ROI_HEIGHT_RATIO)
    x1 = (frame_width - roi_w) // 2
    y1 = (frame_height - roi_h) // 2
    x2 = x1 + roi_w
    y2 = y1 + roi_h
    return x1, y1, x2, y2


class PlateDetector:
    """
    Envoltorio sobre EasyOCR. Se instancia UNA sola vez (el modelo es pesado)
    y se reutiliza para ambas cámaras.
    """

    def __init__(self, use_gpu: bool = False):
        # 'en' funciona bien para lectura alfanumérica de patentes.
        self.reader = easyocr.Reader(["en"], gpu=use_gpu, verbose=False)

    def read_plate_in_roi(self, frame):
        """
        Recibe un frame BGR completo. Recorta únicamente la zona central,
        corre OCR sobre ese recorte y retorna:
            (patente_valida_o_None, roi_box, ocr_box_relativo_o_None)
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = compute_roi(w, h)
        roi_crop = frame[y1:y2, x1:x2]

        if roi_crop.size == 0:
            return None, (x1, y1, x2, y2), None

        gray = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 40, 40)

        results = self.reader.readtext(
            gray,
            detail=1,
            allowlist=_ALLOWLIST,
            paragraph=False,
        )

        best_plate = None
        best_box = None
        best_conf = 0.0

        for (box, text, conf) in results:
            plate = extract_valid_plate(text)
            if plate and conf > best_conf:
                best_plate = plate
                best_conf = conf
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                best_box = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))

        return best_plate, (x1, y1, x2, y2), best_box
