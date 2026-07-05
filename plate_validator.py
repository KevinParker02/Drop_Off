"""
Validación y normalización de patentes chilenas.

Formatos aceptados:
  - Antiguo:  LLDDDD   (2 letras + 4 dígitos)   ej: AB1234
  - Nuevo:    LLLLDD   (4 letras + 2 dígitos)   ej: BXCV12

Cualquier texto leído por el OCR que no calce con alguno de estos dos
patrones es descartado y NO se registra en el dashboard.
"""
import re
from config import PLATE_REGEX_OLD, PLATE_REGEX_NEW

_OLD_RE = re.compile(PLATE_REGEX_OLD)
_NEW_RE = re.compile(PLATE_REGEX_NEW)

# Correcciones típicas de confusión del OCR sobre caracteres ambiguos.
# Solo se aplican como intento adicional si el texto crudo no calza.
_AMBIGUOUS_SUBS = {
    "O": "0", "Q": "0", "D": "0",
    "I": "1", "L": "1",
    "S": "5", "B": "8",
}


def normalize_raw_text(raw_text: str) -> str:
    """Limpia el texto crudo del OCR: quita espacios, guiones, puntos y pasa a mayúsculas."""
    if not raw_text:
        return ""
    cleaned = raw_text.upper()
    for ch in [" ", "-", ".", "_", "·", ":", "*"]:
        cleaned = cleaned.replace(ch, "")
    cleaned = re.sub(r"[^A-Z0-9]", "", cleaned)
    return cleaned


def is_valid_chilean_plate(text: str) -> bool:
    """Retorna True si el texto normalizado calza con un formato de patente chilena."""
    if not text:
        return False
    return bool(_OLD_RE.match(text)) or bool(_NEW_RE.match(text))


def _try_fix_digit_zone(text: str, letter_count: int) -> str:
    """
    Intenta corregir la zona numérica de la patente cuando el OCR confundió
    una letra con un dígito parecido (ej. 'O' por '0', 'I' por '1').
    letter_count: cuántos caracteres iniciales deberían ser letras.
    """
    if len(text) < letter_count:
        return text
    letters_part = text[:letter_count]
    digits_part = text[letter_count:]
    fixed_digits = "".join(_AMBIGUOUS_SUBS.get(ch, ch) for ch in digits_part)
    return letters_part + fixed_digits


def extract_valid_plate(raw_text: str) -> str | None:
    """
    Intenta obtener una patente chilena válida a partir de un texto crudo de OCR.
    Retorna la patente normalizada (ej: 'AB1234') o None si no se pudo validar.
    """
    candidate = normalize_raw_text(raw_text)

    if is_valid_chilean_plate(candidate):
        return candidate

    # Intento de corrección para formato antiguo (2 letras + 4 dígitos)
    if len(candidate) == 6:
        fixed_old = _try_fix_digit_zone(candidate, 2)
        if is_valid_chilean_plate(fixed_old):
            return fixed_old

        # Intento de corrección para formato nuevo (4 letras + 2 dígitos)
        fixed_new = _try_fix_digit_zone(candidate, 4)
        if is_valid_chilean_plate(fixed_new):
            return fixed_new

    return None
