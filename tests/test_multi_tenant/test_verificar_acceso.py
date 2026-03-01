import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from sfce.db.modelos_auth import Usuario
from sfce.db.modelos import Empresa


def _usuario(gestoria_id):
    u = MagicMock(spec=Usuario)
    u.gestoria_id = gestoria_id
    u.rol = "admin_gestoria" if gestoria_id else "superadmin"
    return u


def _empresa(gestoria_id):
    e = MagicMock(spec=Empresa)
    e.id = 1
    e.gestoria_id = gestoria_id
    return e


def test_superadmin_accede_a_cualquier_empresa():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(None)
    e = _empresa(5)
    sesion = MagicMock()
    sesion.get.return_value = e
    resultado = verificar_acceso_empresa(u, 1, sesion)
    assert resultado == e


def test_gestor_accede_a_su_empresa():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(2)
    e = _empresa(2)
    sesion = MagicMock()
    sesion.get.return_value = e
    resultado = verificar_acceso_empresa(u, 1, sesion)
    assert resultado == e


def test_gestor_no_accede_a_empresa_ajena():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(2)
    e = _empresa(9)
    sesion = MagicMock()
    sesion.get.return_value = e
    with pytest.raises(HTTPException) as exc:
        verificar_acceso_empresa(u, 1, sesion)
    assert exc.value.status_code == 403


def test_empresa_no_encontrada_lanza_404():
    from sfce.api.auth import verificar_acceso_empresa
    u = _usuario(None)
    sesion = MagicMock()
    sesion.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        verificar_acceso_empresa(u, 99, sesion)
    assert exc.value.status_code == 404
