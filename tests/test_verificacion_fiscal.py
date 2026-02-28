"""Tests para sfce.core.verificacion_fiscal — sin llamadas reales a servicios externos."""
import unittest
from unittest.mock import MagicMock, patch

from sfce.core.verificacion_fiscal import (
    inferir_tipo_persona,
    verificar_cif_aeat,
    verificar_vat_vies,
)


class TestInferirTipoPersona(unittest.TestCase):
    """Tests para la funcion inferir_tipo_persona."""

    def test_cif_juridica_letra_b(self):
        """CIF espanol con letra B → juridica."""
        resultado = inferir_tipo_persona("B12345678")
        self.assertEqual(resultado, "juridica")

    def test_cif_juridica_varios(self):
        """CIFs con diferentes letras validas → juridica."""
        for letra in "ABCDEFGHJNPSUVW":
            with self.subTest(letra=letra):
                self.assertEqual(inferir_tipo_persona(f"{letra}1234567X"), "juridica")

    def test_nif_persona_fisica(self):
        """NIF 8 digitos + letra → fisica."""
        self.assertEqual(inferir_tipo_persona("12345678A"), "fisica")

    def test_nif_minuscula(self):
        """NIF con letra minuscula sigue siendo fisica."""
        self.assertEqual(inferir_tipo_persona("12345678z"), "fisica")

    def test_nie_x_fisica(self):
        """NIE con X → fisica."""
        self.assertEqual(inferir_tipo_persona("X1234567L"), "fisica")

    def test_nie_y_fisica(self):
        """NIE con Y → fisica."""
        self.assertEqual(inferir_tipo_persona("Y9876543A"), "fisica")

    def test_nie_z_fisica(self):
        """NIE con Z → fisica."""
        self.assertEqual(inferir_tipo_persona("Z0000000B"), "fisica")

    def test_vat_europeo_se(self):
        """VAT sueco → juridica."""
        self.assertEqual(inferir_tipo_persona("SE556703748501"), "juridica")

    def test_vat_europeo_fr(self):
        """VAT frances → juridica."""
        self.assertEqual(inferir_tipo_persona("FR12345678901"), "juridica")

    def test_vat_europeo_de(self):
        """VAT aleman → juridica."""
        self.assertEqual(inferir_tipo_persona("DE123456789"), "juridica")

    def test_desconocido_vacio(self):
        """Cadena vacia → desconocida."""
        self.assertEqual(inferir_tipo_persona(""), "desconocida")

    def test_desconocido_formato_raro(self):
        """Formato que no encaja en ninguna regla → desconocida."""
        self.assertEqual(inferir_tipo_persona("???"), "desconocida")

    def test_limpia_espacios_y_guiones(self):
        """Se eliminan espacios y guiones antes de evaluar."""
        self.assertEqual(inferir_tipo_persona("B-1234567-8"), "juridica")
        self.assertEqual(inferir_tipo_persona(" 12345678A "), "fisica")


class TestVerificarVatVies(unittest.TestCase):
    """Tests para verificar_vat_vies con mock de requests.get."""

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_vat_valido(self, mock_get):
        """VAT valido devuelve valido=True con nombre y direccion."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "isValid": True,
            "name": "ACME AB",
            "address": "Storgatan 1, Stockholm",
        }
        mock_get.return_value = mock_resp

        resultado = verificar_vat_vies("SE556703748501")

        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["nombre"], "ACME AB")
        self.assertEqual(resultado["direccion"], "Storgatan 1, Stockholm")
        self.assertEqual(resultado["pais"], "SE")

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_vat_invalido(self, mock_get):
        """VAT invalido devuelve valido=False."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "isValid": False,
            "name": "",
            "address": "",
        }
        mock_get.return_value = mock_resp

        resultado = verificar_vat_vies("FR00000000000")

        self.assertFalse(resultado["valido"])
        self.assertEqual(resultado["pais"], "FR")

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_error_de_red(self, mock_get):
        """Error de red devuelve valido=None con clave 'error'."""
        import requests as req_real
        mock_get.side_effect = req_real.exceptions.ConnectionError("Sin conexion")

        resultado = verificar_vat_vies("DE123456789")

        self.assertIsNone(resultado["valido"])
        self.assertIn("error", resultado)

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_error_http_status(self, mock_get):
        """HTTP 500 devuelve valido=None con clave 'error'."""
        import requests as req_real
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_real.exceptions.HTTPError("500 Server Error")
        mock_get.return_value = mock_resp

        resultado = verificar_vat_vies("IT01234567890")

        self.assertIsNone(resultado["valido"])
        self.assertIn("error", resultado)

    def test_vat_demasiado_corto(self):
        """VAT con menos de 4 caracteres devuelve error sin llamada HTTP."""
        resultado = verificar_vat_vies("SE")
        self.assertIsNone(resultado["valido"])
        self.assertIn("error", resultado)

    @patch("sfce.core.verificacion_fiscal.requests.get")
    def test_nombre_none_se_convierte_a_vacio(self, mock_get):
        """Si la API devuelve name=null, nombre sera cadena vacia."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"isValid": True, "name": None, "address": None}
        mock_get.return_value = mock_resp

        resultado = verificar_vat_vies("NL123456789B01")

        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["nombre"], "")
        self.assertEqual(resultado["direccion"], "")


class TestVerificarCifAeat(unittest.TestCase):
    """Tests para verificar_cif_aeat con mock de requests.post."""

    _XML_IDENTIFICADO = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">"
        "<soapenv:Body>"
        "<VNifV2Output>"
        "<Contribuyente>"
        "<Resultado>IDENTIFICADO</Resultado>"
        "<Nombre>EMPRESA EJEMPLO SL</Nombre>"
        "</Contribuyente>"
        "</VNifV2Output>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )

    _XML_NO_IDENTIFICADO = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">"
        "<soapenv:Body>"
        "<VNifV2Output>"
        "<Contribuyente>"
        "<Resultado>NO IDENTIFICADO</Resultado>"
        "<Nombre></Nombre>"
        "</Contribuyente>"
        "</VNifV2Output>"
        "</soapenv:Body>"
        "</soapenv:Envelope>"
    )

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_cif_identificado(self, mock_post):
        """CIF identificado en AEAT → valido=True con nombre."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = self._XML_IDENTIFICADO
        mock_post.return_value = mock_resp

        resultado = verificar_cif_aeat("B12345678")

        self.assertTrue(resultado["valido"])
        self.assertEqual(resultado["nombre"], "EMPRESA EJEMPLO SL")

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_cif_no_identificado(self, mock_post):
        """CIF no identificado → valido=False."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = self._XML_NO_IDENTIFICADO
        mock_post.return_value = mock_resp

        resultado = verificar_cif_aeat("X9999999Z")

        self.assertFalse(resultado["valido"])

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_error_de_red(self, mock_post):
        """Error de conexion → valido=None con clave 'error'."""
        import requests as req_real
        mock_post.side_effect = req_real.exceptions.ConnectionError("Timeout")

        resultado = verificar_cif_aeat("B12345678")

        self.assertIsNone(resultado["valido"])
        self.assertIn("error", resultado)

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_error_http_status(self, mock_post):
        """HTTP 503 → valido=None con clave 'error'."""
        import requests as req_real
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req_real.exceptions.HTTPError("503 Service Unavailable")
        mock_post.return_value = mock_resp

        resultado = verificar_cif_aeat("A87654321")

        self.assertIsNone(resultado["valido"])
        self.assertIn("error", resultado)

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_xml_invalido(self, mock_post):
        """Respuesta XML malformada → valido=None con clave 'error'."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = "esto no es xml válido <<<"
        mock_post.return_value = mock_resp

        resultado = verificar_cif_aeat("B12345678")

        self.assertIsNone(resultado["valido"])
        self.assertIn("error", resultado)

    @patch("sfce.core.verificacion_fiscal.requests.post")
    def test_cif_se_normaliza_a_mayusculas(self, mock_post):
        """El CIF se convierte a mayusculas antes de enviarse."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = self._XML_IDENTIFICADO
        mock_post.return_value = mock_resp

        verificar_cif_aeat("b12345678")

        # Comprobar que el payload enviado contiene el CIF en mayusculas
        llamada_data = mock_post.call_args[1]["data"]
        xml_enviado = llamada_data.decode("utf-8")
        self.assertIn("B12345678", xml_enviado)


if __name__ == "__main__":
    unittest.main()
