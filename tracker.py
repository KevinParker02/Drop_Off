import time

class VehicleTracker:

    def __init__(self):
        self.current_plate = None
        self.first_seen = None

    def update(self, plate):

        now = time.time()

        if self.current_plate != plate:

            self.current_plate = plate
            self.first_seen = now

        return now - self.first_seen

    def reset(self):

        self.current_plate = None
        self.first_seen = None