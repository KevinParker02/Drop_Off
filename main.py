"""
Punto de entrada del sistema Drop-Off - Genios Traviesos.
Ejecutar con: python main.py
"""
from app import App

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
