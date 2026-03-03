"""
Añade registro A contabilidad.prometh-ai.es → 65.108.60.69 en DonDominio.
"""
from playwright.sync_api import sync_playwright

DD_URL = "https://www.dondominio.com"
USER = "carlincarlichi"
PASSWORD = "Caixabank1159$"
DOMAIN = "prometh-ai.es"
SUBDOMAIN = "contabilidad"
IP = "65.108.60.69"

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("1. Login en DonDominio (esperando SPA)...")
        page.goto(f"{DD_URL}/es/login/", timeout=30000)

        # Esperar a que aparezcan los inputs (SPA React puede tardar)
        try:
            page.wait_for_selector("input", timeout=20000, state="attached")
            print("   Inputs aparecieron ✓")
        except:
            print("   Timeout esperando inputs")

        page.wait_for_timeout(2000)
        page.screenshot(path="/tmp/dd_01_login.png", full_page=True)

        all_inputs = page.locator("input").all()
        print(f"   Inputs: {len(all_inputs)}")
        for inp in all_inputs:
            print(f"   - name='{inp.get_attribute('name')}' type='{inp.get_attribute('type')}' id='{inp.get_attribute('id')}'")

        if len(all_inputs) == 0:
            # Quizás hay shadow DOM
            result = page.evaluate("""
                () => {
                    const all = document.querySelectorAll('*');
                    const inputs = [];
                    for (const el of all) {
                        if (el.shadowRoot) {
                            const shadowInputs = el.shadowRoot.querySelectorAll('input');
                            shadowInputs.forEach(i => inputs.push({
                                name: i.name, type: i.type, id: i.id,
                                shadow: true
                            }));
                        }
                    }
                    // also regular inputs
                    document.querySelectorAll('input').forEach(i => inputs.push({
                        name: i.name, type: i.type, id: i.id, shadow: false
                    }));
                    return inputs;
                }
            """)
            print(f"   Inputs via JS (incl. shadow DOM): {result}")

            # Ver qué scripts se cargaron
            scripts = page.locator("script[src]").all()
            print(f"   Scripts cargados: {[s.get_attribute('src') for s in scripts[:5]]}")

        browser.close()

if __name__ == "__main__":
    run()
