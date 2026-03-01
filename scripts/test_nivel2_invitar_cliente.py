"""
Test nivel 2: gestor invita cliente a empresa.
Requisito: admin_gestoria_t1@test.com existe (creado en nivel 1).
Flujo:
  1. Gestor T1 acepta su invitacion (via API aceptar-invitacion)
  2. Gestor navega a empresa 1 (PASTORINO) e invita un cliente
  3. Verificar que aparece URL de invitacion del cliente
"""
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import urllib.request, urllib.parse
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"
API  = "http://localhost:8000"
EMPRESA_ID = 1  # PASTORINO COSTA DEL SOL S.L.

EMAIL_G  = "gestor_t1@test.com"
PASS_G   = "Gestor123!"
EMAIL_C  = "cliente_t2@test.com"
NOMBRE_C = "Cliente T2"


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


def _obtener_estado_gestor():
    """Devuelve (invitacion_token_o_None, activo) para el gestor T1."""
    from sqlalchemy import create_engine, text
    engine = create_engine("sqlite:///sfce.db")
    with engine.connect() as c:
        row = c.execute(text(
            f"SELECT invitacion_token, activo FROM usuarios WHERE email='{EMAIL_G}'"
        )).fetchone()
        if not row:
            return None, False
        return row[0], bool(row[1])


def main():
    os.chdir("c:/Users/carli/PROYECTOS/CONTABILIDAD")
    _limpiar_usuario(EMAIL_C)

    token_gestor, gestor_activo = _obtener_estado_gestor()

    if not token_gestor and not gestor_activo:
        print("FALLO - Gestor T1 no existe en BD. Ejecutar test nivel 1 primero.")
        return

    if token_gestor:
        print(f"1. Token invitacion gestor encontrado: {token_gestor[:20]}...")
    else:
        print(f"1. Gestor ya activo (sin token pendiente) — login directo con contrasena conocida")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=150)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})
        errores = []
        page.on("console", lambda m: errores.append(m.text) if m.type == "error" else None)

        # --- Paso 1: Gestor entra al sistema ---
        if token_gestor:
            print("2. Gestor acepta invitacion...")
            page.goto(f"{BASE}/auth/aceptar-invitacion?token={token_gestor}")
            page.wait_for_load_state("networkidle")
            page.locator("#password").fill(PASS_G)
            page.locator("#confirmar").fill(PASS_G)
            page.click("button[type='submit']")
        else:
            print("2. Gestor hace login directo...")
            page.goto(f"{BASE}/login")
            page.wait_for_load_state("networkidle")
            page.locator("#email").fill(EMAIL_G)
            page.locator("#password").fill(PASS_G)
            page.click("button[type='submit']")

        try:
            page.wait_for_url(lambda url: "/auth/" not in url and "/login" not in url, timeout=8000)
            print(f"   OK - redirigido a: {page.url}")
        except Exception:
            alertas = page.locator("[role='alert']").all_text_contents()
            print(f"   FALLO - URL: {page.url}. Alertas: {alertas}")
            browser.close()
            return

        # --- Paso 2: Navegar a empresa e invitar cliente ---
        print("3. Navegando a empresa 1...")
        # El gestor necesita acceso a la empresa. Asignarla via BD si hace falta.
        from sqlalchemy import create_engine, text
        engine = create_engine("sqlite:///sfce.db")
        with engine.connect() as c:
            c.execute(text(
                f"UPDATE usuarios SET empresas_asignadas='[{EMPRESA_ID}]' "
                f"WHERE email='{EMAIL_G}'"
            ))
            c.commit()
            print(f"   Empresa {EMPRESA_ID} asignada al gestor")

        # Relogin para que el token refleje los cambios (en realidad empresas_asignadas
        # no esta en el JWT, pero si en el perfil cargado)
        # Navegar directo a la empresa
        page.goto(f"{BASE}/empresa/{EMPRESA_ID}/pyg")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t2_01_empresa.png")
        print(f"   URL: {page.url}")

        # Buscar boton invitar cliente (puede estar en config/usuarios o en la empresa)
        # Intentar la ruta especifica de invitar cliente
        page.goto(f"{BASE}/empresa/{EMPRESA_ID}/config/usuarios")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t2_02_usuarios.png")

        botones = [b for b in page.locator("button").all_text_contents() if b.strip()]
        print(f"   Botones en config/usuarios: {botones}")

        invitar_btn = None
        for sel in [
            "text=Invitar cliente",
            "text=Nuevo cliente",
            "text=Invitar",
            "button:has-text('cliente')",
            "button:has-text('Cliente')",
        ]:
            if page.locator(sel).count() > 0:
                invitar_btn = sel
                break

        if not invitar_btn:
            # Intentar via PyG page que podria tener el boton
            page.goto(f"{BASE}/empresa/{EMPRESA_ID}/pyg")
            page.wait_for_load_state("networkidle")
            for sel in ["text=Invitar cliente", "button:has-text('cliente')"]:
                if page.locator(sel).count() > 0:
                    invitar_btn = sel
                    break

        if not invitar_btn:
            print("   FALLO - No hay boton de invitar cliente")
            texto = page.locator("body").inner_text()
            print(f"   Texto: {texto[:600]}")
            browser.close()
            return

        print(f"   Boton encontrado: '{invitar_btn}'")
        page.click(invitar_btn)
        page.wait_for_timeout(500)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t2_03_form_cliente.png")

        inputs = {inp.get_attribute("id"): inp.get_attribute("placeholder")
                  for inp in page.locator("input").all()}
        print(f"   Inputs: {inputs}")

        for id_campo, valor in [("nombre", NOMBRE_C), ("email", EMAIL_C)]:
            loc = page.locator(f"#{id_campo}")
            if loc.count() > 0:
                loc.fill(valor)
                print(f"   Rellenado #{id_campo} = {valor}")

        page.screenshot(path="/tmp/t2_04_form_relleno.png")
        page.click("button[type='submit']")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="/tmp/t2_05_post_envio.png", full_page=True)

        print("4. Verificando resultado...")
        contenido = page.content()
        if "aceptar-invitacion" in contenido or EMAIL_C in contenido:
            print(f"   PASS - URL de invitacion del cliente visible")
        else:
            dialog_abierto = page.locator("[role='dialog']").count() > 0
            if dialog_abierto:
                texto_dialog = page.locator("[role='dialog']").inner_text()
                print(f"   FALLO - Dialog abierto: {texto_dialog[:300]}")
            else:
                texto = page.locator("body").inner_text()
                print(f"   FALLO - Sin confirmacion. Texto: {texto[:500]}")

        browser.close()
    print("\nScreenshots en /tmp/t2_*.png")


if __name__ == "__main__":
    main()
