import cv2
import time
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from PIL import Image, ImageTk
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import json
import os
from ctypes import windll
try:
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from detector import detect_plate
from tracker import VehicleTracker
from logger import save_infraction

import torch

print("CUDA disponible:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))

# ─────────────────────────────────────────────
#  TEMA
# ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

ACCENT       = "#00bfff"
ACCENT2      = "#1a7abf"
BG_APP       = "#0f1e2d"
BG_FRAME     = "#162840"
BG_PANEL     = "#0a1520"
BTN_MAIN     = "#1a4a70"
BTN_HOVER    = "#2266a0"
BTN_RED      = "#7a1515"
BTN_RED_H    = "#aa2222"
TEXT_PRIMARY = "#e8f4fd"
TEXT_MUTED   = "#7ab8d8"
GREEN        = "#00e676"
RED          = "#ff5252"
BORDER       = "#2a5a8a"

# Panel de video — aprox 50% de 1920x1080
VIDEO_W = 800
VIDEO_H = 450


class App(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("DROP OFF  -  Sistema de Vigilancia")

        # Ventana total: panel izquierdo 280 + video 800 + márgenes
        WIN_W = 280 + VIDEO_W + 48
        WIN_H = VIDEO_H + 160
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.resizable(True, True)
        self.configure(fg_color=BG_APP)

        # Barra de título oscura en Windows
        try:
            from ctypes import windll, byref, sizeof, c_int
            HWND = windll.user32.GetParent(self.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(
                HWND, 20, byref(c_int(1)), sizeof(c_int(1))
            )
        except Exception:
            pass

        self.cap                 = None
        self.running             = False
        self.tracker             = VehicleTracker()
        self.alert_sent          = False
        self.last_ocr_time       = 0
        self.last_detection_time = time.time()
        self.plate               = None
        self._photo              = None

        self._build_ui()
        self._animate_status()

    # ─────────────────────────────────────────
    #  BUILD UI
    # ─────────────────────────────────────────

    def _build_ui(self):

        # ══ BARRA DE TÍTULO ══════════════════════
        title_bar = ctk.CTkFrame(
            self, fg_color=BG_PANEL,
            corner_radius=0, height=46
        )
        title_bar.pack(fill="x", side="top")
        title_bar.pack_propagate(False)

        ctk.CTkLabel(
            title_bar,
            text="DROP OFF  —  Panel de Control",
            font=ctk.CTkFont("Segoe UI", 12, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left", padx=(20, 0), pady=14)

        # Línea cyan
        ctk.CTkFrame(
            self, height=2,
            fg_color=ACCENT, corner_radius=0
        ).pack(fill="x")

        # ══ CUERPO ═══════════════════════════════
        body = ctk.CTkFrame(self, fg_color=BG_APP, corner_radius=0)
        body.pack(fill="both", expand=True, padx=10, pady=(8, 0))

        # ── COLUMNA IZQUIERDA ─────────────────────
        left = ctk.CTkFrame(
            body, fg_color=BG_FRAME,
            corner_radius=10,
            border_width=1, border_color=BORDER,
            width=260
        )
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(
            left,
            text="SISTEMA DE DETECCION",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=16, pady=(14, 0))

        ctk.CTkLabel(
            left,
            text="Vigilancia Zona Drop-Off",
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(2, 8))

        ctk.CTkFrame(
            left, height=1,
            fg_color=BORDER, corner_radius=0
        ).pack(fill="x", padx=16, pady=(0, 10))

        # Campo cámara
        ctk.CTkLabel(
            left,
            text="INDICE DE CAMARA",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=16)

        self.cam_index = ctk.CTkEntry(
            left,
            width=228, height=36,
            fg_color=BG_PANEL,
            border_color=BORDER, border_width=1,
            text_color=ACCENT,
            font=ctk.CTkFont("Consolas", 13, "bold"),
            corner_radius=6,
        )
        self.cam_index.insert(0, "0")
        self.cam_index.pack(padx=16, pady=(4, 10))

        # Panel estado
        sf = ctk.CTkFrame(
            left, fg_color=BG_PANEL,
            corner_radius=8,
            border_width=1, border_color=BORDER,
        )
        sf.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            sf,
            text="ESTADO DEL SISTEMA",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", padx=12, pady=(8, 3))

        row = ctk.CTkFrame(sf, fg_color="transparent")
        row.pack(anchor="w", padx=12, pady=(0, 3))

        self._dot_canvas = tk.Canvas(
            row, width=12, height=12,
            bg=BG_PANEL, highlightthickness=0
        )
        self._dot_canvas.pack(side="left", padx=(0, 6))

        self._status_label = ctk.CTkLabel(
            row,
            text="Inactivo",
            font=ctk.CTkFont("Segoe UI", 10, "bold"),
            text_color=RED,
        )
        self._status_label.pack(side="left")

        self._plate_label = ctk.CTkLabel(
            sf,
            text="Patente:  —",
            font=ctk.CTkFont("Consolas", 11),
            text_color=TEXT_MUTED,
        )
        self._plate_label.pack(anchor="w", padx=12, pady=(0, 10))

        # Botones
        btn_cfg = dict(
            width=228, height=38,
            corner_radius=8,
            font=ctk.CTkFont("Segoe UI", 11, "bold"),
            fg_color=BTN_MAIN,
            hover_color=BTN_HOVER,
            text_color=TEXT_PRIMARY,
            border_width=1, border_color=BORDER,
        )

        ctk.CTkButton(
            left, text="▶   Iniciar camara",
            command=self.start, **btn_cfg
        ).pack(pady=(0, 6))

        ctk.CTkButton(
            left, text="Ver infracciones",
            command=self.show_infractions, **btn_cfg
        ).pack(pady=(0, 6))

        ctk.CTkButton(
            left, text="⏹   Detener",
            command=self.stop,
            fg_color=BTN_RED,
            hover_color=BTN_RED_H,
            **{k: v for k, v in btn_cfg.items()
               if k not in ("fg_color", "hover_color")}
        ).pack(pady=(0, 14))

        # ── COLUMNA DERECHA: video ────────────────
        right = ctk.CTkFrame(
            body, fg_color=BG_FRAME,
            corner_radius=10,
            border_width=1, border_color=BORDER,
        )
        right.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            right,
            text="VISTA EN VIVO",
            font=ctk.CTkFont("Segoe UI", 8, "bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self._video_canvas = tk.Canvas(
            right,
            bg="#000000",
            highlightthickness=1,
            highlightbackground=BORDER,
        )

        self._video_canvas.pack(
            fill="both",
            expand=True,
            padx=4,
            pady=4
        )
        self.after(100, self._draw_no_signal)

        # ══ FOOTER ═══════════════════════════════
        footer = ctk.CTkFrame(
            self, fg_color=BG_PANEL,
            corner_radius=0, height=26
        )
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text="DROP OFF v2.0  -  Seguridad Escolar",
            font=ctk.CTkFont("Segoe UI", 8),
            text_color="#2a5a7a",
        ).pack(side="left", padx=12, pady=4)

        self._clock_label = ctk.CTkLabel(
            footer, text="",
            font=ctk.CTkFont("Consolas", 8),
            text_color=TEXT_MUTED,
        )
        self._clock_label.pack(side="right", padx=12, pady=4)
        self._update_clock()

    # ─────────────────────────────────────────
    #  SIN SEÑAL
    # ─────────────────────────────────────────

    def _draw_no_signal(self):

        self._video_canvas.delete("all")

        canvas_w = self._video_canvas.winfo_width()
        canvas_h = self._video_canvas.winfo_height()

        # Si todavía no está inicializado
        if canvas_w < 10:
            canvas_w = VIDEO_W
        if canvas_h < 10:
            canvas_h = VIDEO_H

        cx = canvas_w // 2
        cy = canvas_h // 2

        self._video_canvas.create_text(
            cx,
            cy - 40,
            text="📷",
            font=("Segoe UI Emoji", 48),
            fill="#1a3a5a"
        )

        self._video_canvas.create_text(
            cx,
            cy + 30,
            text="Sin señal — presiona Iniciar cámara",
            font=("Segoe UI", 16),
            fill="#1e4a6a"
        )

    # ─────────────────────────────────────────
    #  UTILIDADES UI
    # ─────────────────────────────────────────

    def _update_clock(self):
        self._clock_label.configure(text=time.strftime("%H:%M:%S"))
        self.after(1000, self._update_clock)

    def _animate_status(self):
        self._dot_on = not getattr(self, "_dot_on", False)
        color = GREEN if self.running else RED
        fill  = color if self._dot_on else BG_PANEL

        self._dot_canvas.delete("all")
        self._dot_canvas.create_oval(
            1, 1, 11, 11,
            fill=fill, outline=color, width=2
        )
        self._status_label.configure(
            text="Activo — Camara en vivo" if self.running else "Inactivo",
            text_color=GREEN if self.running else RED,
        )
        self._plate_label.configure(
            text=f"Patente:  {self.plate}" if self.plate else "Patente:  —",
            text_color=ACCENT if self.plate else TEXT_MUTED,
        )
        self.after(500, self._animate_status)

    # ─────────────────────────────────────────
    #  INFRACCIONES
    # ─────────────────────────────────────────

    def show_infractions(self):

        file_path = "infractions.json"

        if not os.path.exists(file_path):
            CTkMessagebox(
                title="Infracciones",
                message="No hay registros aun.",
                icon="info",
                width=340, height=200,
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        win = ctk.CTkToplevel(self)
        win.title("Registro de Infracciones")
        win.geometry("660x460")
        win.configure(fg_color=BG_APP)
        win.resizable(True, True)
        win.grab_set()
        win.after(150, win.lift)

        ctk.CTkLabel(
            win,
            text="Infracciones registradas",
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(anchor="w", padx=18, pady=(14, 8))

        tree_frame = ctk.CTkFrame(
            win, fg_color=BG_FRAME,
            corner_radius=8,
            border_width=1, border_color=BORDER,
        )
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        cell_font    = tkfont.Font(family="Consolas", size=12)
        heading_font = tkfont.Font(family="Segoe UI",  size=12, weight="bold")

        style = ttk.Style(win)
        style.theme_use("default")
        style.configure(
            "Drop.Treeview",
            background=BG_PANEL,
            foreground=TEXT_PRIMARY,
            fieldbackground=BG_PANEL,
            rowheight=38,
            font=cell_font,
            borderwidth=0,
        )
        style.configure(
            "Drop.Treeview.Heading",
            background=BG_FRAME,
            foreground=ACCENT,
            font=heading_font,
            relief="flat",
        )
        style.map(
            "Drop.Treeview",
            background=[("selected", ACCENT2)],
        )

        tree = ttk.Treeview(
            tree_frame,
            columns=("#", "Patente", "Hora"),
            show="headings",
            style="Drop.Treeview",
        )
        tree.heading("#",       text="#")
        tree.heading("Patente", text="Patente")
        tree.heading("Hora",    text="Hora / Fecha")
        tree.column("#",        width=50,  anchor="center", minwidth=40)
        tree.column("Patente",  width=180, anchor="center", minwidth=120)
        tree.column("Hora",     width=380, anchor="w",      minwidth=180)

        sb = ttk.Scrollbar(
            tree_frame, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 4))
        tree.pack(fill="both", expand=True, padx=6, pady=6)

        for i, inf in enumerate(data, 1):
            tree.insert("", "end",
                         values=(i, inf["plate"], inf["time"]))

    # ─────────────────────────────────────────
    #  START
    # ─────────────────────────────────────────

    def start(self):

        if self.running:
            return

        try:
            idx = int(self.cam_index.get())
        except ValueError:
            idx = 0

        self.cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.running = True
        self.loop()

    # ─────────────────────────────────────────
    #  STOP
    # ─────────────────────────────────────────

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.after(100, self._draw_no_signal)

    # ─────────────────────────────────────────
    #  LOOP
    # ─────────────────────────────────────────

    def loop(self):

        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.stop()
            return

        h, w = frame.shape[:2]

        # Zona OCR
        cv2.rectangle(frame,
            (int(w * 0.25), int(h * 0.30)),
            (int(w * 0.75), int(h * 0.70)),
            (0, 191, 255), 2)
        cv2.rectangle(frame,
            (int(w * 0.24), int(h * 0.29)),
            (int(w * 0.76), int(h * 0.71)),
            (30, 100, 160), 1)

        now = time.time()

        if now - self.last_ocr_time > 3:
            detected = detect_plate(frame)
            if detected:
                self.plate = detected
                self.last_detection_time = now
                print("Patente detectada:", detected)
            self.last_ocr_time = now

        if now - self.last_detection_time > 5:
            self.plate = None
            self.alert_sent = False
            self.tracker.reset()

        if self.plate:
            elapsed = self.tracker.update(self.plate)

            overlay = frame.copy()
            cv2.rectangle(overlay, (10, 10), (460, 140), (10, 30, 50), -1)
            cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

            cv2.putText(frame, self.plate,
                        (20, 78), cv2.FONT_HERSHEY_SIMPLEX,
                        2.4, (0, 191, 255), 3)
            cv2.putText(frame, f"Tiempo: {int(elapsed)}s",
                        (20, 122), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (135, 206, 235), 2)

            if elapsed > 5 and not self.alert_sent:
                save_infraction(self.plate)
                alert = ctk.CTkToplevel(self)
                alert.title("DROP OFF - Infracción")
                alert.geometry("500x300")
                alert.resizable(False, False)
                alert.grab_set()

                ctk.CTkLabel(
                    alert,
                    text="⚠ INFRACCIÓN DETECTADA",
                    font=ctk.CTkFont("Segoe UI", 22, "bold"),
                    text_color="#ff5252"
                ).pack(pady=(20, 10))

                ctk.CTkLabel(
                    alert,
                    text=(
                        f"Patente: {self.plate}\n\n"
                        "Vehículo estacionado más de 5 minutos.\n"
                        "Infracción registrada y apoderado notificado."
                    ),
                    justify="center",
                    font=ctk.CTkFont("Segoe UI", 15)
                ).pack(pady=10)

                ctk.CTkButton(
                    alert,
                    text="Aceptar",
                    command=alert.destroy,
                    width=150
                ).pack(pady=20)
                self.alert_sent = True

        else:
            cv2.putText(frame, "Esperando patente...",
                        (20, 46), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 120, 200), 2)

        # Convertir frame
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        # Tamaño REAL del canvas
        canvas_w = self._video_canvas.winfo_width()
        canvas_h = self._video_canvas.winfo_height()

        # Evitar errores al iniciar
        if canvas_w < 10 or canvas_h < 10:
            self.after(16, self.loop)
            return

        # Ajustar imagen al tamaño del canvas
        pil_img = pil_img.resize(
            (canvas_w, canvas_h),
            Image.LANCZOS
        )

        self._photo = ImageTk.PhotoImage(pil_img)

        self._video_canvas.delete("all")
        self._video_canvas.create_image(
            0,
            0,
            anchor="nw",
            image=self._photo
        )

        self.after(16, self.loop)


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()