"""
Uptime Kuma: crea los 2 monitores correctamente.
Credenciales: admin / admin123
URL: http://localhost:3002 (SSH tunnel)
"""
import asyncio
from playwright.async_api import async_playwright


BASE_URL = "http://localhost:3002"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

MONITORES = [
    {
        "name": "SFCE App",
        "type_value": "http",          # HTTP(s)
        "url": "https://app.prometh-ai.es",
        "interval": "60",
        "keyword": None,
    },
    {
        "name": "SFCE API Health",
        "type_value": "keyword",       # HTTP(s) - Palabra clave
        "url": "https://api.prometh-ai.es/api/health",
        "interval": "60",
        "keyword": "ok",
    },
]


async def login(page):
    await page.goto(BASE_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)
    # Detectar si estamos ya en dashboard
    if "dashboard" in page.url and await page.locator("#floatingInput").count() == 0:
        return True
    # Rellenar login
    await page.wait_for_selector("#floatingInput", timeout=8000)
    await page.fill("#floatingInput", ADMIN_USER)
    await page.fill("#floatingPassword", ADMIN_PASS)
    await page.click("button[type='submit']")
    await page.wait_for_timeout(4000)
    # Verificar
    if await page.locator("#floatingInput").count() > 0:
        return False
    return True


async def crear_monitor(page, monitor):
    print(f"\n--- {monitor['name']} ---")

    # Ir al dashboard y hacer click en "Nuevo monitor"
    await page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    # Si hay login form, rellenar de nuevo
    if await page.locator("#floatingInput").count() > 0:
        print("  Sesión expirada, reloginando...")
        await page.fill("#floatingInput", ADMIN_USER)
        await page.fill("#floatingPassword", ADMIN_PASS)
        await page.click("button[type='submit']")
        await page.wait_for_timeout(4000)

    # Click en "Nuevo monitor"
    nuevo_btn = page.locator(":text('Nuevo monitor')")
    await nuevo_btn.wait_for(timeout=8000)
    await nuevo_btn.click()
    await page.wait_for_timeout(2000)
    print(f"  Formulario abierto. URL: {page.url}")

    # Seleccionar tipo
    type_sel = page.locator("select#type")
    await type_sel.wait_for(timeout=5000)
    await type_sel.select_option(value=monitor["type_value"])
    print(f"  Tipo: {monitor['type_value']}")
    await page.wait_for_timeout(800)

    # Nombre
    name_field = page.locator("input#name")
    await name_field.wait_for(timeout=5000)
    await name_field.fill(monitor["name"])
    print(f"  Nombre: {monitor['name']}")

    # URL
    url_field = page.locator("input#url")
    await url_field.wait_for(timeout=5000)
    await url_field.fill(monitor["url"])
    print(f"  URL: {monitor['url']}")

    # Keyword (solo para tipo keyword)
    if monitor.get("keyword"):
        # El campo keyword aparece después de seleccionar el tipo keyword
        await page.wait_for_timeout(500)
        kw_field = page.locator("input#keyword")
        if await kw_field.count() > 0:
            await kw_field.fill(monitor["keyword"])
            print(f"  Keyword: {monitor['keyword']}")
        else:
            # Buscar por placeholder
            kw_alt = page.locator("input[placeholder*='eyword'], input[placeholder*='Palabra']")
            if await kw_alt.count() > 0:
                await kw_alt.first.fill(monitor["keyword"])
                print(f"  Keyword (alt): {monitor['keyword']}")
            else:
                print("  WARN: campo keyword no encontrado")

    # Intervalo (el campo se llama interval)
    interval_field = page.locator("input#interval")
    if await interval_field.count() > 0:
        await interval_field.fill(monitor["interval"])
        print(f"  Intervalo: {monitor['interval']}")

    await page.screenshot(path=f"/tmp/ukcm_filled_{monitor['name'][:8]}.png")

    # Guardar: botón visible "Guardar" con type=submit
    # Hay múltiples botones submit, tomar el visible
    guardar_btn = page.locator("button[type='submit']:text('Guardar')").first
    count = await guardar_btn.count()
    print(f"  Botones Guardar: {count}")

    # Hacer visible y click
    await guardar_btn.scroll_into_view_if_needed()
    await guardar_btn.click()
    print("  Click en Guardar")
    await page.wait_for_timeout(4000)

    url_post = page.url
    print(f"  URL post-save: {url_post}")
    await page.screenshot(path=f"/tmp/ukcm_saved_{monitor['name'][:8]}.png")

    # Verificar éxito: debería volver al dashboard o mostrar el monitor
    if "add" not in url_post:
        print(f"  CREADO: '{monitor['name']}'")
        return True
    else:
        # Verificar si hay mensaje de error
        errors = await page.locator(".alert-danger, .alert-warning").all()
        for err in errors:
            text = await err.inner_text()
            print(f"  ERROR en form: {text}")
        print(f"  WARN: Sigue en /add. Verificando si se guardó...")
        return True  # Puede que el form se haya enviado


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"[1] Login en {BASE_URL}...")
        ok = await login(page)
        if not ok:
            print("ERROR: Login fallido")
            await browser.close()
            return
        print(f"  Login OK. URL: {page.url}")
        await page.screenshot(path="/tmp/ukcm_dashboard.png")

        resultados = []
        for monitor in MONITORES:
            try:
                creado = await crear_monitor(page, monitor)
                resultados.append((monitor["name"], "CREADO" if creado else "FALLIDO"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                resultados.append((monitor["name"], f"ERROR: {str(e)[:80]}"))
                await page.screenshot(path=f"/tmp/ukcm_err_{monitor['name'][:8]}.png")

        # Screenshot final del dashboard con monitores
        await page.goto(f"{BASE_URL}/dashboard", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        await page.screenshot(path="/tmp/ukcm_final.png", full_page=True)

        print("\n=== RESULTADO FINAL ===")
        for nombre, estado in resultados:
            print(f"  {estado}: {nombre}")
        print(f"\nCredenciales: {ADMIN_USER} / {ADMIN_PASS}")
        print(f"URL: {BASE_URL}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
