#!/bin/bash
# docker-user-firewall.sh — Bloquear puertos sensibles expuestos por Docker
# La cadena DOCKER-USER se evalúa ANTES que DOCKER, y Docker no la toca.
# Ejecutado por docker-user-firewall.service al arrancar, después de Docker.
# Idempotente: seguro para ejecutar múltiples veces.

# Verificar que la cadena DOCKER-USER existe (Docker debe estar corriendo)
if ! iptables -L DOCKER-USER -n > /dev/null 2>&1; then
  echo 'ERROR: DOCKER-USER chain no existe. ¿Docker está corriendo?'
  exit 1
fi

# Limpiar reglas previas de este script (seguro para re-ejecución)
# Eliminar todas las reglas con comentario 'sfce-sec' de mayor a menor
NUMS=$(iptables -L DOCKER-USER -n --line-numbers 2>/dev/null | grep 'sfce-sec' | awk '{print $1}' | sort -rn)
if [ -n "$NUMS" ]; then
  for num in $NUMS; do
    iptables -D DOCKER-USER "$num" 2>/dev/null || true
  done
  echo "Reglas previas sfce-sec eliminadas"
fi

# -------------------------------------------------------
# REGLA 0: Tráfico Docker-interno siempre permitido
# Fuentes 172.16.0.0/12 = todas las subredes Docker por defecto
iptables -I DOCKER-USER 1 -s 172.16.0.0/12 -m comment --comment "sfce-sec:docker-internal" -j RETURN

# REGLA 1: PostgreSQL 5432 — bloquear acceso externo
iptables -A DOCKER-USER -p tcp --dport 5432 -m comment --comment "sfce-sec:block-pg" -j DROP

# REGLA 2: Redis 6379 — bloquear acceso externo
iptables -A DOCKER-USER -p tcp --dport 6379 -m comment --comment "sfce-sec:block-redis" -j DROP

# REGLA 3: API interna 8000 — solo via nginx proxy
iptables -A DOCKER-USER -p tcp --dport 8000 -m comment --comment "sfce-sec:block-api" -j DROP

# REGLA 4: Nginx interno 8080 — solo via nginx principal
iptables -A DOCKER-USER -p tcp --dport 8080 -m comment --comment "sfce-sec:block-8080" -j DROP

echo "DOCKER-USER firewall rules aplicadas OK"
iptables -L DOCKER-USER -n -v
