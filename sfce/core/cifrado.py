"""Cifrado simétrico Fernet para credenciales de correo IMAP/OAuth."""
import os

from cryptography.fernet import Fernet


def _obtener_o_generar_clave() -> bytes:
    clave = os.getenv("SFCE_FERNET_KEY", "").strip()
    if not clave:
        clave = Fernet.generate_key().decode()
        print(
            f"[cifrado] SFCE_FERNET_KEY no configurada. "
            f"Clave generada (añadir a .env):\n  SFCE_FERNET_KEY={clave}"
        )
    if isinstance(clave, str):
        clave = clave.encode()
    return clave


_fernet = Fernet(_obtener_o_generar_clave())


def cifrar(texto: str) -> str:
    """Cifra un texto con la clave Fernet configurada."""
    return _fernet.encrypt(texto.encode()).decode()


def descifrar(cifrado: str) -> str:
    """Descifra un texto cifrado con cifrar()."""
    return _fernet.decrypt(cifrado.encode()).decode()
