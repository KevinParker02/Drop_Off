"""
Hilo de trabajo por cámara: lee frames del video, corre el detector de patentes
sobre la zona central, actualiza el tracker y entrega al hilo principal (GUI)
tanto el frame ya dibujado (con overlays) como los eventos de dashboard.
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
        self._thread = None
        self._frame_counter = 0

        # Última patente/estado válido detectado, para mostrarlo en la UI
        self.current_plate = None
        self.current_elapsed = 0.0

    def start(self):
        self._stop_flag.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_flag.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self.video_source.release()

    def change_video(self, new_path: str):
        was_running = self._thread is not None and self._thread.is_alive()
        if was_running:
            self.stop()
        self.video_source = VideoSource(new_path)
        self.tracker.reset()
        if was_running:
            self.start()

    def _run(self):
        frame_delay = 1.0 / PLAYBACK_FPS

        while not self._stop_flag.is_set():
            loop_start = time.time()

            frame = self.video_source.read_frame()
            if frame is None:
                time.sleep(frame_delay)
                continue

            self._frame_counter += 1
            run_ocr = (self._frame_counter % OCR_EVERY_N_FRAMES == 0)

            display_frame = frame.copy()

            # El recuadro de la zona de lectura se dibuja SIEMPRE, en cada frame,
            # para que quede fijo en pantalla (no depende de si corre el OCR o no).
            h, w = display_frame.shape[:2]
            x1, y1, x2, y2 = compute_roi(w, h)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), COLOR_ROI_BOX, 2)

            if run_ocr:
                plate, _, ocr_box = self.detector.read_plate_in_roi(frame)

                if plate:
                    event = self.tracker.on_plate_detected(plate)
                    self.current_plate = plate
                    self.current_elapsed = self.tracker.get_elapsed_for_plate(plate)

                    if ocr_box:
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

                    if event:
                        self.event_queue.put(event)

            # Revisa salidas de vehículos (independiente de si hubo OCR este frame)
            departure_events = self.tracker.check_departures()
            for ev in departure_events:
                self.event_queue.put(ev)
                if ev.plate == self.current_plate:
                    self.current_plate = None
                    self.current_elapsed = 0.0

            # Deja el frame disponible para la GUI (descarta el anterior si no se consumió)
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(display_frame)

            elapsed = time.time() - loop_start
            sleep_time = max(0.0, frame_delay - elapsed)
            time.sleep(sleep_time)
