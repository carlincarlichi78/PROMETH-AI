# Diseño: 3 Instancias FacturaScripts Independientes

**Fecha**: 2026-03-03
**Sesión**: 47
**Objetivo**: Aislamiento total — cada gestoría ve solo sus propias empresas en FacturaScripts.

---

## Contexto

Actualmente todas las empresas comparten una única instancia FS (`contabilidad.prometh-ai.es`). El aislamiento existe a nivel SFCE (pipeline inyecta credenciales por gestoría via migración 024), pero los gestores que acceden directamente al panel FS pueden ver datos de otras gestorías.

**Estado previo completado (sesión 45)**:
- Migración 024: columnas `gestorias.fs_url` + `gestorias.fs_token_enc` (Fernet)
- `obtener_credenciales_gestoria()` en `sfce/core/fs_api.py`
- `_resolver_credenciales_fs()` en `sfce/core/pipeline_runner.py` (inyecta env vars en subprocess)
- Endpoints admin `PUT/GET /api/admin/gestorias/{id}/fs-credenciales`

---

## Arquitectura

### Instancias Docker

| Instancia | Directorio servidor | Puerto | Dominio |
|-----------|---------------------|--------|---------|
| fs-uralde | `/opt/apps/fs-uralde/` | 8010 | `fs-uralde.prometh-ai.es` |
| fs-gestoriaa | `/opt/apps/fs-gestoriaa/` | 8011 | `fs-gestoriaa.prometh-ai.es` |
| fs-javier | `/opt/apps/fs-javier/` | 8012 | `fs-javier.prometh-ai.es` |

Cada una: `docker-compose.yml` propio + MariaDB 10.11 propio + volúmenes aislados.

`contabilidad.prometh-ai.es` queda intacto para `carloscanetegomez` (superadmin global, acceso a todo via SFCE).

### docker-compose.yml por instancia (template)

```yaml
services:
  facturascripts:
    image: <MISMO_QUE_INSTANCIA_ACTUAL>  # verificar: docker inspect facturascripts | grep Image
    restart: unless-stopped
    ports:
      - "PORT:80"       # 8010/8011/8012 según instancia
    environment:
      DB_HOST: mariadb
      DB_PORT: "3306"
      DB_NAME: facturascripts
      DB_USER: fsuser
      DB_PASS: ${FS_DB_PASS}
    volumes:
      - ./app_data:/var/www/facturascripts/MyFiles
    depends_on:
      - mariadb

  mariadb:
    image: mariadb:10.11
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${FS_DB_ROOT_PASS}
      MYSQL_DATABASE: facturascripts
      MYSQL_USER: fsuser
      MYSQL_PASSWORD: ${FS_DB_PASS}
    volumes:
      - ./db_data:/var/lib/mysql
```

### Nginx vhost (template por instancia)

```nginx
server {
    listen 80;
    server_name fs-uralde.prometh-ai.es;
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl;
    server_name fs-uralde.prometh-ai.es;
    ssl_certificate /etc/letsencrypt/live/fs-uralde.prometh-ai.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/fs-uralde.prometh-ai.es/privkey.pem;

    include /etc/nginx/conf.d/00-security.conf;

    location / {
        proxy_pass http://localhost:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        client_max_body_size 64m;
    }
}
```

---

## SFCE BD — Migración 025

### Objetivo
Crear gestoria_id=3 para Javier (asesor independiente que actúa como su propia gestoría) y elevar roles de socios en Gestoría A.

### Cambios
```sql
-- 1. Nueva gestoría para Javier
INSERT INTO gestorias (nombre, email_contacto, activa)
VALUES ('Javier Independiente', 'javier@prometh-ai.es', TRUE);
-- Resultado esperado: id=3

-- 2. Javier: asesor_independiente → admin_gestoria de gestoria_id=3
UPDATE usuarios SET rol='admin_gestoria', gestoria_id=3
WHERE email='javier@prometh-ai.es';

-- 3. Empresas 10-13 → gestoria_id=3
UPDATE empresas SET gestoria_id=3 WHERE id IN (10, 11, 12, 13);

-- 4. gestor1 y gestor2: asesor → admin_gestoria (socios con mismos derechos)
UPDATE usuarios SET rol='admin_gestoria'
WHERE email IN ('gestor1@prometh-ai.es', 'gestor2@prometh-ai.es');
```

### Impacto en SFCE
- `gestor1` y `gestor2`: acceso admin a su gestoría en dashboard SFCE (invitar asesores, configurar empresas)
- `javier`: accede como admin de su propia gestoría (empresas 10-13)
- `pipeline_runner._resolver_credenciales_fs()`: funciona sin cambios (lee `empresa.gestoria.fs_url`)

---

## Usuarios FS por instancia

Creación via `docker exec` + INSERT MariaDB + hash bcrypt. Patrón exacto: sesión 46.
Password universal: `Uralde2026!`

| Instancia | Nick | Nivel FS | Rol |
|-----------|------|---------|-----|
| fs-uralde | `carloscanetegomez` | 99 | Superadmin global |
| fs-uralde | `sergio` | 10 | Propietario gestoría |
| fs-uralde | `francisco`, `mgarcia`, `llupianez` | 5 | Asesores |
| fs-gestoriaa | `carloscanetegomez` | 99 | Superadmin global |
| fs-gestoriaa | `gestor1`, `gestor2` | 10 | Socios (mismos derechos) |
| fs-javier | `carloscanetegomez` | 99 | Superadmin global |
| fs-javier | `javier` | 10 | Propietario único |

Nota: en FS niveles 10+ = admin (gestión usuarios, acceso total a la instancia). Nivel 5 = asesor (acceso datos pero no gestión). Como gestor1 y gestor2 son socios iguales y comparten acceso en la misma instancia, ambos van a nivel 10.

---

## Empresas FS por instancia

Via `FsSetup(base_url=URL, token=TOKEN).setup_completo()` (ya soporta parametrización). PGC: "pymes" para SL/SA, "general" para autónomos/otros.

| Instancia | Empresas SFCE (id) | Nombre empresa | Forma | PGC |
|-----------|---------------------|----------------|-------|-----|
| fs-uralde | 1 | PASTORINO COSTA DEL SOL S.L. | sl | pymes |
| fs-uralde | 2 | GERARDO GONZALEZ CALLEJON | autonomo | general |
| fs-uralde | 3 | CHIRINGUITO SOL Y ARENA S.L. | sl | pymes |
| fs-uralde | 4 | ELENA NAVARRO PRECIADOS | autonomo | general |
| fs-gestoriaa | 5 | MARCOS RUIZ DELGADO | autonomo | general |
| fs-gestoriaa | 6 | RESTAURANTE LA MAREA S.L. | sl | pymes |
| fs-gestoriaa | 7 | Aurora Digital S.L. | sl | pymes |
| fs-gestoriaa | 8 | Catering Costa S.L. | sl | pymes |
| fs-gestoriaa | 9 | Distribuciones Levante S.L. | sl | pymes |
| fs-javier | 10 | Comunidad Propietarios Mirador | comunidad | general |
| fs-javier | 11 | F. Mora Construcciones | autonomo | general |
| fs-javier | 12 | Gastro Holding S.L. | sl | pymes |
| fs-javier | 13 | Bermúdez Asesores S.L. | sl | pymes |

Año ejercicio: 2025 por defecto (ajustar si hay datos históricos 2024 que migrar).

---

## API Tokens FS + Registro en SFCE BD

Cada instancia necesita un token API para que SFCE pueda llamarla.

**Generación**: Admin > API > Tokens en panel de cada instancia (o INSERT directo en MariaDB tabla `fs_api_access`).

**Registro en SFCE** (via endpoint ya implementado):
```
PUT /api/admin/gestorias/1/fs-credenciales
  { "fs_url": "https://fs-uralde.prometh-ai.es/api/3", "fs_token": "<TOKEN_URALDE>" }

PUT /api/admin/gestorias/2/fs-credenciales
  { "fs_url": "https://fs-gestoriaa.prometh-ai.es/api/3", "fs_token": "<TOKEN_GESTORIAA>" }

PUT /api/admin/gestorias/3/fs-credenciales
  { "fs_url": "https://fs-javier.prometh-ai.es/api/3", "fs_token": "<TOKEN_JAVIER>" }
```

Token se cifra con Fernet antes de guardar en BD. Nunca se expone en claro.

---

## DNS

Registros A en DonDominio (manual, panel web), apuntando a `65.108.60.69`:

```
fs-uralde.prometh-ai.es    A  65.108.60.69
fs-gestoriaa.prometh-ai.es A  65.108.60.69
fs-javier.prometh-ai.es    A  65.108.60.69
```

DNS debe estar propagado antes de ejecutar certbot.

---

## Backup

Añadir los 3 nuevos MariaDB al script `/opt/apps/sfce/backup_total.sh`. Actualmente cubre 6 PG + 2 MariaDB; hay que añadir 3 más.

---

## Consideraciones importantes

| Aspecto | Detalle |
|---------|---------|
| Docker image | Confirmar en servidor: `docker inspect <container_fs_actual> \| grep Image` |
| Setup wizard FS | Primera visita a cada nueva URL requiere completar wizard: DB config + admin user (password: `Uralde2026!`) |
| Plugins fiscales | Las nuevas instancias arrancan sin plugins. No necesarios para SFCE (genera modelos independientemente). Instalar solo si gestores los usan directamente. |
| Puertos disponibles | Verificar que 8010, 8011, 8012 no estén en uso: `ss -tlnp \| grep -E "801[012]"` |
| Acceso desde contabilidad.prometh-ai.es | `carloscanetegomez` en todas las instancias con nivel 99 para soporte superadmin |

---

## Orden de implementación

```
1. DNS (manual DonDominio) — PRIMERO, antes de todo
   ↓ esperar propagación DNS (~15 min)
2. Servidor SSH: verificar imagen Docker + puertos libres
3. Servidor: crear /opt/apps/fs-uralde/ + docker-compose.yml + .env + up -d
4. Servidor: crear /opt/apps/fs-gestoriaa/ + docker-compose.yml + .env + up -d
5. Servidor: crear /opt/apps/fs-javier/ + docker-compose.yml + .env + up -d
6. Web: completar setup wizard en cada instancia (http://65.108.60.69:8010/11/12)
7. Servidor: INSERT usuarios FS via docker exec + MariaDB
8. Web: Admin > API > Tokens → generar token por instancia
9. Servidor: nginx vhosts (3 archivos conf) + reload
10. Servidor: certbot SSL (3 dominios)
11. SFCE local: migración 025 (SQLite dev)
    → pytest tests/ (verificar sin regresiones)
12. SFCE prod: migración 025 via SSH psql
13. SFCE: registrar fs_url + tokens via endpoint admin (superadmin login)
14. Script: crear empresas en cada instancia (nuevo script parametrizado o 3 llamadas FsSetup)
15. Backup: añadir 3 MariaDB a backup_total.sh
16. Verificación: pipeline SFCE usa credenciales correctas por gestoría
```

---

## Verificación final

- [ ] `curl https://fs-uralde.prometh-ai.es/api/3/version` → responde con token
- [ ] `curl https://fs-gestoriaa.prometh-ai.es/api/3/version` → responde con token
- [ ] `curl https://fs-javier.prometh-ai.es/api/3/version` → responde con token
- [ ] Login sergio en fs-uralde solo ve empresas Uralde (no Gestoría A)
- [ ] Login gestor1 en fs-gestoriaa solo ve empresas Gestoría A
- [ ] Login javier en fs-javier solo ve empresas 10-13
- [ ] carloscanetegomez puede logear en las 3 instancias (nivel 99)
- [ ] `pytest tests/` pasa (migración 025 + roles)
- [ ] Pipeline SFCE empresa Marcos Ruiz usa `fs-gestoriaa.prometh-ai.es` (no instancia global)
