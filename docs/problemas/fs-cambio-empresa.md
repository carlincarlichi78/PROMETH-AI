# Problema: FacturaScripts siempre muestra empresa por defecto (E-9881)

## Síntoma
Cualquier usuario que entra en una instancia FacturaScripts (fs-uralde, fs-gestoriaa, fs-javier)
ve la empresa por defecto del wizard (E-9881 / idempresa=1) en lugar de su empresa asignada.

## Instancias afectadas
| URL | Empresa correcta por defecto |
|-----|------------------------------|
| https://fs-uralde.prometh-ai.es | PASTORINO (idempresa=2) |
| https://fs-gestoriaa.prometh-ai.es | MARCOS RUIZ (idempresa=2) |
| https://fs-javier.prometh-ai.es | COMUNIDAD MIRADOR (idempresa=2) |

## Credenciales admin FS (para pruebas)
- Nick: `carloscanete` / Password: `Uralde2026!`

## Lo que se intentó (sin éxito vía BD)
1. `UPDATE users SET idempresa=2 WHERE nick='francisco'` → FS lo sobreescribe a 1 al hacer login
2. `UPDATE settings SET properties = JSON_SET(properties, '$.idempresa', '2')` → FS usa caché
3. Borrar sesiones PHP + reiniciar container → sigue igual
4. Borrar `MyFiles/Tmp/FileCache/tools-settings.cache` → ahora muestra `%company%` (sin resolver)

## Causa raíz identificada
En `Core/Model/User.php`:
```php
$this->idempresa = Tools::settings('default', 'idempresa', 1);
```
FS siempre fuerza la empresa del usuario al valor global de `settings.default.idempresa`.
Además cachea ese valor en `MyFiles/Tmp/FileCache/tools-settings.cache`.

Adicionalmente, `nombrecorto` estaba a NULL en todas las empresas → mostraba `%company%`
en lugar del nombre. Ya corregido en BD.

## Estado actual tras los fixes de BD
- `settings.default.idempresa = "2"` en las 3 instancias (MariaDB)
- `nombrecorto` rellenado en todas las empresas
- Caché `tools-settings.cache` borrada

## ✅ RESUELTO (sesión 54)

El problema tenía 4 causas encadenadas:

1. **Wizard bloqueado**: `users.homepage='Wizard'` → fix: `UPDATE users SET homepage=NULL`
2. **Dinamic/ vacía**: menú no aparecía → fix: `AdminPlugins → Reconstruir`
3. **settings.default.idempresa=1**: empresa E-9881 → fix: UPDATE MariaDB + borrar caché + confirmar en `EditSettings`
4. **nombrecorto=NULL**: mostraba `%company%` → fix: `UPDATE empresas SET nombrecorto='NOMBRE'`

### Estado final

| Instancia | Empresa activa | Menú |
|-----------|---------------|------|
| fs-uralde | PASTORINO (idempresa=2) ✅ | Completo ✅ |
| fs-gestoriaa | MARCOS (idempresa=2) ✅ | Completo ✅ |
| fs-javier | COMUNIDAD (idempresa=2) ✅ | Completo ✅ |

### Cómo cambiar empresa activa

`Administrador → Panel de control` (`/EditSettings`) → dropdown "Empresa" → Guardar
(NO existe `/EditAppProperties` en esta versión de FS)

**Documentación completa**: `docs/LIBRO/_temas/24-facturascripts.md` → sección "Problemas frecuentes en instancias nuevas"

### URLs directas a probar
- `https://fs-uralde.prometh-ai.es/EditAppProperties` → buscar campo "Empresa"
- `https://fs-uralde.prometh-ai.es/ListEmpresa`
- `https://fs-uralde.prometh-ai.es/EditEmpresa?code=2`

## Empresas por instancia
### fs-uralde (idempresa default → 2)
| idempresa | nombre | nombrecorto |
|-----------|--------|-------------|
| 2 | PASTORINO COSTA DEL SOL S.L. | PASTORINO |
| 3 | GERARDO GONZALEZ CALLEJON | GERARDO |
| 4 | CHIRINGUITO SOL Y ARENA S.L. | CHIRINGUITO |
| 5 | ELENA NAVARRO PRECIADOS | ELENA |

### fs-gestoriaa (idempresa default → 2)
| idempresa | nombre | nombrecorto |
|-----------|--------|-------------|
| 2 | MARCOS RUIZ DELGADO | MARCOS |
| 3 | RESTAURANTE LA MAREA S.L. | LA MAREA |
| 4 | AURORA DIGITAL S.L. | AURORA |
| 5 | CATERING COSTA S.L. | CATERING |
| 6 | DISTRIBUCIONES LEVANTE S.L. | DISTRIB |

### fs-javier (idempresa default → 2)
| idempresa | nombre | nombrecorto |
|-----------|--------|-------------|
| 2 | COMUNIDAD MIRADOR DEL MAR | COMUNIDAD |
| 3 | FRANCISCO MORA | FRANMORA |
| 4 | GASTRO HOLDING S.L. | GASTRO |
| 5 | JOSE ANTONIO BERMUDEZ | BERMUDEZ |
