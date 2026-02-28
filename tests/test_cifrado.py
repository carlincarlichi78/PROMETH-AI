"""Tests del servicio de cifrado Fernet para credenciales de correo."""
import os
import pytest


def test_cifrar_y_descifrar_credencial(monkeypatch):
    monkeypatch.setenv("SFCE_FERNET_KEY", "")
    # Forzar recarga para que use la clave auto-generada
    import importlib
    import sfce.core.cifrado as m
    importlib.reload(m)
    from sfce.core.cifrado import cifrar, descifrar
    original = "mi_contraseña_segura_123"
    cifrado = cifrar(original)
    assert cifrado != original
    assert descifrar(cifrado) == original


def test_fernet_key_auto_generada_si_no_existe(monkeypatch):
    monkeypatch.setenv("SFCE_FERNET_KEY", "")
    from importlib import reload
    import sfce.core.cifrado as m
    reload(m)
    assert m._fernet is not None


def test_fernet_key_usada_si_existe(monkeypatch):
    """Si SFCE_FERNET_KEY está configurada, se usa esa clave."""
    from cryptography.fernet import Fernet
    clave = Fernet.generate_key().decode()
    monkeypatch.setenv("SFCE_FERNET_KEY", clave)
    from importlib import reload
    import sfce.core.cifrado as m
    reload(m)
    # Debe poder cifrar y descifrar correctamente
    texto = "secreto_de_prueba"
    assert m.descifrar(m.cifrar(texto)) == texto
