import cv2
import time
import tkinter as tk
from tkinter import messagebox

from detector import detect_plate
from tracker import VehicleTracker
from logger import save_infraction

# Ocultar ventana principal de Tkinter
root = tk.Tk()
root.withdraw()

tracker = VehicleTracker()

cap = cv2.VideoCapture(0)

alert_sent = False

# OCR cada 2 segundos
last_ocr_time = 0

# Última vez que se detectó una patente
last_detection_time = time.time()

# Patente actual
plate = None

while True:

    ret, frame = cap.read()

    if not ret:
        break

    # =========================
    # ZONA CENTRAL DE LECTURA
    # =========================

    h, w = frame.shape[:2]

    x1 = int(w * 0.30)
    y1 = int(h * 0.35)

    x2 = int(w * 0.70)
    y2 = int(h * 0.65)

    cv2.rectangle(
        frame,
        (x1, y1),
        (x2, y2),
        (0, 255, 0),
        2
    )

    current_time = time.time()

    # =========================
    # OCR CADA 2 SEGUNDOS
    # =========================

    if current_time - last_ocr_time > 2:

        detected_plate = detect_plate(frame)

        if detected_plate:

            plate = detected_plate
            last_detection_time = current_time

            print("Detectado:", plate)

        last_ocr_time = current_time

    # =========================
    # SI DESAPARECE LA PATENTE
    # =========================

    if current_time - last_detection_time > 5:

        plate = None
        alert_sent = False

        tracker.reset()

    # =========================
    # SI HAY PATENTE
    # =========================

    if plate:

        elapsed = tracker.update(plate)

        # Mostrar patente grande
        cv2.putText(
            frame,
            plate,
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            2,
            (0, 255, 0),
            3
        )

        cv2.putText(
            frame,
            f"Tiempo: {int(elapsed)}s",
            (20, 110),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        if elapsed > 30 and not alert_sent:

            save_infraction(plate)

            messagebox.showwarning(
                "DROP OFF",
                f"Patente: {plate}\n\n"
                "Apoderado estacionado en la entrada "
                "más de 5 minutos.\n\n"
                "Detalles de la sanción enviados por correo."
            )

            alert_sent = True

    else:

        cv2.putText(
            frame,
            "Esperando patente...",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

    cv2.imshow("Drop Off", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()