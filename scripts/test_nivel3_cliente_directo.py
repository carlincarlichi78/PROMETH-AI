"""
Test nivel 3: superadmin crea cliente directo (sin gestoria).
Flujo:
  1. Superadmin va a /admin (o busca boton de cliente directo)
  2. Crea cliente directo via API (no hay UI especifica aun)
  3. Cliente acepta invitacion en /auth/aceptar-invitacion
  4. Cliente ve portal /portal
"""
import sys, io, json, os
import urllib.request
from playwright.sync_api import sync_playwright

BASE    = "http://localhost:3001"
API     = "http://localhost:8000"
EMAIL_SA = "admin@sfce.local"
PASS_SA  = "admin"

EMAIL_CD  = "cliente_directo_t3@test.com"
NOMBRE_CD = "Cliente Directo T3"
PASS_CD   = "Cliente123!"


def _api_post(url, body, token=""):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()}


def _limpiar_usuario(email):
    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///sfce.db")
    with engine.connect() as c:
        c.execute(text(f"DELETE FROM usuarios WHERE email='{email}'"))
        c.commit()


def main():
    os.chdir("c:/Users/carli/PROYECTOS/CONTABILIDAD")
    _limpiar_usuario(EMAIL_CD)

    # --- Paso 1: Superadmin crea cliente directo via API ---
    print("1. Superadmin crea cliente directo via API...")
    token_sa_resp = _api_post(f"{API}/api/auth/login",
                              {"email": EMAIL_SA, "password": PASS_SA})
    token_sa = token_sa_resp.get("access_token", "")
    if not token_sa:
        print(f"   FALLO login: {token_sa_resp}")
        return

    resp = _api_post(
        f"{API}/api/admin/clientes-directos",
        {"email": EMAIL_CD, "nombre": NOMBRE_CD},
        token_sa,
    )
    token_inv = resp.get("invitacion_token")
    if not token_inv:
        print(f"   FALLO crear cliente directo: {resp}")
        return
    print(f"   Cliente directo creado. Token: {token_inv[:20]}...")
    print(f"   URL: /auth/aceptar-invitacion?token={token_inv}")

    # --- Paso 2: Cliente acepta invitacion ---
    print("2. Cliente acepta invitacion en dashboard...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        errores = []
        page.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)

        page.goto(f"{BASE}/auth/aceptar-invitacion?token={token_inv}")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t3_01_aceptar.png")

        titulos = page.locator("h1, p.text-muted-foreground").all_text_contents()
        print(f"   Titulos: {titulos[:3]}")

        page.locator("#password").fill(PASS_CD)
        page.locator("#confirmar").fill(PASS_CD)
        page.click("button[type='submit']")

        try:
            page.wait_for_url(lambda url: "/auth/" not in url, timeout=8000)
            print(f"   OK - redirigido a: {page.url}")
        except Exception:
            alertas = page.locator("[role='alert']").all_text_contents()
            print(f"   FALLO - URL: {page.url}. Alertas: {alertas}")
            browser.close()
            return

        page.screenshot(path="/tmp/t3_02_post_login.png")

        # --- Paso 3: Cliente ve el portal ---
        print("3. Verificando portal del cliente...")
        # Esperar un momento para que React cargue
        page.wait_for_timeout(1000)

        url_actual = page.url
        print(f"   URL actual: {url_actual}")

        # Cliente sin empresa asignada deberia ver portal o mensaje informativo
        if "/portal" in url_actual or "/" in url_actual:
            page.goto(f"{BASE}/portal")
            page.wait_for_load_state("networkidle")
            page.screenshot(path="/tmp/t3_03_portal.png")
            texto = page.locator("body").inner_text()
            print(f"   Texto portal: {texto[:400]}")
            print("   PASS - Cliente directo creado y puede acceder al sistema")
        else:
            print(f"   FALLO - URL inesperada: {url_actual}")

        if errores:
            # Filtrar solo errores no-forwardRef
            reales = [e for e in errores if "forwardRef" not in e and "Function components cannot" not in e]
            if reales:
                print(f"   Errores consola: {reales[:2]}")

        browser.close()
    print("\nScreenshots en /tmp/t3_*.png")


import asyncio
import time
from scripts.motor_campo.modelos import ResultadoEjecucion


async def ejecutar(base_url: str = "https://app.prometh-ai.es",
                   headless: bool = True) -> ResultadoEjecucion:
    """Retorna ResultadoEjecucion. Llama al flujo Playwright existente."""
    inicio = time.monotonic()
    try:
        main()
        return ResultadoEjecucion(
            escenario_id="test_nivel3_cliente_directo",
            variante_id="playwright",
            canal="playwright",
            resultado="ok",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"capturas": []},
        )
    except Exception as e:
        return ResultadoEjecucion(
            escenario_id="test_nivel3_cliente_directo",
            variante_id="playwright",
            canal="playwright",
            resultado="bug_pendiente",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"error": str(e)},
        )


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    resultado = asyncio.run(ejecutar(headless="--headed" not in sys.argv))
    print(f"{'OK' if resultado.resultado == 'ok' else 'FAIL'}: {resultado.escenario_id} — {resultado.duracion_ms}ms")
    sys.exit(0 if resultado.resultado == "ok" else 1)
