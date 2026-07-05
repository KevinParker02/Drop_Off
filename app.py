"""
Interfaz gráfica del sistema Drop-Off - Genios Traviesos.
Construida con customtkinter, con un diseño oscuro y ordenado.
"""
import os
import json
import threading
import queue

import cv2
import customtkinter as ctk
from tkinter import ttk, filedialog
from PIL import Image, ImageDraw, ImageFont
from CTkMessagebox import CTkMessagebox

import config
from detector import PlateDetector
from camera_worker import CameraWorker
from video_source import find_default_video
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _make_placeholder_ctkimage(width, height, text="Sin señal"):
    """
    Genera una imagen fija (placeholder) con el texto centrado, para mostrar
    en los paneles de cámara cuando no hay transmisión activa. Se dibuja el
    texto directamente sobre la imagen para evitar que el texto del widget
    quede superpuesto sobre el último frame capturado.
    """
    img = Image.new("RGB", (width, height), color=(10, 10, 10))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((width - tw) / 2, (height - th) / 2), text, fill=(148, 163, 184), font=font)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(width, height))


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Drop-Off · Genios Traviesos")
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=config.COLOR_BG)

        self.detector = None
        self.workers: dict[str, CameraWorker] = {}
        self.video_paths = {"Cámara 1": None, "Cámara 2": None}
        self.is_running = False
        self.next_id = 1

        self._build_layout()
        self._load_records_from_disk()
        self._autodetect_videos()
        self._poll_workers()

    # ------------------------------------------------------------------ #
    # Construcción de la interfaz
    # ------------------------------------------------------------------ #
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=300, corner_radius=0, fg_color=config.COLOR_PANEL)
        sidebar.grid(row=0, column=0, sticky="nsw")
        sidebar.grid_propagate(False)

        title = ctk.CTkLabel(
            sidebar, text="Drop-Off\nGenios Traviesos",
            font=ctk.CTkFont(size=22, weight="bold"),
            justify="center",
        )
        title.pack(pady=(30, 20), padx=20)

        # --- Tarjeta de estado del sistema ---
        status_card = ctk.CTkFrame(sidebar, fg_color=config.COLOR_CARD, corner_radius=12)
        status_card.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            status_card, text="ESTADO DEL SISTEMA",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=config.COLOR_ACCENT,
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.status_dot_label = ctk.CTkLabel(
            status_card, text="● Inactivo",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=config.COLOR_INACTIVE,
        )
        self.status_dot_label.pack(anchor="w", padx=15, pady=(0, 10))

        self.plate_cam1_label = ctk.CTkLabel(
            status_card, text="Cámara 1 · Patente: —",
            font=ctk.CTkFont(size=13), text_color=config.COLOR_TEXT_MUTED,
        )
        self.plate_cam1_label.pack(anchor="w", padx=15, pady=(0, 4))

        self.plate_cam2_label = ctk.CTkLabel(
            status_card, text="Cámara 2 · Patente: —",
            font=ctk.CTkFont(size=13), text_color=config.COLOR_TEXT_MUTED,
        )
        self.plate_cam2_label.pack(anchor="w", padx=15, pady=(0, 15))

        # --- Estado de videos cargados ---
        self.video_status_label = ctk.CTkLabel(
            sidebar, text="Buscando videos/imágenes...",
            font=ctk.CTkFont(size=12), text_color=config.COLOR_TEXT_MUTED,
            justify="left", wraplength=260,
        )
        self.video_status_label.pack(anchor="w", padx=25, pady=(10, 10))

        # --- Botones ---
        self.start_button = ctk.CTkButton(
            sidebar, text="▶  Iniciar Prueba", height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=config.COLOR_ACTIVE, hover_color="#16a34a",
            command=self.start_simulation,
        )
        self.start_button.pack(fill="x", padx=20, pady=(20, 8))

        self.stop_button = ctk.CTkButton(
            sidebar, text="■  Detener", height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=config.COLOR_INACTIVE, hover_color="#b91c1c",
            command=self.stop_simulation, state="disabled",
        )
        self.stop_button.pack(fill="x", padx=20, pady=8)

        self.load_button = ctk.CTkButton(
            sidebar, text="📁  Cargar Videos/Imágenes", height=40,
            font=ctk.CTkFont(size=14),
            fg_color="#334155", hover_color="#475569",
            command=self.load_videos_manually,
        )
        self.load_button.pack(fill="x", padx=20, pady=8)

        self.clear_button = ctk.CTkButton(
            sidebar, text="🗑  Limpiar Registros", height=40,
            font=ctk.CTkFont(size=14),
            fg_color="#334155", hover_color="#475569",
            command=self.clear_records,
        )
        self.clear_button.pack(fill="x", padx=20, pady=8)

        footer = ctk.CTkLabel(
            sidebar, text=f"Umbral de sanción: {config.TIME_THRESHOLD_SECONDS:.0f} s",
            font=ctk.CTkFont(size=11), text_color=config.COLOR_TEXT_MUTED,
        )
        footer.pack(side="bottom", pady=15)

    def _build_main_area(self):
        main_area = ctk.CTkFrame(self, fg_color=config.COLOR_BG)
        main_area.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
        main_area.grid_rowconfigure(0, weight=2)
        main_area.grid_rowconfigure(1, weight=3)
        main_area.grid_columnconfigure(0, weight=1)

        # --- Fila de cámaras ---
        cameras_row = ctk.CTkFrame(main_area, fg_color=config.COLOR_BG)
        cameras_row.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        cameras_row.grid_columnconfigure(0, weight=1)
        cameras_row.grid_columnconfigure(1, weight=1)
        cameras_row.grid_rowconfigure(0, weight=1)

        self.cam1_frame, self.cam1_video_label = self._build_camera_panel(cameras_row, "Cámara 1")
        self.cam1_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self.cam2_frame, self.cam2_video_label = self._build_camera_panel(cameras_row, "Cámara 2")
        self.cam2_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # --- Dashboard ---
        dashboard_frame = ctk.CTkFrame(main_area, fg_color=config.COLOR_PANEL, corner_radius=12)
        dashboard_frame.grid(row=1, column=0, sticky="nsew")
        dashboard_frame.grid_rowconfigure(1, weight=1)
        dashboard_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dashboard_frame, text="Registro de Detecciones",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))

        self._build_dashboard_table(dashboard_frame)

    def _build_camera_panel(self, parent, label_text):
        frame = ctk.CTkFrame(parent, fg_color=config.COLOR_PANEL, corner_radius=12)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text=label_text, font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(12, 5))

        video_label = ctk.CTkLabel(
            frame, text="", fg_color="#0a0a0a", corner_radius=10,
            width=config.VIDEO_DISPLAY_WIDTH, height=config.VIDEO_DISPLAY_HEIGHT,
        )
        placeholder = _make_placeholder_ctkimage(config.VIDEO_DISPLAY_WIDTH, config.VIDEO_DISPLAY_HEIGHT)
        video_label.configure(image=placeholder)
        video_label.image = placeholder
        video_label.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 8))

        info_label = ctk.CTkLabel(
            frame, text="Patente: — · Tiempo: 0.0 s",
            font=ctk.CTkFont(size=12), text_color=config.COLOR_TEXT_MUTED,
        )
        info_label.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 12))

        frame.info_label = info_label
        return frame, video_label

    def _build_dashboard_table(self, parent):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background=config.COLOR_CARD,
            fieldbackground=config.COLOR_CARD,
            foreground=config.COLOR_TEXT_LIGHT,
            rowheight=38,
            borderwidth=0,
            font=("Segoe UI", 13),
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#1f2937",
            foreground=config.COLOR_TEXT_LIGHT,
            font=("Segoe UI", 13, "bold"),
            borderwidth=0,
        )
        style.map("Custom.Treeview", background=[("selected", config.COLOR_ACCENT)])

        columns = ("id", "patente", "camara", "fecha", "hora", "estado", "accion")
        self.tree = ttk.Treeview(
            parent, columns=columns, show="headings", style="Custom.Treeview", height=14,
        )
        headers = {
            "id": "ID", "patente": "Patente", "camara": "Cámara", "fecha": "Fecha", "hora": "Hora",
            "estado": "Estado", "accion": "Acción",
        }
        widths = {"id": 70, "patente": 160, "camara": 120, "fecha": 120, "hora": 100, "estado": 220, "accion": 260}
        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.tag_configure("ok", background=config.COLOR_OK_ROW)
        self.tree.tag_configure("over", background=config.COLOR_BAD_ROW)

        self.tree.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 20))

    # ------------------------------------------------------------------ #
    # Videos: autodetección / carga manual
    # ------------------------------------------------------------------ #
    def _autodetect_videos(self):
        cam1_path = find_default_video("camera1")
        cam2_path = find_default_video("camera2")
        self.video_paths["Cámara 1"] = cam1_path
        self.video_paths["Cámara 2"] = cam2_path
        self._refresh_video_status_label()

    def _refresh_video_status_label(self):
        lines = []
        for cam, path in self.video_paths.items():
            if path:
                lines.append(f"{cam}: {os.path.basename(path)} ✓")
            else:
                lines.append(f"{cam}: no encontrado ✗")
        self.video_status_label.configure(text="\n".join(lines))

    def load_videos_manually(self):
        for cam_label in ("Cámara 1", "Cámara 2"):
            path = filedialog.askopenfilename(
                title=f"Selecciona el video o imagen para {cam_label}",
                filetypes=[
                    ("Videos e imágenes", "*.mp4 *.avi *.mov *.mkv *.jpg *.jpeg *.png *.bmp"),
                    ("Videos", "*.mp4 *.avi *.mov *.mkv"),
                    ("Imágenes", "*.jpg *.jpeg *.png *.bmp"),
                ],
            )
            if path:
                self.video_paths[cam_label] = path
                if cam_label in self.workers:
                    self.workers[cam_label].change_video(path)
        self._refresh_video_status_label()

    # ------------------------------------------------------------------ #
    # Control de simulación
    # ------------------------------------------------------------------ #
    def start_simulation(self):
        if self.is_running:
            return

        missing = [cam for cam, path in self.video_paths.items() if not path]
        if missing:
            CTkMessagebox(
                title="Faltan fuentes",
                message=f"No hay video ni imagen cargado para: {', '.join(missing)}. "
                        f"Usa 'Cargar Videos/Imágenes' para seleccionarlos manualmente.",
                icon="warning",
            )
            return

        self.start_button.configure(state="disabled", text="Cargando modelo...")
        threading.Thread(target=self._init_and_start, daemon=True).start()

    def _init_and_start(self):
        try:
            if self.detector is None:
                self.detector = PlateDetector(use_gpu=False)

            self.workers = {
                "Cámara 1": CameraWorker("Cámara 1", self.video_paths["Cámara 1"], self.detector),
                "Cámara 2": CameraWorker("Cámara 2", self.video_paths["Cámara 2"], self.detector),
            }
            for worker in self.workers.values():
                worker.start()

            self.is_running = True
            self.after(0, self._on_simulation_started)
        except Exception as exc:
            self.after(0, lambda: self._on_start_error(str(exc)))

    def _on_simulation_started(self):
        self.start_button.configure(state="disabled", text="▶  Iniciar Prueba")
        self.stop_button.configure(state="normal")
        self.status_dot_label.configure(text="● Activo", text_color=config.COLOR_ACTIVE)

    def _on_start_error(self, message):
        self.start_button.configure(state="normal", text="▶  Iniciar Prueba")
        CTkMessagebox(title="Error al iniciar", message=message, icon="cancel")

    def stop_simulation(self):
        if not self.is_running:
            return
        for worker in self.workers.values():
            worker.stop()
        self.workers = {}
        self.is_running = False

        self.start_button.configure(state="normal", text="▶  Iniciar Prueba")
        self.stop_button.configure(state="disabled")
        self.status_dot_label.configure(text="● Inactivo", text_color=config.COLOR_INACTIVE)
        self.plate_cam1_label.configure(text="Cámara 1 · Patente: —")
        self.plate_cam2_label.configure(text="Cámara 2 · Patente: —")

        placeholder1 = _make_placeholder_ctkimage(config.VIDEO_DISPLAY_WIDTH, config.VIDEO_DISPLAY_HEIGHT)
        placeholder2 = _make_placeholder_ctkimage(config.VIDEO_DISPLAY_WIDTH, config.VIDEO_DISPLAY_HEIGHT)
        self.cam1_video_label.configure(image=placeholder1, text="")
        self.cam1_video_label.image = placeholder1
        self.cam2_video_label.configure(image=placeholder2, text="")
        self.cam2_video_label.image = placeholder2

        self.cam1_frame.info_label.configure(text="Patente: — · Tiempo: 0.0 s")
        self.cam2_frame.info_label.configure(text="Patente: — · Tiempo: 0.0 s")

    def clear_records(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.next_id = 1
        self._save_records_to_disk()

    # ------------------------------------------------------------------ #
    # Polling de frames y eventos desde los hilos de cámara
    # ------------------------------------------------------------------ #
    def _poll_workers(self):
        if self.is_running:
            self._update_camera_panel("Cámara 1", self.cam1_video_label, self.cam1_frame, self.plate_cam1_label)
            self._update_camera_panel("Cámara 2", self.cam2_video_label, self.cam2_frame, self.plate_cam2_label)
            self._drain_events()

        self.after(30, self._poll_workers)

    def _update_camera_panel(self, cam_label, video_label, frame_widget, status_label):
        worker = self.workers.get(cam_label)
        if worker is None:
            return

        try:
            frame = worker.frame_queue.get_nowait()
        except queue.Empty:
            frame = None

        if frame is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb_frame)
            ctk_img = ctk.CTkImage(
                light_image=img, dark_image=img,
                size=(config.VIDEO_DISPLAY_WIDTH, config.VIDEO_DISPLAY_HEIGHT),
            )
            video_label.configure(image=ctk_img, text="")
            video_label.image = ctk_img

        plate_text = worker.current_plate or "—"
        elapsed_text = f"{worker.current_elapsed:.1f} s" if worker.current_plate else "0.0 s"
        frame_widget.info_label.configure(text=f"Patente: {plate_text} · Tiempo: {elapsed_text}")
        status_label.configure(text=f"{cam_label} · Patente: {plate_text}")

    def _drain_events(self):
        for cam_label, worker in self.workers.items():
            while True:
                try:
                    event = worker.event_queue.get_nowait()
                except queue.Empty:
                    break
                self._add_dashboard_row(event)

    def _add_dashboard_row(self, event):
        now = datetime.now()

        fecha = now.strftime("%d-%m-%Y")
        hora = now.strftime("%H:%M:%S")

        tag = "over" if event.state == config.STATE_OVER else "ok"
        self.tree.insert(
            "", "end",
            values=(self.next_id, event.plate, event.camera_label, fecha, hora, event.state, event.action),
            tags=(tag,),
        )
        self.next_id += 1
        self._save_records_to_disk()

    # ------------------------------------------------------------------ #
    # Persistencia de registros (JSON)
    # ------------------------------------------------------------------ #
    def _load_records_from_disk(self):
        """Carga registros previamente guardados y los muestra en el dashboard."""
        if not os.path.isfile(config.RECORDS_FILE):
            return
        try:
            with open(config.RECORDS_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        max_id = 0
        for rec in records:
            tag = "over" if rec.get("estado") == config.STATE_OVER else "ok"
            self.tree.insert(
                "", "end",
                values=(rec.get("id"), rec.get("patente"), rec.get("camara"), rec.get("fecha"), rec.get("hora"),
                         rec.get("estado"), rec.get("accion")),
                tags=(tag,),
            )
            try:
                max_id = max(max_id, int(rec.get("id", 0)))
            except (TypeError, ValueError):
                pass
        self.next_id = max_id + 1

    def _save_records_to_disk(self):
        """Vuelca el contenido actual del dashboard a un archivo JSON en disco."""
        records = []
        for row_id in self.tree.get_children():
            values = self.tree.item(row_id, "values")
            records.append({
                "id": values[0], "patente": values[1], "fecha": values[3],
                "hora": values[4], "estado": values[5], "accion": values[6],
            })
        try:
            with open(config.RECORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def on_close(self):
        if self.is_running:
            self.stop_simulation()
        self.destroy()
