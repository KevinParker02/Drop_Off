"""
Manejo de la fuente de "cámara" para una cámara simulada: puede ser un archivo
de VIDEO (con loop automático) o una IMAGEN fija (se repite el mismo frame,
simulando una cámara mirando una escena estática). No se usa la webcam.
"""
import os
import cv2

from config import VIDEOS_DIR, VIDEO_EXTENSIONS, IMAGE_EXTENSIONS

VALID_EXTENSIONS = VIDEO_EXTENSIONS + IMAGE_EXTENSIONS


def find_default_video(filename_hint: str) -> str | None:
    """
    Busca en la carpeta /videos un archivo (video o imagen) cuyo nombre
    (sin extensión) coincida con filename_hint (ej: 'camera1').
    Retorna la ruta completa o None.
    """
    if not os.path.isdir(VIDEOS_DIR):
        return None

    for fname in os.listdir(VIDEOS_DIR):
        name, ext = os.path.splitext(fname)
        if name.lower() == filename_hint.lower() and ext.lower() in VALID_EXTENSIONS:
            return os.path.join(VIDEOS_DIR, fname)
    return None


def is_image_file(path: str) -> bool:
    _, ext = os.path.splitext(path)
    return ext.lower() in IMAGE_EXTENSIONS


class VideoSource:
    """
    Envoltorio sobre la fuente de frames de una cámara simulada.

    - Si `path` es un VIDEO: usa cv2.VideoCapture y hace loop automático
      al llegar al final.
    - Si `path` es una IMAGEN: la carga una sola vez y `read_frame()`
      siempre retorna una copia de esa misma imagen (cámara "fija").
    """

    def __init__(self, path: str):
        self.path = path
        self.cap = None
        self.is_image = is_image_file(path)
        self._static_frame = None
        self._open()

    def _open(self):
        if self.is_image:
            frame = cv2.imread(self.path)
            if frame is None:
                raise FileNotFoundError(f"No se pudo abrir la imagen: {self.path}")
            self._static_frame = frame
        else:
            self.cap = cv2.VideoCapture(self.path)
            if not self.cap.isOpened():
                raise FileNotFoundError(f"No se pudo abrir el video: {self.path}")

    def read_frame(self):
        """
        Retorna el siguiente frame.
        - Imagen: siempre retorna una copia del frame estático.
        - Video: si terminó, reinicia desde el principio (loop).
        """
        if self.is_image:
            return self._static_frame.copy()

        ok, frame = self.cap.read()
        if not ok:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
            if not ok:
                return None
        return frame

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def change_source(self, new_path: str):
        self.release()
        self.path = new_path
        self.is_image = is_image_file(new_path)
        self._static_frame = None
        self._open()
