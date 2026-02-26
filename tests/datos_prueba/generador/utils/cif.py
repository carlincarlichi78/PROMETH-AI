"""
Modulo para generar y validar CIF/NIF espanoles realistas.
Usado en el generador de datos de prueba contable.
"""

import random
import string

# Tabla de letras de control para NIF/NIE
_LETRAS_NIF = "TRWAGMYFPDXBNJZSQVHLCKE"

# Provincias espanolas validas (01-52, sin 00, 43 no existe pero se incluye por simplificacion)
_PROVINCIAS = [f"{i:02d}" for i in range(1, 53) if i not in (0,)]

# Tipos de CIF validos
_TIPOS_CIF = "ABCDEFGHJNPQRSUVW"

# Tipos donde el control es letra
_CONTROL_LETRA = set("KPQS")
# Tipos donde el control es numero
_CONTROL_NUMERO = set("ABEH")
# Resto: puede ser numero o letra (usamos numero por simplicidad)


def _calcular_control_cif(digitos: str) -> int:
    """
    Calcula el digito de control del CIF a partir de los 7 digitos internos.

    Algoritmo:
    - Pares (posiciones 2, 4, 6): sumar directamente
    - Impares (posiciones 1, 3, 5, 7): multiplicar x2, si resultado >= 10 sumar sus digitos
    - Control = (10 - (suma % 10)) % 10
    """
    suma_pares = 0
    suma_impares = 0

    for i, d in enumerate(digitos):
        n = int(d)
        if (i + 1) % 2 == 0:
            # Posicion par (indice impar): sumar directo
            suma_pares += n
        else:
            # Posicion impar (indice par): multiplicar x2 y sumar digitos
            doble = n * 2
            suma_impares += doble // 10 + doble % 10

    total = suma_pares + suma_impares
    return (10 - total % 10) % 10


def generar_cif(tipo: str = "B", provincia: str = None) -> str:
    """
    Genera un CIF valido para sociedades espanolas.

    Formato: tipo(1) + provincia(2) + inscripcion(5) + control(1)

    Args:
        tipo: Letra del tipo de entidad (A=SA, B=SL, C=Soc.Colectiva, etc.)
        provincia: Codigo de provincia (01-52). Si None, se elige aleatoriamente.

    Returns:
        CIF valido como cadena de 9 caracteres.
    """
    tipo = tipo.upper()
    if tipo not in _TIPOS_CIF:
        tipo = "B"

    if provincia is None:
        provincia = random.choice(_PROVINCIAS)

    # 5 digitos de inscripcion (rellenar con ceros a la izquierda)
    inscripcion = f"{random.randint(1, 99999):05d}"

    # Los 7 digitos sobre los que se calcula el control
    digitos = provincia + inscripcion

    control_num = _calcular_control_cif(digitos)

    # Determinar si el control es letra o numero segun el tipo
    letras_control = "JABCDEFGHI"  # 0->J, 1->A, 2->B, ..., 9->I
    if tipo in _CONTROL_LETRA:
        control = letras_control[control_num]
    elif tipo in _CONTROL_NUMERO:
        control = str(control_num)
    else:
        # Resto: usamos numero
        control = str(control_num)

    return tipo + digitos + control


def validar_cif(cif: str) -> bool:
    """
    Valida un CIF espanol.

    Args:
        cif: CIF a validar (9 caracteres).

    Returns:
        True si el CIF es valido, False en caso contrario.
    """
    if not cif or len(cif) != 9:
        return False

    tipo = cif[0].upper()
    if tipo not in _TIPOS_CIF:
        return False

    digitos = cif[1:8]
    control_recibido = cif[8].upper()

    if not digitos.isdigit():
        return False

    control_num = _calcular_control_cif(digitos)
    letras_control = "JABCDEFGHI"

    if tipo in _CONTROL_LETRA:
        return control_recibido == letras_control[control_num]
    elif tipo in _CONTROL_NUMERO:
        return control_recibido == str(control_num)
    else:
        # Resto: aceptar tanto numero como letra equivalente
        return control_recibido == str(control_num) or control_recibido == letras_control[control_num]


def generar_nif(seed_num: int = None) -> str:
    """
    Genera un NIF valido (DNI espanol con letra de control).

    Formato: 8 digitos + letra de control.
    La letra se calcula como: _LETRAS_NIF[numero % 23]

    Args:
        seed_num: Numero base (1-99999999). Si None, se genera aleatoriamente.

    Returns:
        NIF valido como cadena de 9 caracteres.
    """
    if seed_num is None:
        # Evitar numeros especiales reservados (00000000, 00000001, etc.)
        num = random.randint(10000000, 99999999)
    else:
        num = seed_num % 100000000

    letra = _LETRAS_NIF[num % 23]
    return f"{num:08d}{letra}"


def validar_nif(nif: str) -> bool:
    """
    Valida un NIF espanol.

    Args:
        nif: NIF a validar (9 caracteres: 8 digitos + letra).

    Returns:
        True si el NIF es valido, False en caso contrario.
    """
    if not nif or len(nif) != 9:
        return False

    parte_num = nif[:8]
    letra = nif[8].upper()

    if not parte_num.isdigit():
        return False

    num = int(parte_num)
    letra_esperada = _LETRAS_NIF[num % 23]
    return letra == letra_esperada


def generar_nie(tipo: str = "X") -> str:
    """
    Genera un NIE valido (Numero de Identidad de Extranjero).

    Formato: prefijo(1) + 7 digitos + letra de control.
    Prefijos: X=0, Y=1, Z=2 (para el calculo de la letra).

    Args:
        tipo: Prefijo del NIE ("X", "Y" o "Z").

    Returns:
        NIE valido como cadena de 9 caracteres.
    """
    tipo = tipo.upper()
    prefijos = {"X": 0, "Y": 1, "Z": 2}
    if tipo not in prefijos:
        tipo = "X"

    prefijo_num = prefijos[tipo]
    digitos = random.randint(0, 9999999)

    # El numero completo para calcular la letra combina prefijo y digitos
    num_completo = int(f"{prefijo_num}{digitos:07d}")
    letra = _LETRAS_NIF[num_completo % 23]

    return f"{tipo}{digitos:07d}{letra}"


def generar_vat_eu(pais: str) -> str:
    """
    Genera un numero VAT europeo ficticio con formato correcto.

    Paises soportados y formatos:
    - IRL: IE + 7 digitos + letra
    - DEU: DE + 9 digitos
    - FRA: FR + 2 letras + 9 digitos
    - ITA: IT + 11 digitos
    - PRT: PT + 9 digitos
    - SWE: SE + 10 digitos + "01"

    Args:
        pais: Codigo de pais en formato ISO 3166-1 alpha-3 (IRL, DEU, FRA, ITA, PRT, SWE).

    Returns:
        VAT europeo ficticio como cadena.

    Raises:
        ValueError: Si el pais no esta soportado.
    """
    pais = pais.upper()

    if pais == "IRL":
        # IE + 7 digitos + letra
        digitos = f"{random.randint(1000000, 9999999)}"
        letra = random.choice(string.ascii_uppercase)
        return f"IE{digitos}{letra}"

    elif pais == "DEU":
        # DE + 9 digitos
        digitos = f"{random.randint(100000000, 999999999)}"
        return f"DE{digitos}"

    elif pais == "FRA":
        # FR + 2 letras + 9 digitos
        letras = random.choice(string.ascii_uppercase) + random.choice(string.ascii_uppercase)
        digitos = f"{random.randint(100000000, 999999999)}"
        return f"FR{letras}{digitos}"

    elif pais == "ITA":
        # IT + 11 digitos
        digitos = f"{random.randint(10000000000, 99999999999)}"
        return f"IT{digitos}"

    elif pais == "PRT":
        # PT + 9 digitos
        digitos = f"{random.randint(100000000, 999999999)}"
        return f"PT{digitos}"

    elif pais == "SWE":
        # SE + 10 digitos + "01"
        digitos = f"{random.randint(1000000000, 9999999999)}"
        return f"SE{digitos}01"

    else:
        raise ValueError(f"Pais no soportado: {pais}. Usar IRL, DEU, FRA, ITA, PRT o SWE.")


def generar_cif_invalido(cif_valido: str) -> str:
    """
    Corrompe el ultimo caracter de un CIF valido para generar un CIF invalido.
    Usado para generar casos de error E01 (identificador fiscal incorrecto).

    Args:
        cif_valido: CIF valido de 9 caracteres.

    Returns:
        CIF con el caracter de control modificado (invalido).
    """
    if not cif_valido or len(cif_valido) < 2:
        return cif_valido

    control_actual = cif_valido[-1]

    # Intentar cambiar el control por un caracter diferente
    if control_actual.isdigit():
        # Incrementar el digito (con wraparound)
        nuevo_control = str((int(control_actual) + 1) % 10)
    else:
        # Cambiar la letra por la siguiente en el alfabeto (con wraparound)
        idx = string.ascii_uppercase.index(control_actual.upper())
        nuevo_control = string.ascii_uppercase[(idx + 1) % 26]

    return cif_valido[:-1] + nuevo_control
