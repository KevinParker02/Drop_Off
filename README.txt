Coloca aquí la fuente de cada cámara simulada. Puede ser un VIDEO o una
IMAGEN fija (por ejemplo, para probar rápidamente la lectura OCR sin
necesitar un video real):

  camera1.mp4  (o camera1.jpg / .png)   -> fuente para el panel "Cámara 1"
  camera2.mp4  (o camera2.jpg / .png)   -> fuente para el panel "Cámara 2"

Extensiones de video soportadas: .mp4, .avi, .mov, .mkv
Extensiones de imagen soportadas: .jpg, .jpeg, .png, .bmp

Si usas una imagen fija, el sistema la trata como una cámara que siempre
ve la misma escena: la patente detectada nunca "se retira" del cuadro,
por lo que eventualmente se marcará como "Pasado de tiempo" apenas se
cumpla el umbral de tiempo configurado (ideal para pruebas rápidas de
OCR y validación de patente, no para simular el flujo completo de
entrada/salida de un vehículo).

Si no se encuentra ninguna fuente con estos nombres al abrir la
aplicación, el sistema permitirá cargarla manualmente con el botón
"Cargar Videos/Imágenes".
