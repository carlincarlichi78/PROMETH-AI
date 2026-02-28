"""Diccionario PGC 2007 — nombres y clasificación de subcuentas.

RD 1514/2007 — Plan General de Contabilidad español.
Las subcuentas en BD son de 10 dígitos, ej: 7000000000 (Ventas de mercaderías).
"""

from typing import TypedDict


class InfoCuenta(TypedDict):
    nombre: str
    grupo: str
    naturaleza: str        # activo_corriente|activo_no_corriente|pasivo_corriente|pasivo_no_corriente|patrimonio|ingreso|gasto
    linea_pyg: str | None  # L1|L4|L6|L7|L8|L12|L13|L17|None


GRUPOS: dict[str, dict] = {
    "1": {"nombre": "Financiación básica", "naturaleza": "patrimonio"},
    "2": {"nombre": "Activo no corriente", "naturaleza": "activo_no_corriente"},
    "3": {"nombre": "Existencias", "naturaleza": "activo_corriente"},
    "4": {"nombre": "Acreedores y deudores", "naturaleza": "activo_corriente"},  # bilateral — se refina por subcuenta
    "5": {"nombre": "Cuentas financieras", "naturaleza": "activo_corriente"},
    "6": {"nombre": "Compras y gastos", "naturaleza": "gasto"},
    "7": {"nombre": "Ventas e ingresos", "naturaleza": "ingreso"},
    "8": {"nombre": "Gastos imputados a PN", "naturaleza": "gasto"},
    "9": {"nombre": "Ingresos imputados a PN", "naturaleza": "ingreso"},
}

# Mapa prefijo → (nombre, naturaleza, linea_pyg)
# Se aplica de más específico (más dígitos) a más genérico
_PREFIJOS: list[tuple[str, str, str, str | None]] = [
    # (prefijo, nombre, naturaleza, linea_pyg)
    # GRUPO 1 — Financiación básica
    ("100", "Capital social", "patrimonio", None),
    ("112", "Reserva legal", "patrimonio", None),
    ("113", "Reservas voluntarias", "patrimonio", None),
    ("129", "Resultado del ejercicio", "patrimonio", None),
    ("173", "Proveedores de inmovilizado a LP", "pasivo_no_corriente", None),
    # GRUPO 2 — Activo no corriente
    ("210", "Terrenos y bienes naturales", "activo_no_corriente", None),
    ("211", "Construcciones", "activo_no_corriente", None),
    ("213", "Maquinaria", "activo_no_corriente", None),
    ("216", "Mobiliario", "activo_no_corriente", None),
    ("217", "Equipos para proceso información", "activo_no_corriente", None),
    ("218", "Elementos de transporte", "activo_no_corriente", None),
    ("280", "Amortización acumulada inmovilizado intangible", "activo_no_corriente", None),
    ("281", "Amortización acumulada inmovilizado material", "activo_no_corriente", None),
    # GRUPO 3 — Existencias
    ("300", "Mercaderías A", "activo_corriente", None),
    ("301", "Mercaderías B", "activo_corriente", None),
    ("302", "Mercaderías", "activo_corriente", None),
    # GRUPO 4 — Acreedores y deudores
    ("400", "Proveedores", "pasivo_corriente", None),
    ("401", "Proveedores, efectos comerciales a pagar", "pasivo_corriente", None),
    ("410", "Acreedores por prestaciones de servicios", "pasivo_corriente", None),
    ("430", "Clientes", "activo_corriente", None),
    ("431", "Clientes, efectos comerciales a cobrar", "activo_corriente", None),
    ("440", "Deudores", "activo_corriente", None),
    ("460", "Anticipos de remuneraciones", "activo_corriente", None),
    ("465", "Remuneraciones pendientes de pago", "pasivo_corriente", None),
    ("470", "HP deudora por IVA", "activo_corriente", None),
    ("4700", "HP deudora por retenciones", "activo_corriente", None),
    ("4709", "HP deudora por devolución impuestos", "activo_corriente", None),
    ("472", "HP IVA soportado", "activo_corriente", None),
    ("473", "HP retenciones y pagos a cuenta", "activo_corriente", None),
    ("474", "Activos por diferencias temporarias", "activo_no_corriente", None),
    ("475", "HP acreedora por IVA", "pasivo_corriente", None),
    ("4751", "HP acreedora por retenciones practicadas", "pasivo_corriente", None),
    ("476", "Organismos SS acreedores", "pasivo_corriente", None),
    ("477", "HP IVA repercutido", "pasivo_corriente", None),
    ("480", "Gastos anticipados", "activo_corriente", None),
    ("485", "Ingresos anticipados", "pasivo_corriente", None),
    # GRUPO 5 — Cuentas financieras
    ("500", "Obligaciones a corto plazo", "pasivo_corriente", None),
    ("520", "Deudas a corto plazo con entidades de crédito", "pasivo_corriente", None),
    ("521", "Deudas a corto plazo", "pasivo_corriente", None),
    ("570", "Caja, euros", "activo_corriente", None),
    ("572", "Bancos e instituciones de crédito", "activo_corriente", None),
    ("580", "Inversiones financieras a corto plazo", "activo_corriente", None),
    # GRUPO 6 — Compras y gastos
    ("600", "Compras de mercaderías", "gasto", "L4"),
    ("601", "Compras de materias primas", "gasto", "L4"),
    ("602", "Compras de otros aprovisionamientos", "gasto", "L4"),
    ("606", "Descuentos sobre compras", "gasto", "L4"),
    ("607", "Trabajos realizados por otras empresas", "gasto", "L4"),
    ("610", "Variación de existencias de mercaderías", "gasto", "L4"),
    ("621", "Arrendamientos y cánones", "gasto", "L7"),
    ("622", "Reparaciones y conservación", "gasto", "L7"),
    ("623", "Servicios de profesionales independientes", "gasto", "L7"),
    ("624", "Transportes", "gasto", "L7"),
    ("625", "Primas de seguros", "gasto", "L7"),
    ("626", "Servicios bancarios y similares", "gasto", "L7"),
    ("627", "Publicidad, propaganda y relaciones públicas", "gasto", "L7"),
    ("628", "Suministros", "gasto", "L7"),
    ("629", "Otros servicios", "gasto", "L7"),
    ("630", "Impuesto sobre beneficios", "gasto", "L17"),
    ("631", "Otros tributos", "gasto", "L7"),
    ("640", "Sueldos y salarios", "gasto", "L6"),
    ("642", "Seguridad social a cargo de la empresa", "gasto", "L6"),
    ("649", "Otros gastos sociales", "gasto", "L6"),
    ("650", "Pérdidas de créditos comerciales", "gasto", "L7"),
    ("660", "Gastos financieros por deudas con entidades", "gasto", "L13"),
    ("662", "Intereses de deudas", "gasto", "L13"),
    ("665", "Descuentos sobre ventas por pronto pago", "gasto", "L13"),
    ("668", "Diferencias negativas de cambio", "gasto", "L13"),
    ("671", "Pérdidas procedentes del inmovilizado", "gasto", "L7"),
    ("681", "Amortización del inmovilizado intangible", "gasto", "L8"),
    ("6810", "Amortización del inmovilizado material", "gasto", "L8"),
    ("690", "Pérdidas por deterioro existencias", "gasto", "L7"),
    ("694", "Pérdidas por deterioro créditos", "gasto", "L7"),
    # GRUPO 7 — Ventas e ingresos
    ("700", "Ventas de mercaderías", "ingreso", "L1"),
    ("701", "Ventas de productos terminados", "ingreso", "L1"),
    ("702", "Ventas de productos semiterminados", "ingreso", "L1"),
    ("705", "Prestaciones de servicios", "ingreso", "L1"),
    ("706", "Descuentos sobre ventas", "ingreso", "L1"),
    ("708", "Devoluciones de ventas", "ingreso", "L1"),
    ("740", "Subvenciones a la explotación", "ingreso", "L1"),
    ("751", "Resultados de operaciones en común", "ingreso", "L1"),
    ("760", "Ingresos de participaciones en capital", "ingreso", "L12"),
    ("762", "Ingresos de créditos", "ingreso", "L12"),
    ("769", "Otros ingresos financieros", "ingreso", "L12"),
    ("771", "Beneficios procedentes del inmovilizado", "ingreso", "L12"),
]

# Construir índice ordenado por longitud de prefijo DESC (más específico primero)
_INDICE: list[tuple[str, str, str, str | None]] = sorted(
    _PREFIJOS, key=lambda x: len(x[0]), reverse=True
)


def obtener_nombre(subcuenta: str) -> str:
    """Devuelve el nombre legible de una subcuenta por prefijo. Fallback: código original."""
    codigo = str(subcuenta).strip()
    for prefijo, nombre, _, _ in _INDICE:
        if codigo.startswith(prefijo):
            return nombre
    # Fallback: nombre del grupo (solo grupos 1-7; grupos 8-9 son de ajuste PN, rara vez usados)
    if codigo and codigo[0] in GRUPOS and codigo[0] not in ("8", "9"):
        return GRUPOS[codigo[0]]["nombre"]
    return codigo


def clasificar(subcuenta: str) -> InfoCuenta:
    """Clasifica una subcuenta: nombre, grupo, naturaleza, línea PyG."""
    codigo = str(subcuenta).strip()
    for prefijo, nombre, naturaleza, linea_pyg in _INDICE:
        if codigo.startswith(prefijo):
            grupo = codigo[0] if codigo else "?"
            return InfoCuenta(
                nombre=nombre,
                grupo=grupo,
                naturaleza=naturaleza,
                linea_pyg=linea_pyg,
            )
    # Fallback al grupo
    grupo = codigo[0] if codigo else "?"
    if grupo in GRUPOS:
        g = GRUPOS[grupo]
        return InfoCuenta(nombre=g["nombre"], grupo=grupo, naturaleza=g["naturaleza"], linea_pyg=None)
    return InfoCuenta(nombre=codigo, grupo="?", naturaleza="gasto", linea_pyg=None)
