"""
Configuración central del sistema Drop-Off - Genios Traviesos.
Todas las constantes ajustables del proyecto viven aquí.
"""
import os
import sys

# --- Rutas ---
# Cuando el programa corre como script normal, BASE_DIR es la carpeta del proyecto.
# Cuando corre empaquetado como .exe (PyInstaller), sys.frozen es True y __file__
# apunta a una carpeta temporal de extracción; en ese caso usamos la carpeta donde
# realmente está el .exe, para que /videos y el JSON de registros persistan entre
# ejecuciones en vez de perderse en una carpeta temporal.
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VIDEOS_DIR = os.path.join(BASE_DIR, "videos")

# Nombres esperados de los videos por defecto dentro de /videos
DEFAULT_VIDEO_CAM1 = os.path.join(VIDEOS_DIR, "camera1.mp4")
DEFAULT_VIDEO_CAM2 = os.path.join(VIDEOS_DIR, "camera2.mp4")

# Extensiones aceptadas como fuente de cámara: video (con loop) o imagen fija
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp")

# --- Persistencia del dashboard ---
RECORDS_FILE = os.path.join(BASE_DIR, "dashboard_records.json")

# --- Parámetros de detección ---
# Umbral de tiempo detenido (segundos) para considerar "Pasado de tiempo"
TIME_THRESHOLD_SECONDS = 5.0

# Tiempo (segundos) sin ver la patente para considerar que el vehículo se retiró
GRACE_PERIOD_SECONDS = 1.5

# Cada cuántos frames se corre el OCR (para no saturar la CPU)
OCR_EVERY_N_FRAMES = 8

# Proporción del frame que ocupa la zona central de lectura (ROI)
# Ej: 0.5 significa que el ROI ocupa el 50% del ancho/alto, centrado.
ROI_WIDTH_RATIO = 0.55
ROI_HEIGHT_RATIO = 0.5

# Tamaño de despliegue de cada panel de cámara en la interfaz
VIDEO_DISPLAY_WIDTH = 420
VIDEO_DISPLAY_HEIGHT = 260

# FPS objetivo de reproducción simulada
PLAYBACK_FPS = 25

# --- Patentes chilenas ---
# Formato antiguo: 2 letras + 4 dígitos (ej: AB1234)
# Formato nuevo (2007+): 4 letras + 2 dígitos (ej: BXCV12)
PLATE_REGEX_OLD = r"^[A-Z]{2}\d{4}$"
PLATE_REGEX_NEW = r"^[A-Z]{4}\d{2}$"

# --- Colores (tema oscuro, coherente con el mockup) ---
COLOR_BG = "#1a1a1a"
COLOR_PANEL = "#242424"
COLOR_CARD = "#0f1720"
COLOR_ACCENT = "#3b82f6"
COLOR_TEXT_LIGHT = "#e5e7eb"
COLOR_TEXT_MUTED = "#94a3b8"
COLOR_ACTIVE = "#22c55e"
COLOR_INACTIVE = "#ef4444"
COLOR_WARNING = "#f59e0b"
COLOR_OK_ROW = "#14532d"
COLOR_BAD_ROW = "#7f1d1d"
COLOR_ROI_BOX = (59, 130, 246)   # BGR para cv2 (azul)
COLOR_PLATE_BOX = (34, 197, 94)  # BGR para cv2 (verde) - patente válida detectada

# --- Estados / Acciones para el dashboard ---
STATE_OK = "Rango aceptable"
STATE_OVER = "Pasado de tiempo"
ACTION_NONE = "Ninguna"
ACTION_FINE = "Notificación y multa"
