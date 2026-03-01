"""Tests para clasificar_motivo_cuarentena y notificar_cuarentena."""


def test_motivo_ilegible_notifica_cliente():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("foto borrosa") == "cliente"
    assert clasificar_motivo_cuarentena("ilegible") == "cliente"
    assert clasificar_motivo_cuarentena("duplicado") == "cliente"
    assert clasificar_motivo_cuarentena("sin datos extraibles") == "cliente"


def test_motivo_contable_notifica_gestor():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("entidad desconocida") == "gestor"
    assert clasificar_motivo_cuarentena("fecha fuera del ejercicio") == "gestor"
    assert clasificar_motivo_cuarentena("importe negativo") == "gestor"
    assert clasificar_motivo_cuarentena("cif inválido") == "gestor"


def test_motivo_desconocido_notifica_gestor():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("error desconocido") == "gestor"
    assert clasificar_motivo_cuarentena("error raro") == "gestor"


def test_clasificar_case_insensitive():
    from sfce.core.notificaciones import clasificar_motivo_cuarentena
    assert clasificar_motivo_cuarentena("Foto Borrosa") == "cliente"
    assert clasificar_motivo_cuarentena("ILEGIBLE") == "cliente"
