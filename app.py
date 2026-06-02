import cv2
import time
import tkinter as tk
from tkinter import messagebox
import json
import os

from detector import detect_plate
from tracker import VehicleTracker
from logger import save_infraction


# =========================
# APP
# =========================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Panel de control - DROPOFF")

        self.cap = None
        self.running = False

        self.tracker = VehicleTracker()
        self.alert_sent = False
        self.last_ocr_time = 0
        self.last_detection_time = time.time()
        self.plate = None

        # UI
        tk.Label(root, text="Seleccionar cámara").pack()

        self.cam_index = tk.IntVar(value=0)
        tk.Entry(root, textvariable=self.cam_index).pack()

        tk.Button(root, text="Iniciar cámara", command=self.start).pack()
        tk.Button(root, text="Infracciones", command=self.show_infractions).pack()
        tk.Button(root, text="Detener", command=self.stop).pack()
        tk.Button(root, text="Salir", command=root.quit).pack()

    # =========================
    # MOSTRAR INFRACCIONES
    # =========================
    def show_infractions(self):

        file_path = "infractions.json"

        if not os.path.exists(file_path):
            messagebox.showinfo("Infracciones", "No hay registros aún.")
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        text = ""

        for i, inf in enumerate(data, 1):
            text += f"{i}. Patente: {inf['plate']} - Hora: {inf['time']}\n"

        win = tk.Toplevel(self.root)
        win.title("Infracciones")
        win.geometry("400x400")

        txt = tk.Text(win)
        txt.pack(expand=True, fill="both")

        txt.insert("end", text)
        txt.config(state="disabled")

    # =========================
    # START CAM
    # =========================
    def start(self):
        if self.running:
            return

        self.cap = cv2.VideoCapture(self.cam_index.get())

        # mejorar calidad cámara
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.running = True
        self.loop()

    # =========================
    # STOP
    # =========================
    def stop(self):
        self.running = False

        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()

    # =========================
    # LOOP PRINCIPAL
    # =========================
    def loop(self):

        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.stop()
            return

        h, w = frame.shape[:2]

        # ROI visual
        cv2.rectangle(frame,
                      (int(w * 0.30), int(h * 0.35)),
                      (int(w * 0.70), int(h * 0.65)),
                      (0, 255, 0), 2)

        now = time.time()

        # OCR cada 2s
        if now - self.last_ocr_time > 2:

            detected = detect_plate(frame)

            if detected:
                self.plate = detected
                self.last_detection_time = now

            self.last_ocr_time = now

        # timeout reset
        if now - self.last_detection_time > 5:
            self.plate = None
            self.alert_sent = False
            self.tracker.reset()

        # tracking
        if self.plate:

            elapsed = self.tracker.update(self.plate)

            cv2.putText(frame, self.plate, (20, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)

            cv2.putText(frame, f"{int(elapsed)}s", (20, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            #Timer de infraccion -Modificado para probar
            if elapsed > 5 and not self.alert_sent:
                save_infraction(self.plate)

                messagebox.showwarning(
                    "DROP OFF",
                    f"Patente: {self.plate}\nInfracción registrada"
                )

                self.alert_sent = True

        else:
            cv2.putText(frame, "Esperando patente...", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow("Drop Off - Camera", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            self.stop()
            return

        self.root.after(10, self.loop)


# =========================
# MAIN
# =========================
root = tk.Tk()
root.geometry("1000x700")

app = App(root)

root.mainloop()