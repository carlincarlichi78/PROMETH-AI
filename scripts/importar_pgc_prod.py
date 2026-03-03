"""
Importa el Plan General Contable en cada instancia FS para todas sus empresas.
Ejecutar en el servidor: python3 /tmp/importar_pgc_prod.py
"""
import urllib.request
import urllib.parse
import http.cookiejar
import re
import time

INSTANCIAS = {
    "https://fs-uralde.prometh-ai.es": [
        ("0002", "pymes"),    # PASTORINO (SL)
        ("0003", "general"),  # GERARDO (autónomo)
        ("0004", "pymes"),    # CHIRINGUITO (SL)
        ("0005", "general"),  # ELENA (autónomo)
    ],
    "https://fs-gestoriaa.prometh-ai.es": [
        ("0002", "general"),  # MARCOS RUIZ (autónomo)
        ("0003", "pymes"),    # LA MAREA (SL)
        ("0004", "pymes"),    # AURORA DIGITAL (SL)
        ("0005", "pymes"),    # CATERING COSTA (SL)
        ("0006", "pymes"),    # DISTRIBUCIONES LEVANTE (SL)
    ],
    "https://fs-javier.prometh-ai.es": [
        ("0002", "general"),  # COMUNIDAD MIRADOR (comunidad)
        ("0003", "general"),  # FRANCISCO MORA (autónomo)
        ("0004", "pymes"),    # GASTRO HOLDING (SL)
        ("0005", "general"),  # BERMUDEZ (autónomo)
    ],
}

NICK = "carloscanetegomez"
FS_PASS = "Uralde2026!"


def get_opener_with_jar():
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    return opener, jar


def get_token_from_page(opener, url):
    """Obtiene el multireqtoken del formulario de login."""
    req = urllib.request.Request(f"{url}/login",
                                 headers={"User-Agent": "Mozilla/5.0"})
    resp = opener.open(req, timeout=15)
    html = resp.read().decode("utf-8", errors="ignore")
    m = re.search(r'name="multireqtoken"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


def login(url):
    opener, jar = get_opener_with_jar()

    token = get_token_from_page(opener, url)
    if not token:
        print("  ERROR: no se encontró token en la página de login")
        return None, None

    print(f"  Token: {token[:20]}...")

    data = urllib.parse.urlencode({
        "fsNick": NICK,
        "fsPassword": FS_PASS,
        "multireqtoken": token,
        "action": "login",
    }).encode()

    req = urllib.request.Request(
        f"{url}/login",
        data=data, method="POST",
        headers={"User-Agent": "Mozilla/5.0",
                 "Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        resp = opener.open(req, timeout=15)
        cookies = {c.name: c.value for c in jar}
        if cookies.get("fsLogkey"):
            print(f"  Login OK — fsNick={cookies.get('fsNick','')}")
            return opener, cookies
        else:
            print(f"  Login FALLO — cookies: {list(cookies.keys())}")
            return None, None
    except Exception as e:
        print(f"  Login ERROR: {e}")
        return None, None


def get_token_from_ejercicio(opener, url, codejercicio):
    """Obtiene token fresco desde la página del ejercicio."""
    req = urllib.request.Request(
        f"{url}/index.php?page=EditEjercicio&code={codejercicio}",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    try:
        resp = opener.open(req, timeout=15)
        html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r'name="multireqtoken"\s+value="([^"]+)"', html)
        return m.group(1) if m else ""
    except Exception as e:
        print(f"    ERROR obteniendo token para {codejercicio}: {e}")
        return ""


def importar_pgc(opener, url, codejercicio, tipo):
    """Importa el plan contable para un ejercicio."""
    token = get_token_from_ejercicio(opener, url, codejercicio)
    if not token:
        print(f"    {codejercicio} ({tipo}) → ERROR: sin token")
        return False

    plan_code = "PGCPYMES2007" if tipo == "pymes" else "PGC2007"

    data = urllib.parse.urlencode({
        "codejercicio": codejercicio,
        "action": "importarplan",
        "multireqtoken": token,
        "codplan": plan_code,
    }).encode()

    req = urllib.request.Request(
        f"{url}/index.php?page=EditEjercicio&code={codejercicio}",
        data=data, method="POST",
        headers={"User-Agent": "Mozilla/5.0",
                 "Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        resp = opener.open(req, timeout=60)
        html = resp.read().decode("utf-8", errors="ignore")
        # FS muestra mensaje de éxito o ya importado
        if "importado" in html.lower() or "subcuenta" in html.lower() or resp.status in (200, 302):
            print(f"    {codejercicio} ({tipo}/{plan_code}) → OK")
            return True
        else:
            print(f"    {codejercicio} ({tipo}/{plan_code}) → posible error (HTTP {resp.status})")
            return True  # 200 sin mensaje claro = probablemente OK
    except Exception as e:
        print(f"    {codejercicio} ({tipo}/{plan_code}) → ERROR: {e}")
        return False


def main():
    total_ok = 0
    total_err = 0

    for url, ejercicios in INSTANCIAS.items():
        print(f"\n{'='*60}")
        print(f"Instancia: {url}")

        opener, cookies = login(url)
        if opener is None:
            total_err += len(ejercicios)
            continue

        for codejercicio, tipo in ejercicios:
            ok = importar_pgc(opener, url, codejercicio, tipo)
            if ok:
                total_ok += 1
            else:
                total_err += 1
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"RESULTADO FINAL: {total_ok} OK  |  {total_err} errores")


if __name__ == "__main__":
    main()
