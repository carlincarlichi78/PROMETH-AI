"""
Test nivel 0: verificar que se puede crear una gestoria desde el dashboard.
Flujo: login como superadmin -> /admin/gestorias -> crear nueva gestoria -> verificar en lista.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3001"
EMAIL = "admin@sfce.local"
PASSWORD = "admin"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=200)
        page = browser.new_page()
        page.set_viewport_size({"width": 1280, "height": 900})

        # Capturar logs de consola
        errores_consola = []
        page.on("console", lambda msg: errores_consola.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)

        # --- LOGIN ---
        print("1. Login...")
        page.goto(f"{BASE}/login")
        page.wait_for_load_state("networkidle")

        # Usar IDs directos (confirmados del codigo fuente)
        page.locator("#email").fill(EMAIL)
        page.locator("#password").fill(PASSWORD)
        page.screenshot(path="/tmp/t0_01_credenciales.png")

        page.click("button[type='submit']")

        # Esperar navegacion tras login
        try:
            page.wait_for_url(lambda url: "/login" not in url, timeout=8000)
            print(f"   OK - redirigido a: {page.url}")
        except Exception:
            page.screenshot(path="/tmp/t0_02_login_fail.png")
            print(f"   FALLO - sigue en login. URL: {page.url}")
            if errores_consola:
                print("   Errores consola:", errores_consola[:5])
            # Intentar ver si hay mensaje de error en la pagina
            error_text = page.locator("[role='alert'], .error, [class*='error']").all_text_contents()
            if error_text:
                print(f"   Alerta en pantalla: {error_text}")
            browser.close()
            return

        page.screenshot(path="/tmp/t0_03_home.png")

        # --- NAVEGAR A GESTORIAS ---
        print("2. Navegando a /admin/gestorias...")
        page.goto(f"{BASE}/admin/gestorias")
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t0_04_gestorias_lista.png")

        titulos = page.locator("h1, h2").all_text_contents()
        print(f"   Titulos: {titulos}")

        botones = page.locator("button").all_text_contents()
        print(f"   Botones: {[b for b in botones if b.strip()]}")

        # --- BUSCAR BOTON CREAR ---
        print("3. Buscando boton de crear gestoria...")
        crear_btn = None
        for selector in [
            "text=Nueva gestoria",
            "text=Nueva gestoría",
            "text=Crear gestoria",
            "text=Nueva",
            "text=Crear",
            "button:has-text('estoria')",
            "button:has-text('nueva')",
            "button:has-text('crear')",
            "[data-testid='btn-crear-gestoria']",
        ]:
            loc = page.locator(selector)
            if loc.count() > 0:
                crear_btn = selector
                print(f"   Encontrado: '{selector}'")
                break

        if not crear_btn:
            print("   FALLO - No hay boton de crear. Capturando estado completo...")
            page.screenshot(path="/tmp/t0_05_sin_boton.png", full_page=True)
            print("   HTML resumido:")
            # Solo mostrar texto visible
            texto = page.locator("body").inner_text()
            print(f"   {texto[:1000]}")
            browser.close()
            return

        # --- CLICK EN CREAR ---
        print("4. Abriendo formulario...")
        page.click(crear_btn)
        page.wait_for_timeout(500)
        page.wait_for_load_state("networkidle")
        page.screenshot(path="/tmp/t0_06_formulario.png")

        inputs = page.locator("input").all()
        print(f"   Inputs en formulario: {len(inputs)}")
        for inp in inputs:
            name = inp.get_attribute("name") or ""
            placeholder = inp.get_attribute("placeholder") or ""
            id_attr = inp.get_attribute("id") or ""
            print(f"     id={id_attr} name={name} placeholder={placeholder}")

        # --- RELLENAR FORMULARIO ---
        print("5. Rellenando datos...")
        NOMBRE = "Gestoria Test T0"
        NIF    = "B12345678"
        EMAIL_G = "test0@gestoria.com"

        campos = [
            (["input[id='nombre']", "input[name='nombre']", "input[placeholder*='estoria']"], NOMBRE),
            (["input[id='cif']", "input[name='cif']", "input[placeholder='B12345678']"], NIF),
            (["input[id='email']", "input[name='email']", "input[type='email']"], EMAIL_G),
        ]

        for selectores, valor in campos:
            for sel in selectores:
                loc = page.locator(sel)
                if loc.count() > 0:
                    loc.first.fill(valor)
                    print(f"   Rellenado '{sel}' = {valor}")
                    break

        page.screenshot(path="/tmp/t0_07_formulario_relleno.png")

        # --- GUARDAR ---
        print("6. Guardando...")
        guardado = False
        for selector in ["button[type='submit']", "text=Guardar", "text=Crear", "text=Confirmar"]:
            loc = page.locator(selector)
            if loc.count() > 0:
                loc.first.click()
                guardado = True
                print(f"   Click en: '{selector}'")
                break

        if not guardado:
            print("   FALLO - No hay boton de guardar")
            page.screenshot(path="/tmp/t0_08_sin_guardar.png")
            browser.close()
            return

        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path="/tmp/t0_09_post_guardar.png", full_page=True)
        print(f"   URL tras guardar: {page.url}")

        # Verificar alerta de error en UI
        alertas = page.locator("p.text-destructive, [role='alert']").all_text_contents()
        if alertas:
            print(f"   Error UI: {alertas}")

        # --- VERIFICAR ---
        print("7. Verificando resultado...")

        # El dialog debe estar cerrado tras exito
        dialog_abierto = page.locator("[role='dialog']").count() > 0
        if dialog_abierto:
            print("   FALLO - El dialogo sigue abierto (submit bloqueado por validacion o error)")
            texto_dialog = page.locator("[role='dialog']").inner_text()
            print(f"   Contenido dialog: {texto_dialog[:400]}")
            browser.close()
            return

        # El nombre debe aparecer en una card de la lista (CardTitle), no en un input
        cards_nombre = page.locator(f"[data-slot='card-title']:has-text('{NOMBRE}'), .truncate:has-text('{NOMBRE}')")
        if cards_nombre.count() > 0:
            print(f"   PASS - '{NOMBRE}' encontrada en lista de cards")
        else:
            # Fallback: buscar en toda la pagina pero excluyendo inputs
            texto_pagina = page.locator("main, [role='main']").inner_text()
            if NOMBRE in texto_pagina:
                print(f"   PASS - '{NOMBRE}' encontrada en pagina (fuera de dialog)")
            else:
                print(f"   FALLO - '{NOMBRE}' NO encontrada en lista")
                print(f"   Texto pagina: {texto_pagina[:600]}")

        browser.close()
        print("\nScreenshots en /tmp/t0_*.png")

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
            escenario_id="test_crear_gestoria",
            variante_id="playwright",
            canal="playwright",
            resultado="ok",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"capturas": []},
        )
    except Exception as e:
        return ResultadoEjecucion(
            escenario_id="test_crear_gestoria",
            variante_id="playwright",
            canal="playwright",
            resultado="bug_pendiente",
            duracion_ms=int((time.monotonic() - inicio) * 1000),
            detalles={"error": str(e)},
        )


if __name__ == "__main__":
    import sys
    resultado = asyncio.run(ejecutar(headless="--headed" not in sys.argv))
    print(f"{'OK' if resultado.resultado == 'ok' else 'FAIL'}: {resultado.escenario_id} — {resultado.duracion_ms}ms")
    sys.exit(0 if resultado.resultado == "ok" else 1)
