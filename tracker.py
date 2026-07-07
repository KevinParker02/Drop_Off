"""
Lógica de negocio: determina cuánto tiempo permanece detenida una patente
detectada en una cámara y decide si corresponde sanción.

Cada cámara tiene su propia instancia de PlateTracker. Como el hilo de OCR
y el hilo de video acceden a esta clase de forma concurrente (el OCR corre
en su propio hilo para no congelar el video), todo acceso al diccionario
interno está protegido con un lock.
"""
import time
import threading
from dataclasses import dataclass

from config import TIME_THRESHOLD_SECONDS, GRACE_PERIOD_SECONDS, STATE_OK, STATE_OVER, ACTION_NONE, ACTION_FINE


@dataclass
class ActiveVehicle:
    plate: str
    start_time: float
    last_seen: float
    logged_over_time: bool = False


@dataclass
class DashboardEvent:
    plate: str
    state: str
    action: str
    camera_label: str


class PlateTracker:
    """
    Mantiene el estado de los vehículos actualmente detenidos frente a una cámara
    y genera eventos para el dashboard cuando corresponde.
    """

    def __init__(self, camera_label: str):
        self.camera_label = camera_label
        self.active_vehicles: dict[str, ActiveVehicle] = {}
        self._lock = threading.Lock()

    def on_plate_detected(self, plate: str) -> DashboardEvent | None:
        """Se llama cada vez que el OCR entrega una patente válida (desde el hilo de OCR)."""
        now = time.time()
        event = None

        with self._lock:
            if plate not in self.active_vehicles:
                self.active_vehicles[plate] = ActiveVehicle(plate=plate, start_time=now, last_seen=now)
            else:
                vehicle = self.active_vehicles[plate]
                vehicle.last_seen = now
                duration = now - vehicle.start_time

                if duration >= TIME_THRESHOLD_SECONDS and not vehicle.logged_over_time:
                    vehicle.logged_over_time = True
                    event = DashboardEvent(
                        plate=plate,
                        state=STATE_OVER,
                        action=ACTION_FINE,
                        camera_label=self.camera_label,
                    )

        return event

    def check_departures(self) -> list[DashboardEvent]:
        """
        Revisa si algún vehículo activo dejó de verse por más del período de gracia,
        lo que se interpreta como que el vehículo se retiró. Genera el evento de
        'Rango aceptable' para los que nunca cruzaron el umbral de 5 segundos.

        El período de gracia debe ser más largo que el tiempo real que tarda el
        OCR en volver a leer la MISMA patente (en CPU, EasyOCR puede tardar más
        de 1 segundo por lectura). Si el período de gracia es muy corto, un
        vehículo que sigue ahí se marca como "retirado" entre una lectura y la
        siguiente, y se vuelve a registrar como si fuera un vehículo nuevo cada
        vez que el OCR lo vuelve a leer.
        """
        now = time.time()
        events = []
        departed_plates = []

        with self._lock:
            for plate, vehicle in list(self.active_vehicles.items()):
                if now - vehicle.last_seen > GRACE_PERIOD_SECONDS:
                    departed_plates.append(plate)
                    if not vehicle.logged_over_time:
                        events.append(
                            DashboardEvent(
                                plate=plate,
                                state=STATE_OK,
                                action=ACTION_NONE,
                                camera_label=self.camera_label,
                            )
                        )

            for plate in departed_plates:
                del self.active_vehicles[plate]

        return events

    def get_elapsed_for_plate(self, plate: str) -> float:
        with self._lock:
            vehicle = self.active_vehicles.get(plate)
            if not vehicle:
                return 0.0
            return time.time() - vehicle.start_time

    def reset(self):
        with self._lock:
            self.active_vehicles.clear()
