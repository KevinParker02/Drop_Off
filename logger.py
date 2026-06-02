import csv
import os
from datetime import datetime

def save_infraction(plate):

    file_exists = os.path.exists("infracciones.csv")

    with open(
        "infracciones.csv",
        "a",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "fecha",
                "hora",
                "patente"
            ])

        now = datetime.now()

        writer.writerow([
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            plate
        ])