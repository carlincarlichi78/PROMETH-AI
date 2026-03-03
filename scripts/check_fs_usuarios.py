from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://contabilidad.prometh-ai.es/", wait_until="networkidle", timeout=20000)
    page.screenshot(path="/tmp/fs_new_domain.png", full_page=True)
    print(f"URL: {page.url}")
    print(f"Título: {page.title()}")
    # Ver si hay errores
    errors = page.locator(".alert, .text-danger, .error").all()
    for e in errors:
        print(f"Error: {e.inner_text().strip()[:100]}")
    browser.close()
