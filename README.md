# Drop_Off

Para ejecutar esta basura debes

1. Crear un entorno virtual (python -m venv venv)
2. Activa el entorno virtual (venv\Scripts\activate)
3. Instalas los requerimiento (pip install -r requirements.txt)
3.1 Instalar PyTorch según la GPU disponible:
    a.NVIDIA CUDA:
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
    b.CPU:
        pip install torch torchvision

4. Corres el programa con (python app.py)