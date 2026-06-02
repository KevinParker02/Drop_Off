import json
import os
from datetime import datetime

FILE = "infractions.json"


def save_infraction(plate):

    # nueva infracción
    infraction = {
        "plate": plate,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # cargar datos existentes
    if os.path.exists(FILE):
        try:
            with open(FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = []
    else:
        data = []

    # agregar nueva
    data.append(infraction)

    # guardar todo
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)