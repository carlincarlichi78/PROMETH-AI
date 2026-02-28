#!/usr/bin/env python3
"""
add-nginx-security-headers.py
Añade security headers faltantes en cada conf file activo de nginx.
Idempotente: solo añade lo que falta. Hace backup antes de modificar.
"""

import os
import re
import shutil
from datetime import datetime

CONF_DIR = "/opt/infra/nginx/conf.d"
BACKUP_SUFFIX = f".bak.secheaders.{datetime.now().strftime('%Y%m%d%H%M%S')}"

# Headers requeridos: (clave para detectar, línea completa a añadir)
REQUIRED_HEADERS = [
    ("Strict-Transport-Security",
     '    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'),
    ("X-Frame-Options",
     '    add_header X-Frame-Options "SAMEORIGIN" always;'),
    ("X-Content-Type-Options",
     '    add_header X-Content-Type-Options "nosniff" always;'),
    ("Referrer-Policy",
     '    add_header Referrer-Policy "strict-origin-when-cross-origin" always;'),
    ("Permissions-Policy",
     '    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=()" always;'),
]

# Confs activos a procesar (excluir .bak, .backup, .save, etc.)
ACTIVE_CONFS = [
    "capweb.conf",
    "carloscanetegomez.conf",
    "ccoo-necta.conf",
    "clinicagerardogonzalez.conf",
    "facturascripts.conf",
    "lemonfresh-tuc.conf",
    "pintor.conf",
    "spice-landing.conf",
    "vaultwarden.conf",
]

# Patrones ancla donde insertar los headers (en orden de preferencia)
# Se insertan después de la primera línea que coincida
ANCHOR_PATTERNS = [
    r'resolver_timeout\s+\d+s;',
    r'ssl_session_tickets\s+off;',
    r'ssl_stapling_verify\s+on;',
    r'ssl_stapling\s+on;',
    r'ssl_session_timeout\s+\d+m;',
    r'ssl_session_cache\s+shared',
    r'ssl_prefer_server_ciphers\s+off;',
    r'ssl_ciphers\s+',
    r'ssl_protocols\s+',
    r'ssl_certificate_key\s+',
]


def find_https_server_blocks(content: str) -> list[tuple[int, int]]:
    """Encuentra los rangos de líneas de los server blocks que tienen listen 443."""
    blocks = []
    lines = content.split('\n')
    depth = 0
    block_start = None
    in_https_block = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        opens = stripped.count('{')
        closes = stripped.count('}')

        if stripped.startswith('server') and '{' in stripped and depth == 0:
            block_start = i
            depth += opens - closes
        elif depth == 0 and stripped.startswith('server') and opens > 0:
            block_start = i
            depth += opens - closes
        elif depth > 0:
            depth += opens - closes
            if 'listen 443' in stripped or 'listen [::]:443' in stripped:
                in_https_block = True
            if depth == 0 and block_start is not None:
                if in_https_block:
                    blocks.append((block_start, i))
                block_start = None
                in_https_block = False

    return blocks


def find_anchor_line(lines: list[str], block_start: int, block_end: int) -> int:
    """Encuentra la mejor línea ancla para insertar los headers."""
    for pattern in ANCHOR_PATTERNS:
        for i in range(block_start, block_end + 1):
            if re.search(pattern, lines[i]):
                return i
    # Fallback: usar la línea después de la primera {
    for i in range(block_start, block_end + 1):
        if '{' in lines[i]:
            return i
    return block_start + 1


def process_conf(filepath: str) -> bool:
    """Procesa un conf file y añade los headers faltantes. Retorna True si modificó."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    lines = content.split('\n')

    # Detectar qué headers ya están en ALGÚN server block HTTPS
    https_blocks = find_https_server_blocks(content)
    if not https_blocks:
        print(f"  [SKIP] No tiene server blocks HTTPS")
        return False

    modified = False

    # Para cada server block HTTPS, añadir los headers que faltan
    # Procesar en orden inverso para no invalidar índices
    for block_start, block_end in reversed(https_blocks):
        block_content = '\n'.join(lines[block_start:block_end + 1])

        # Ver qué headers faltan en ESTE bloque
        missing = []
        for key, header_line in REQUIRED_HEADERS:
            if key not in block_content:
                missing.append(header_line)

        if not missing:
            print(f"  [OK] Server block L{block_start}: todos los headers presentes")
            continue

        print(f"  [ADD] Server block L{block_start}: añadiendo {len(missing)} header(s)")
        for h in missing:
            print(f"        + {h.strip()}")

        # Encontrar ancla de inserción
        anchor_line = find_anchor_line(lines, block_start, block_end)

        # Insertar headers después del ancla
        insert_after = anchor_line
        new_lines = (
            lines[:insert_after + 1]
            + ['']
            + ['    # Security headers añadidos por add-nginx-security-headers.py']
            + missing
            + lines[insert_after + 1:]
        )
        lines = new_lines
        modified = True

    if not modified:
        return False

    # Backup antes de modificar
    backup_path = filepath + BACKUP_SUFFIX
    shutil.copy2(filepath, backup_path)
    print(f"  [BCK] Backup: {backup_path}")

    # Escribir archivo modificado
    new_content = '\n'.join(lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return True


def main():
    print(f"=== Añadiendo security headers en nginx confs ({CONF_DIR}) ===\n")

    total_modified = 0
    for conf_name in ACTIVE_CONFS:
        filepath = os.path.join(CONF_DIR, conf_name)
        if not os.path.exists(filepath):
            print(f"[NOTFOUND] {conf_name}")
            continue

        print(f"--- {conf_name} ---")
        try:
            modified = process_conf(filepath)
            if modified:
                total_modified += 1
                print(f"  => MODIFICADO\n")
            else:
                print(f"  => Sin cambios\n")
        except Exception as e:
            print(f"  [ERROR] {e}\n")

    print(f"\n=== Total modificados: {total_modified}/{len(ACTIVE_CONFS)} ===")


if __name__ == '__main__':
    main()
