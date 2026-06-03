import cv2
import time
import tkinter as tk
from tkinter import messagebox
import json
import os

from detector import detect_plate
from tracker import VehicleTracker
from logger import save_infraction


class App:

    def __init__(self, root):

        self.root = root
        self.root.title("DROP OFF")
        self.root.geometry("350x250")
        self.root.resizable(False, False)

        self.cap = None
        self.running = False

        self.tracker = VehicleTracker()
        self.alert_sent = False

        self.last_ocr_time = 0
        self.last_detection_time = time.time()

        self.plate = None

        # -------------------------
        # UI
        # -------------------------

        tk.Label(
            root,
            text="Panel de Control DROP OFF",
            font=("Arial", 12, "bold")
        ).pack(pady=10)

        tk.Label(
            root,
            text="Índice de cámara"
        ).pack()

        self.cam_index = tk.IntVar(value=0)

        tk.Entry(
            root,
            textvariable=self.cam_index,
            width=10
        ).pack(pady=5)

        tk.Button(
            root,
            text="Iniciar cámara",
            width=20,
            command=self.start
        ).pack(pady=3)

        tk.Button(
            root,
            text="Ver infracciones",
            width=20,
            command=self.show_infractions
        ).pack(pady=3)

        tk.Button(
            root,
            text="Detener",
            width=20,
            command=self.stop
        ).pack(pady=3)

        tk.Button(
            root,
            text="Salir",
            width=20,
            command=root.quit
        ).pack(pady=3)

    # ---------------------------------
    # INFRACCIONES
    # ---------------------------------

    def show_infractions(self):

        file_path = "infractions.json"

        if not os.path.exists(file_path):

            messagebox.showinfo(
                "Infracciones",
                "No hay registros aún."
            )

            return

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        text = ""

        for i, inf in enumerate(data, 1):

            text += (
                f"{i}. "
                f"Patente: {inf['plate']} "
                f"- Hora: {inf['time']}\n"
            )

        win = tk.Toplevel(self.root)

        win.title("Infracciones")
        win.geometry("450x350")

        txt = tk.Text(win)

        txt.pack(
            expand=True,
            fill="both"
        )

        txt.insert("end", text)

        txt.config(state="disabled")

    # ---------------------------------
    # START
    # ---------------------------------

    def start(self):

        if self.running:
            return

        self.cap = cv2.VideoCapture(
            self.cam_index.get()
        )

        # Menor resolución = menos lag
        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            30
        )

        self.running = True

        self.loop()

    # ---------------------------------
    # STOP
    # ---------------------------------

    def stop(self):

        self.running = False

        if self.cap:

            self.cap.release()

        cv2.destroyAllWindows()

    # ---------------------------------
    # LOOP
    # ---------------------------------

    def loop(self):

        if not self.running:
            return

        ret, frame = self.cap.read()

        if not ret:

            self.stop()

            return

        h, w = frame.shape[:2]

        # Zona OCR
        cv2.rectangle(
            frame,
            (int(w * 0.30), int(h * 0.35)),
            (int(w * 0.70), int(h * 0.65)),
            (0, 255, 0),
            2
        )

        now = time.time()

        # OCR cada 3 segundos
        if now - self.last_ocr_time > 3:

            detected = detect_plate(frame)

            if detected:

                self.plate = detected
                self.last_detection_time = now

                print(
                    "Patente detectada:",
                    detected
                )

            self.last_ocr_time = now

        # Reinicio si desaparece
        if now - self.last_detection_time > 5:

            self.plate = None

            self.alert_sent = False

            self.tracker.reset()

        # -------------------------
        # PATENTE DETECTADA
        # -------------------------

        if self.plate:

            elapsed = self.tracker.update(
                self.plate
            )

            cv2.putText(
                frame,
                self.plate,
                (20, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                3
            )

            cv2.putText(
                frame,
                f"Tiempo: {int(elapsed)}s",
                (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2
            )

            # 5 segundos para pruebas
            if elapsed > 5 and not self.alert_sent:

                save_infraction(
                    self.plate
                )

                messagebox.showwarning(
                    "DROP OFF",
                    f"Patente: {self.plate}\n\n"
                    f"Infracción registrada."
                )

                self.alert_sent = True

        else:

            cv2.putText(
                frame,
                "Esperando patente...",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2
            )

        # Ventana más pequeña
        frame = cv2.resize(
            frame,
            (800, 600)
        )

        cv2.imshow(
            "Drop Off - Camera",
            frame
        )

        if cv2.waitKey(1) & 0xFF == 27:

            self.stop()

            return

        self.root.after(
            10,
            self.loop
        )


root = tk.Tk()

app = App(root)

root.mainloop()