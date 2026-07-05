"""
Lógica de negocio: determina cuánto tiempo permanece detenida una patente
detectada en una cámara y decide si corresponde sanción.

Cada cámara tiene su propia instancia de PlateTracker.
"""
import time
from dataclasses import dataclass, field

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

    def on_plate_detected(self, plate: str) -> DashboardEvent | None:
        """Se llama cada vez que el OCR entrega una patente válida en el frame actual."""
        now = time.time()
        event = None

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
        """
        now = time.time()
        events = []
        departed_plates = []

        for plate, vehicle in self.active_vehicles.items():
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
        vehicle = self.active_vehicles.get(plate)
        if not vehicle:
            return 0.0
        return time.time() - vehicle.start_time

    def reset(self):
        self.active_vehicles.clear()
