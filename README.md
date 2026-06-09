# 🚗 Drop_Off

**Drop_Off** es una solución tecnológica desarrollada para el colegio **"Genios Traviesos"**, orientada al monitoreo y control de la zona de descenso de estudiantes. El sistema utiliza visión computacional y reconocimiento óptico de caracteres (OCR) para identificar vehículos, medir tiempos de permanencia y detectar infracciones cuando se supera el límite permitido de 4 minutos.

El objetivo principal es optimizar el flujo vehicular, reducir la congestión y proporcionar una herramienta de apoyo para la administración del establecimiento mediante el registro y seguimiento automatizado de infracciones.

---

## 👥 Equipo de Trabajo

* 👩‍💻 **Yasna Villarroel** – Responsable de planificación, gestión de tareas, diseño de interfaces, experiencia de usuario (UI/UX) y desarrollo Frontend.
* 👨‍💻 **Sebastián Carrera** – Desarrollo Backend, integración de componentes y gestión de datos.
* 👨‍💻 **Kevin Vivanco** – Desarrollo Backend, integración de componentes y gestión de datos.

---

## 🧩 Componentes del Sistema

| Módulo                           | Descripción                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------- |
| 🎥 **Captura de Video**          | Obtención de imágenes en tiempo real desde cámaras IP o cámaras conectadas al equipo. |
| 🔍 **Reconocimiento OCR**        | Identificación automática de patentes mediante EasyOCR y procesamiento de imágenes.   |
| ⏱️ **Control de Permanencia**    | Registro y cálculo del tiempo de permanencia de cada vehículo en la zona Drop Off.    |
| 🚨 **Detección de Infracciones** | Generación de alertas cuando un vehículo supera el tiempo máximo permitido.           |
| 🖥️ **Interfaz Administrativa**  | Visualización de eventos, infracciones y monitoreo mediante CustomTkinter.            |
| 📊 **Reportes y Registros**      | Almacenamiento y consulta de información histórica para análisis y seguimiento.       |

---

## ⚙️ Tecnologías Utilizadas

### 🖥️ Aplicación Principal

* **Python 3**
* **CustomTkinter**
* **CTkMessagebox**

### 🎥 Procesamiento de Imágenes

* **OpenCV**
* **NumPy**
* **Pillow**
* **Scikit-Image**
* **SciPy**
* **Shapely**

### 🔤 Reconocimiento de Texto (OCR)

* **EasyOCR**
* **PyTorch**
* **Pyclipper**
* **Python-Bidi**

### ⚙️ Configuración y Utilidades

* **PyYAML**

---

## 🧪 Entorno de Desarrollo

* Desarrollo local mediante entornos virtuales de Python.
* Procesamiento de imágenes en tiempo real utilizando OpenCV.
* Reconocimiento de patentes mediante EasyOCR.
* Interfaz gráfica desarrollada con CustomTkinter.
* Soporte para ejecución utilizando CPU o GPU NVIDIA compatible con CUDA.
* Arquitectura modular para facilitar futuras ampliaciones y mantenimiento.

---

## 📌 Funcionalidades Clave

* Captura de imágenes y video en tiempo real.
* Detección automática de vehículos.
* Reconocimiento de patentes mediante OCR.
* Registro de ingreso y salida de vehículos.
* Medición automática del tiempo de permanencia.
* Detección de infracciones por exceder los 4 minutos permitidos.
* Registro histórico de eventos e infracciones.
* Visualización de información mediante interfaz gráfica.
* Generación de alertas para administración.
* Preparado para futuras integraciones con sistemas de notificación.

---

## 🚀 Instalación y Ejecución

1. Crear un entorno virtual (python -m venv venv)
2. Activa el entorno virtual (venv\Scripts\activate)
3. Instalas los requerimiento (pip install -r requirements.txt)
3.1 Instalar PyTorch según la GPU disponible:
    a.NVIDIA CUDA:
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
    b.CPU:
        pip install torch torchvision

4. Corres el programa con (python app.py)

## 📦 Dependencias Principales

```txt
easyocr==1.7.2
opencv-python==4.13.0.92
numpy==2.4.6
pillow==12.2.0
pyclipper==1.4.0
python-bidi==0.6.10
PyYAML==6.0.3
scikit-image==0.26.0
scipy==1.17.1
shapely==2.1.2
customtkinter==5.2.2
CTkMessagebox==2.7
```
