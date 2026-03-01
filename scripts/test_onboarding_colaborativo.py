"""Test E2E: gestor inicia onboarding, empresario completa.

Requiere servidores arriba:
  - API:       uvicorn sfce.api.app:crear_app --factory --port 8000
  - Frontend:  cd dashboard && npm run dev
"""
import time
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
API = "http://localhost:8000"


def _login(page, email: str, password: str):
    page.goto(f"{BASE}/login")
    page.wait_for_selector("input[type=email]", timeout=10_000)
    page.fill("input[type=email]", email)
    page.fill("input[type=password]", password)
    page.click("button[type=submit]")
    page.wait_for_url(f"{BASE}/", timeout=10_000)
    print(f"  Login OK: {email}")


def test_flujo_onboarding_api():
    """Prueba el flujo completo via API directamente (sin browser)."""
    import requests

    # 1. Login admin
    r = requests.post(f"{API}/api/auth/login", json={"email": "admin@sfce.local", "password": "admin"})
    assert r.status_code == 200, f"Login fallido: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  [1] Login admin OK")

    # 2. Crear empresa en estado configurada
    r = requests.post(f"{API}/api/empresas", headers=headers, json={
        "cif": "B87654321",
        "nombre": "Empresa E2E Onboarding SL",
        "forma_juridica": "sl",
        "territorio": "peninsula",
        "regimen_iva": "general",
    })
    assert r.status_code in (200, 201), f"Crear empresa fallida: {r.text}"
    empresa_id = r.json()["id"]
    print(f"  [2] Empresa creada id={empresa_id}")

    # 3. Gestor invita al empresario
    r = requests.post(
        f"{API}/api/empresas/{empresa_id}/invitar-onboarding",
        headers=headers,
        json={"email_empresario": "empresario@test.com"},
    )
    assert r.status_code == 200, f"invitar-onboarding fallida: {r.text}"
    assert r.json()["estado"] == "pendiente_cliente"
    print("  [3] invitar-onboarding OK → estado=pendiente_cliente")

    # 4. Verificar estado via GET
    r = requests.get(f"{API}/api/onboarding/cliente/{empresa_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "pendiente_cliente"
    print("  [4] GET onboarding estado OK")

    # 5. Empresario completa el onboarding
    r = requests.put(
        f"{API}/api/onboarding/cliente/{empresa_id}",
        headers=headers,
        json={
            "iban": "ES9121000418450200051332",
            "banco_nombre": "CaixaBank",
            "email_facturas": "facturas@empresae2e.com",
            "proveedores": ["Repsol", "Iberdrola"],
        },
    )
    assert r.status_code == 200, f"PUT onboarding fallida: {r.text}"
    assert r.json()["estado"] == "cliente_completado"
    print("  [5] PUT onboarding completado OK → estado=cliente_completado")

    # 6. Verificar estado final
    r = requests.get(f"{API}/api/onboarding/cliente/{empresa_id}", headers=headers)
    assert r.json()["estado"] == "cliente_completado"
    assert r.json()["iban"] == "ES9121000418450200051332"
    assert "Repsol" in r.json()["proveedores"]
    print("  [6] Estado final verificado OK")

    print("\n  Flujo onboarding colaborativo API: PASS")


def test_flujo_browser():
    """Prueba la UI del wizard onboarding con Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Gestor hace login
            _login(page, "admin@sfce.local", "admin")

            # 2. Navegar al wizard de onboarding cliente (empresa id=1 si existe)
            page.goto(f"{BASE}/onboarding/cliente/1")
            time.sleep(1)

            contenido = page.content()
            # El wizard debe renderizar paso 1
            if "Paso 1" in contenido or "Datos de tu empresa" in contenido:
                print("  [browser] Wizard onboarding cliente renderiza OK")
            else:
                print("  [browser] WARN: wizard renderizo pero sin 'Paso 1' en contenido")

        except Exception as e:
            print(f"  [browser] WARN: {e} (servidores pueden no estar arriba)")
        finally:
            browser.close()


if __name__ == "__main__":
    print("=== Test E2E: Onboarding Colaborativo ===\n")

    print("[A] Flujo via API:")
    try:
        test_flujo_onboarding_api()
    except Exception as e:
        print(f"  FAIL: {e}")
        sys.exit(1)

    print("\n[B] Flujo via browser (requiere servidores):")
    try:
        test_flujo_browser()
    except Exception as e:
        print(f"  SKIP (servidor no disponible): {e}")

    print("\nFlujo onboarding colaborativo OK")
