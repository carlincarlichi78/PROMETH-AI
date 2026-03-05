"""Tests de contratos — validan que los Pydantic models aceptan datos
válidos y rechazan datos malformados."""
import json
import pytest
from sfce.core.contracts import (
    IntakeOutput,
    PreValidationOutput,
    RegistrationOutput,
    AsientosOutput,
    CorrectionOutput,
    CrossValidationOutput,
    DocumentoExtraido,
    DatosExtraidos,
    validar_json_pipeline,
)


# --- Fixtures ---

def _doc_extraido_minimo():
    """Doc con campos mínimos válidos."""
    return {
        "archivo": "factura_001.pdf",
        "hash_sha256": "abc123def456",
        "tipo": "FC",
        "datos_extraidos": {
            "emisor_nombre": "Proveedor SL",
            "emisor_cif": "B12345678",
            "total": 121.0,
            "fecha": "2025-06-15",
        },
        "entidad": "proveedor-sl",
        "entidad_cif": "B12345678",
        "confianza_global": 85.0,
        "nivel_confianza": "alto",
    }


def _doc_registrado_minimo():
    return {
        **_doc_extraido_minimo(),
        "idfactura": 42,
        "pagada": True,
        "verificacion_ok": True,
        "tipo_registro": "factura",
    }


# --- Fase 0: Intake ---

class TestIntakeOutput:
    def test_valida_salida_correcta(self):
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[_doc_extraido_minimo()],
            total_pdfs=5,
            total_duplicados=4,
            tier_stats={"0": 1},
        )
        data = json.loads(json_str)
        assert data["total_procesados"] == 1
        assert data["total_duplicados"] == 4
        assert len(data["documentos"]) == 1

    def test_rechaza_tipo_invalido(self):
        doc = _doc_extraido_minimo()
        doc["tipo"] = "INVENTADO"
        with pytest.raises(Exception):
            IntakeOutput.validar_y_serializar(
                documentos=[doc], total_pdfs=1,
            )

    def test_acepta_datos_extraidos_parciales(self):
        """OCR puede fallar parcialmente — solo archivo es obligatorio."""
        doc = _doc_extraido_minimo()
        doc["datos_extraidos"] = {"emisor_nombre": "Solo nombre"}
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[doc], total_pdfs=1,
        )
        data = json.loads(json_str)
        assert data["documentos"][0]["datos_extraidos"]["total"] is None

    def test_coerce_string_a_float(self):
        """FS devuelve importes como string a veces."""
        doc = _doc_extraido_minimo()
        doc["datos_extraidos"]["total"] = "121,50"
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[doc], total_pdfs=1,
        )
        data = json.loads(json_str)
        assert data["documentos"][0]["datos_extraidos"]["total"] == 121.5

    def test_campos_extra_no_rompen(self):
        """Futuros campos no deben romper validación."""
        doc = _doc_extraido_minimo()
        doc["campo_futuro"] = "valor"
        doc["datos_extraidos"]["campo_nuevo_ocr"] = "test"
        json_str = IntakeOutput.validar_y_serializar(
            documentos=[doc], total_pdfs=1,
        )
        assert "campo_futuro" in json_str


# --- Fase 1: Pre-validación ---

class TestPreValidationOutput:
    def test_valida_salida_correcta(self):
        json_str = PreValidationOutput.validar_y_serializar(
            validados=[_doc_extraido_minimo()],
            excluidos=[{"archivo": "bad.pdf", "motivo_exclusion": "CIF inválido"}],
        )
        data = json.loads(json_str)
        assert data["total_validados"] == 1
        assert data["total_excluidos"] == 1
        assert "validados" in data  # Clave canónica, no "documentos"

    def test_clave_canonica_es_validados(self):
        """El JSON debe usar 'validados', nunca 'documentos'."""
        json_str = PreValidationOutput.validar_y_serializar(
            validados=[_doc_extraido_minimo()], excluidos=[],
        )
        data = json.loads(json_str)
        assert "validados" in data
        assert "documentos" not in data


# --- Fase 2: Registro ---

class TestRegistrationOutput:
    def test_valida_salida_correcta(self):
        json_str = RegistrationOutput.validar_y_serializar(
            registrados=[_doc_registrado_minimo()],
            fallidos=[],
            total_entrada=1,
        )
        data = json.loads(json_str)
        assert data["total_registrados"] == 1

    def test_rechaza_total_inconsistente(self):
        """total_registrados debe coincidir con len(registrados)."""
        with pytest.raises(Exception):
            RegistrationOutput(
                fecha_registro="2025-01-01",
                total_entrada=5,
                total_registrados=99,  # mentira
                total_fallidos=0,
                registrados=[_doc_registrado_minimo()],
            )

    def test_acepta_asiento_directo(self):
        doc = _doc_registrado_minimo()
        doc["tipo_registro"] = "asiento_directo"
        doc["idasiento"] = 100
        json_str = RegistrationOutput.validar_y_serializar(
            registrados=[doc], fallidos=[], total_entrada=1,
        )
        data = json.loads(json_str)
        assert data["registrados"][0]["tipo_registro"] == "asiento_directo"

    def test_rechaza_tipo_registro_invalido(self):
        doc = _doc_registrado_minimo()
        doc["tipo_registro"] = "inventado"
        with pytest.raises(Exception):
            RegistrationOutput.validar_y_serializar(
                registrados=[doc], fallidos=[], total_entrada=1,
            )


# --- Fase 3: Asientos ---

class TestAsientosOutput:
    def test_valida_salida_correcta(self):
        asiento = {
            "archivo": "factura_001.pdf",
            "tipo": "FC",
            "idasiento": 500,
            "partidas": [
                {"codsubcuenta": "6000000", "debe": 100.0, "haber": 0.0},
                {"codsubcuenta": "4720000", "debe": 21.0, "haber": 0.0},
                {"codsubcuenta": "4000001", "debe": 0.0, "haber": 121.0},
            ],
        }
        json_str = AsientosOutput.validar_y_serializar(
            asientos=[asiento], sin_asiento=[], total_documentos=1,
        )
        data = json.loads(json_str)
        assert data["total_con_asiento"] == 1
        assert len(data["asientos"][0]["partidas"]) == 3

    def test_coerce_partida_string(self):
        """FS devuelve debe/haber como string."""
        asiento = {
            "archivo": "f.pdf", "tipo": "FC", "idasiento": 1,
            "partidas": [{"codsubcuenta": "600", "debe": "100.00", "haber": "0"}],
        }
        json_str = AsientosOutput.validar_y_serializar(
            asientos=[asiento], sin_asiento=[], total_documentos=1,
        )
        data = json.loads(json_str)
        assert data["asientos"][0]["partidas"][0]["debe"] == 100.0


# --- Fase 4: Corrección ---

class TestCorrectionOutput:
    def test_valida_salida_correcta(self):
        asiento = {
            "archivo": "f.pdf", "tipo": "FC", "idasiento": 500,
            "problemas_detectados": 1,
            "correcciones_aplicadas": 1,
            "problemas": [{"descripcion": "Debe/haber invertido", "corregido": True}],
        }
        json_str = CorrectionOutput.validar_y_serializar(
            asientos_corregidos=[asiento], total_asientos=1,
        )
        data = json.loads(json_str)
        assert data["total_problemas"] == 1

    def test_rechaza_count_inconsistente(self):
        asiento = {
            "archivo": "f.pdf", "tipo": "FC", "idasiento": 500,
            "problemas_detectados": 5,  # dice 5 pero solo hay 1
            "correcciones_aplicadas": 0,
            "problemas": [{"descripcion": "uno"}],
        }
        with pytest.raises(Exception):
            CorrectionOutput.validar_y_serializar(
                asientos_corregidos=[asiento], total_asientos=1,
            )


# --- Fase 5: Cruce ---

class TestCrossValidationOutput:
    def test_valida_salida_correcta(self):
        checks = [
            {"check": 1, "nombre": "Gastos vs 600", "pasa": True},
            {"check": 2, "nombre": "IVA soportado", "pasa": False, "diferencia": 0.03},
        ]
        json_str = CrossValidationOutput.validar_y_serializar(checks)
        data = json.loads(json_str)
        assert data["total_ok"] == 1
        assert data["total_fail"] == 1


# --- Helper: validar JSON existente ---

class TestValidarJsonPipeline:
    def test_archivo_desconocido(self):
        valido, errores = validar_json_pipeline("/tmp/desconocido.json")
        assert not valido
        assert "No hay contrato" in errores[0]
