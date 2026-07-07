"""
Hilo de trabajo por cámara: lee frames del video y los entrega a la GUI a un
ritmo constante (nunca espera al OCR). El reconocimiento de patente corre en
un hilo aparte, para que el video no se congele mientras EasyOCR procesa un
recorte (lo cual puede tardar cientos de milisegundos o más en CPU).
"""
import threading
import queue
import time
import cv2

from config import OCR_EVERY_N_FRAMES, PLAYBACK_FPS, COLOR_ROI_BOX, COLOR_PLATE_BOX
from video_source import VideoSource
from tracker import PlateTracker
from detector import compute_roi


class CameraWorker:
    def __init__(self, camera_label: str, video_path: str, detector):
        self.camera_label = camera_label
        self.detector = detector
        self.tracker = PlateTracker(camera_label)

        self.video_source = VideoSource(video_path)

        self.frame_queue: "queue.Queue" = queue.Queue(maxsize=2)
        self.event_queue: "queue.Queue" = queue.Queue()

        self._stop_flag = threading.Event()
        self._capture_thread = None
        self._ocr_thread = None
        self._frame_counter = 0

        # Comunicación con el hilo de OCR: solo se guarda el frame MÁS RECIENTE
        # pendiente de analizar. Si el OCR va lento, se descartan los frames
        # intermedios (no se acumulan), así nunca genera atraso ni bloqueo.
        self._pending_frame = None
        self._pending_lock = threading.Lock()

        # Último resultado de OCR conocido, para dibujarlo sobre el video
        # mientras se espera el siguiente resultado.
        self._last_plate = None
        self._last_ocr_box = None
        self._result_lock = threading.Lock()

        # Última patente/estado válido detectado, para mostrarlo en la UI
        self.current_plate = None
        self.current_elapsed = 0.0

    def start(self):
        self._stop_flag.clear()
        self._capture_thread = threading.Thread(target=self._run_capture, daemon=True)
        self._ocr_thread = threading.Thread(target=self._run_ocr_loop, daemon=True)
        self._capture_thread.start()
        self._ocr_thread.start()

    def stop(self):
        self._stop_flag.set()
        if self._capture_thread is not None:
            self._capture_thread.join(timeout=2)
        if self._ocr_thread is not None:
            self._ocr_thread.join(timeout=2)
        self.video_source.release()

    def change_video(self, new_path: str):
        was_running = self._capture_thread is not None and self._capture_thread.is_alive()
        if was_running:
            self.stop()
        self.video_source = VideoSource(new_path)
        self.tracker.reset()
        self._pending_frame = None
        self._last_plate = None
        self._last_ocr_box = None
        self.current_plate = None
        self.current_elapsed = 0.0
        if was_running:
            self.start()

    # ------------------------------------------------------------------ #
    # Hilo de captura: SIEMPRE corre al ritmo de PLAYBACK_FPS, sin importar
    # cuánto tarde el OCR. Nunca bloquea esperando al reconocimiento.
    # ------------------------------------------------------------------ #
    def _run_capture(self):
        frame_delay = 1.0 / PLAYBACK_FPS

        while not self._stop_flag.is_set():
            loop_start = time.time()

            frame = self.video_source.read_frame()
            if frame is None:
                time.sleep(frame_delay)
                continue

            self._frame_counter += 1
            should_request_ocr = (self._frame_counter % OCR_EVERY_N_FRAMES == 0)

            if should_request_ocr:
                # Entrega el frame al hilo de OCR (no bloqueante: solo deja
                # el más reciente disponible, no forma cola).
                with self._pending_lock:
                    self._pending_frame = frame.copy()

            display_frame = frame.copy()

            # El recuadro de la zona de lectura se dibuja SIEMPRE, en cada
            # frame, para que quede fijo en pantalla.
            h, w = display_frame.shape[:2]
            x1, y1, x2, y2 = compute_roi(w, h)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), COLOR_ROI_BOX, 2)

            # Dibuja el último resultado de OCR conocido (puede venir de un
            # frame algo anterior, ya que el OCR corre en paralelo).
            with self._result_lock:
                plate = self._last_plate
                ocr_box = self._last_ocr_box

            if plate and ocr_box:
                bx1, by1, bx2, by2 = ocr_box
                cv2.rectangle(
                    display_frame,
                    (x1 + bx1, y1 + by1),
                    (x1 + bx2, y1 + by2),
                    COLOR_PLATE_BOX,
                    2,
                )
                cv2.putText(
                    display_frame, plate, (x1 + bx1, y1 + by1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_PLATE_BOX, 2,
                )

            # Revisa salidas de vehículos (rápido, no depende del OCR)
            departure_events = self.tracker.check_departures()
            for ev in departure_events:
                self.event_queue.put(ev)
                if ev.plate == self.current_plate:
                    self.current_plate = None
                    self.current_elapsed = 0.0

            # Deja el frame disponible para la GUI (descarta el anterior si
            # no se consumió, para no acumular atraso)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(display_frame)

            elapsed = time.time() - loop_start
            sleep_time = max(0.0, frame_delay - elapsed)
            time.sleep(sleep_time)

    # ------------------------------------------------------------------ #
    # Hilo de OCR: procesa el frame pendiente más reciente, a su propio
    # ritmo, sin afectar la reproducción del video.
    # ------------------------------------------------------------------ #
    def _run_ocr_loop(self):
        while not self._stop_flag.is_set():
            frame_to_process = None
            with self._pending_lock:
                if self._pending_frame is not None:
                    frame_to_process = self._pending_frame
                    self._pending_frame = None

            if frame_to_process is None:
                time.sleep(0.03)
                continue

            plate, _, ocr_box = self.detector.read_plate_in_roi(frame_to_process)

            with self._result_lock:
                self._last_plate = plate
                self._last_ocr_box = ocr_box

            if plate:
                event = self.tracker.on_plate_detected(plate)
                self.current_plate = plate
                self.current_elapsed = self.tracker.get_elapsed_for_plate(plate)
                if event:
                    self.event_queue.put(event)
