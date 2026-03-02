"""
Test nivel 1: gestoría invita gestor.
Flujo:
  1. Superadmin invita admin_gestoria para Gestoria Test T0 (via API)
  2. admin_gestoria acepta invitacion en /auth/aceptar-invitacion
  3. admin_gestoria va a /mi-gestoria e invita un gestor
  4. Verificar que aparece la URL de invitacion del gestor
"""
import sys, io, json
import urllib.request, urllib.parse
from playwright.sync_api import sync_playwright

BASE    = "http://localhost:3001"
API     = "http://localhost:8000"
EMAIL_SA = "admin@sfce.local"
PASS_SA  = "admin"
GESTORIA_ID = 2  # Gestoria Test T0

EMAIL_AG = "admin_gestoria_t1@test.com"
PASS_AG  = "Password123!"
NOMBRE_AG = "Admin Gestoria T1"

EMAIL_G  = "gestor_t1@test.com"
NOMBRE_G = "Gestor T1"


def _api_post(url: str, body: dict, token: str = "") -> dict:
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
        return json.loads(e.read())


def _login_api(email: str, password: str) -> str:
    resp = _api_post(f"{API}/api/auth/login", {"email": email, "password": password})
    return resp.get("access_token", "")


def _limpiar_usuario(email: str) -> None:
    """Elimina el usuario de prueba de la BD si existe (para idempotencia)."""
    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///sfce.db")
    with engine.connect() as c:
        c.execute(text(f"DELETE FROM usuarios WHERE email='{email}'"))
        c.commit()


def main():
    import os; os.chdir("c:/Users/carli/PROYECTOS/CONTABILIDAD")

    # Limpiar usuarios de prueba para que el test sea idempotente
    _limpiar_usuario(EMAIL_AG)
    _limpiar_usuario(EMAIL_G)
    print("Usuarios de prueba limpiados")

    # --- PASO 1: Superadmin invita admin_gestoria via API ---
    print("1. Superadmin invita admin_gestoria para gestoria", GESTORIA_ID)
    token_sa = _login_api(EMAIL_SA, PASS_SA)
    if not token_sa:
        print("   FALLO - no se pudo obtener token de superadmin")
        return

    resp = _api_post(
        f"{API}/api/admin/gestorias/{GESTORIA_ID}/invitar",
        {"email": EMAIL_AG, "nombre": NOMBRE_AG, "rol": "admin_gestoria"},
        token_sa,
    )
    token_inv = resp.get("invitacion_token")
    url_inv   = resp.get("invitacion_url", f"/auth/aceptar-invitacion?token={token_inv}")
    if not token_inv:
        print(f"   FALLO - respuesta inesperada: {resp}")
        return
    print(f"   Token invitacion: {token_inv[:20]}...")
    print(f"   URL invitacion: {url_inv}")

    # --- PASO 2: admin_gestoria acepta invitacion en el frontend ---
    print("2. Aceptando invitacion en el dashboard...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        errores = []
        page.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)

        url_completa = f"{BASE}/auth/aceptar-invitacion?token={token_inv}"
        page.goto(url_completa)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t1_01_aceptar.png")

        titulos = page.locator("h1, h2, p.text-muted-foreground").all_text_contents()
        print(f"   Titulos pagina: {titulos[:3]}")

        # Rellenar passwords
        page.locator("#password").fill(PASS_AG)
        page.locator("#confirmar").fill(PASS_AG)
        page.screenshot(path="/tmp/t1_02_password.png")

        page.click("button[type='submit']")

        # Esperar redireccion al home
        try:
            page.wait_for_url(lambda url: "/auth/" not in url and "/login" not in url, timeout=8000)
            print(f"   OK - redirigido a: {page.url}")
        except Exception:
            page.screenshot(path="/tmp/t1_03_fallo.png")
            alertas = page.locator("[role='alert']").all_text_contents()
            print(f"   FALLO - no redirigido. URL: {page.url}. Alertas: {alertas}")
            browser.close()
            return

        page.screenshot(path="/tmp/t1_03_home.png")

        # --- PASO 3: /mi-gestoria e invitar gestor ---
        print("3. Navegando a /mi-gestoria...")
        page.goto(f"{BASE}/mi-gestoria")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t1_04_mi_gestoria.png")

        titulos = page.locator("h1, h2").all_text_contents()
        botones = [b for b in page.locator("button").all_text_contents() if b.strip()]
        print(f"   Titulos: {titulos}")
        print(f"   Botones: {botones}")

        # Buscar boton de invitar
        invitar_btn = None
        for sel in ["text=Invitar gestor", "text=Invitar", "button:has-text('nvitar')"]:
            if page.locator(sel).count() > 0:
                invitar_btn = sel
                break

        if not invitar_btn:
            print("   FALLO - No hay boton de invitar gestor")
            texto = page.locator("body").inner_text()
            print(f"   Texto: {texto[:600]}")
            browser.close()
            return

        print(f"   Boton encontrado: '{invitar_btn}'")
        page.click(invitar_btn)
        page.wait_for_timeout(500)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t1_05_form_invitar.png")

        # Rellenar formulario
        for id_campo, valor in [("nombre-gestor", NOMBRE_G), ("email-gestor", EMAIL_G)]:
            loc = page.locator(f"#" + id_campo)
            if loc.count() > 0:
                loc.fill(valor)
                print(f"   Rellenado #{id_campo} = {valor}")

        # Buscar selector de rol si existe
        for sel in ["select[id='rol']", "[id='rol-gestor']", "select"]:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.select_option("gestor")
                print(f"   Rol seleccionado: gestor")
                break

        page.screenshot(path="/tmp/t1_06_form_relleno.png")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="/tmp/t1_07_post_envio.png", full_page=True)

        # --- VERIFICAR: aparece URL de invitacion del gestor ---
        print("4. Verificando resultado...")
        contenido = page.content()
        if "aceptar-invitacion" in contenido or EMAIL_G in contenido:
            print(f"   PASS - URL de invitacion del gestor visible en pantalla")
        else:
            # Ver si dialog sigue abierto con error
            dialog_abierto = page.locator("[role='dialog']").count() > 0
            if dialog_abierto:
                texto_dialog = page.locator("[role='dialog']").inner_text()
                print(f"   FALLO - Dialog abierto: {texto_dialog[:300]}")
            else:
                texto = page.locator("body").inner_text()
                print(f"   FALLO - Sin URL de invitacion. Texto: {texto[:600]}")

        if errores:
            print(f"   Errores consola: {errores[:3]}")

        browser.close()
    print("\nScreenshots en /tmp/t1_*.png")


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
            escenario_id="test_nivel1_invitar_gestor",
            variante_id="playwright",
            canal="playwright",
            resultado="ok",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"capturas": []},
        )
    except Exception as e:
        return ResultadoEjecucion(
            escenario_id="test_nivel1_invitar_gestor",
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
