"""
Cálculo de IBAN español a partir de datos R11 de Norma 43.

Referencias:
  - AEB Norma 43: banco(4)+oficina(4)+cuenta(10) — sin dígitos de control
  - BdE: Dígitos de Control CCC por Módulo 11 (potencias de 2 mod 11)
  - ISO 13616: Dígitos de control IBAN por Módulo 97
"""
from typing import Tuple

# Pesos Módulo 11: 2^n mod 11 para n = 0..9 → (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)
# Se aplican de derecha a izquierda sobre los dígitos.
_PESOS = (1, 2, 4, 8, 5, 10, 9, 7, 3, 6)


def _dc_mod11(digits: str, n: int) -> int:
    """
    Calcula un único dígito de control CCC por Módulo 11 AEB.

    Args:
        digits: cadena de dígitos (se rellena con 0s a la izquierda hasta n)
        n:      número de pesos a usar (9 para D1, 10 para D2)

    Casos especiales (sólo en cuentas inválidas):
        resultado = 11 → devuelve 0
        resultado = 10 → devuelve 1
    """
    pesos = _PESOS[:n]
    padded = digits.zfill(n)
    total = sum(int(d) * p for d, p in zip(reversed(padded), pesos))
    resultado = 11 - (total % 11)
    if resultado == 11:
        return 0
    if resultado == 10:
        return 1
    return resultado


def calcular_dc_ccc(entidad: str, oficina: str, cuenta: str) -> Tuple[int, int]:
    """
    Calcula los dos dígitos de control de una CCC española.

    D1 — calculado sobre '0' + entidad(4) + oficina(4) → 9 dígitos, 9 pesos
    D2 — calculado sobre cuenta(10) → 10 dígitos, 10 pesos

    Returns:
        (D1, D2) como enteros
    """
    d1 = _dc_mod11("0" + entidad + oficina, 9)
    d2 = _dc_mod11(cuenta, 10)
    return d1, d2


def construir_iban_es(entidad: str, oficina: str, cuenta: str) -> str:
    """
    Construye el IBAN español completo (24 caracteres) desde los 18 dígitos del R11.

    Proceso:
      1. Calcula D1, D2 (Módulo 11 AEB)
      2. Ensambla CCC de 20 dígitos: entidad+oficina+D1D2+cuenta
      3. Calcula dígitos de control IBAN (Módulo 97 ISO 13616):
           rearrangement → CCC + "ES00"
           convierte letras a números (E=14, S=28)
           check_digits = 98 − (número mod 97)
      4. Retorna "ES" + check_digits(2) + CCC(20)

    Args:
        entidad: 4 dígitos del código de entidad bancaria (ej: "2100")
        oficina: 4 dígitos de la oficina (ej: "3889")
        cuenta:  10 dígitos del número de cuenta (ej: "0200255608")

    Returns:
        IBAN sin espacios, 24 chars (ej: "ES54210038896902002556 08")

    Example:
        >>> construir_iban_es("2100", "3889", "0200255608")
        'ES54210038896902002556 08'   # DC=69, check_iban=54 (valores a validar)
    """
    entidad = entidad.zfill(4)
    oficina = oficina.zfill(4)
    cuenta  = cuenta.zfill(10)

    d1, d2 = calcular_dc_ccc(entidad, oficina, cuenta)
    dc  = f"{d1}{d2}"
    ccc = entidad + oficina + dc + cuenta   # 4+4+2+10 = 20 dígitos

    # ISO 13616 — rearrangement: CCC + código_país + "00"
    reordenado = ccc + "ES00"
    numerico = "".join(
        str(ord(c) - ord("A") + 10) if c.isalpha() else c
        for c in reordenado
    )
    check_iban = 98 - (int(numerico) % 97)

    return f"ES{check_iban:02d}{ccc}"
