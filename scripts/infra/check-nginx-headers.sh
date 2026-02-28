#!/bin/bash
# Verifica qué security headers faltan en cada conf activo de nginx

CONF_DIR="/opt/infra/nginx/conf.d"
CONFS=(capweb.conf carloscanetegomez.conf ccoo-necta.conf clinicagerardogonzalez.conf facturascripts.conf lemonfresh-tuc.conf pintor.conf spice-landing.conf vaultwarden.conf)

for f in "${CONFS[@]}"; do
  FILEPATH="$CONF_DIR/$f"
  echo "=== $f ==="
  grep -q 'Strict-Transport-Security' "$FILEPATH" 2>/dev/null && echo "  HSTS: OK" || echo "  HSTS: FALTA"
  grep -q 'X-Frame-Options' "$FILEPATH" 2>/dev/null && echo "  X-Frame: OK" || echo "  X-Frame: FALTA"
  grep -q 'X-Content-Type' "$FILEPATH" 2>/dev/null && echo "  X-Content-Type: OK" || echo "  X-Content-Type: FALTA"
  grep -q 'Referrer-Policy' "$FILEPATH" 2>/dev/null && echo "  Referrer: OK" || echo "  Referrer: FALTA"
done
