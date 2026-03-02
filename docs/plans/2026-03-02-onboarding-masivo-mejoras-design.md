# Diseño: Onboarding Masivo — Mejoras UX + Flujo Guiado

**Fecha**: 2026-03-02
**Estado**: Aprobado
**Rama**: feat/onboarding-masivo-mejoras

---

## Problema

El formulario de Onboarding Masivo acepta cualquier documento ("ZIP, PDFs, CSVs, Excel — todo vale") pero internamente el sistema requiere un modelo 036/037 por empresa como documento base obligatorio. Sin él, el perfil queda bloqueado. El gestor no lo sabe hasta después de procesar el lote.

Además, no existe forma de recuperar un perfil bloqueado sin repetir el lote completo.

---

## Solución: 3 capas + 2 modos de entrada

### Capa A — Información preventiva
Mejorar el formulario ZIP para que sea explícito sobre los requisitos antes de subir.

### Capa B — Recuperación de perfiles bloqueados
Permitir añadir documentos a un perfil bloqueado sin repetir el lote.

### Capa C — Fusión automática con notificación
Cuando llega un 036 que corresponde a un perfil bloqueado, el sistema fusiona automáticamente y notifica al gestor.

---

## Arquitectura

Dos modos de entrada, un único pipeline de procesamiento:

```
Modo ZIP (mejorado)          Modo Guiado (nuevo)
      │                              │
      ▼                              ▼
 POST /api/onboarding/lotes    POST /api/onboarding/wizard/procesar
      │                              │
      └──────────┬───────────────────┘
                 ▼
        ProcesadorLote (sin cambios)
        MotorCreacion (sin cambios)
                 │
                 ▼
        BD: onboarding_lotes / onboarding_perfiles
```

El wizard construye el lote de forma incremental (estado `borrador`) antes de procesarlo. El resultado es idéntico para ambos modos.

---

## UI: Flujo ZIP mejorado

### Formulario de subida

- Texto del drop zone cambia a: "Organiza el ZIP con una carpeta por empresa"
- Acordeón colapsado "¿Qué documentos necesito?" con tres secciones:
  - **Obligatorio por empresa**: Modelo 036/037 (censo de empresarios)
  - **Recomendados**: 303, 390, 200, libros de facturas emitidas/recibidas, sumas y saldos
  - **Opcionales**: resto de modelos fiscales
- Botón secundario "Modo guiado →" junto al botón principal "Subir y procesar →"

### Perfiles bloqueados (Capa B)

Cada `PerfilRevisionCard` con estado `bloqueado` muestra:
- Badge rojo "Bloqueado" con motivo visible
- Botón "Añadir documentos" que expande un uploader inline
- El uploader llama a `POST /api/onboarding/perfiles/{id}/completar`
- Tras procesar, la tarjeta se actualiza con el nuevo estado sin recargar la página

### Notificaciones (Capa C)

- Badge en campana de notificaciones del AppHeader
- Texto según score resultante:
  - Score ≥85: "Perfil EMPRESA X creado automáticamente"
  - Score 60–84: "Perfil EMPRESA X desbloqueado — revisa antes de aprobar"
- Clic en notificación navega directamente al perfil

---

## UI: Flujo Guiado (wizard)

4 pasos con navegación libre hacia atrás sin pérdida de datos.

### Paso 1 — Subir modelos 036/037

- Drop zone exclusivo para 036/037
- Al subir cada archivo, clasificación inmediata (ligera, sin OCR completo)
- Feedback por archivo: ✅ reconocido con nombre+CIF detectado, ⚠️ no reconocido
- No se puede continuar con 0 archivos reconocidos

### Paso 2 — Revisar empresas detectadas

- Tabla: nombre, CIF, forma jurídica, territorio
- Advertencias visibles por empresa (ej: "Canarias — verificar IGIC vs IVA")
- Botón eliminar empresa del lote

### Paso 3 — Enriquecer (opcional)

- Una fila por empresa, expandible
- Drop zone por empresa para documentos adicionales (303, 390, libros, etc.)
- Botón "Saltar" para omitir el paso completo
- Tipos detectados mostrados por archivo subido

### Paso 4 — Confirmar y procesar

- Resumen: N empresas, documentos por empresa
- Input nombre del lote
- Botón "Procesar lote →" llama a `POST /api/onboarding/wizard/{lote_id}/procesar`
- Redirige a la pantalla de resultados estándar (idéntica para ambos modos)

---

## Backend

### Cambios en BD

```sql
-- onboarding_lotes: nueva columna
ALTER TABLE onboarding_lotes ADD COLUMN modo TEXT DEFAULT 'zip';
-- valores: 'zip' | 'wizard'
-- estado 'borrador' añadido para lotes wizard en construcción
```

### Endpoints nuevos

```
POST   /api/onboarding/wizard/iniciar
       → { lote_id, estado: "borrador" }

POST   /api/onboarding/wizard/{lote_id}/subir-036
       body: { archivo: File }
       → { nif, nombre, forma_juridica, territorio, advertencias[] }
       (clasificación + OCR 036 inmediato, sin persistir empresa aún)

DELETE /api/onboarding/wizard/{lote_id}/empresa/{nif}
       → elimina empresa del borrador

POST   /api/onboarding/wizard/{lote_id}/empresa/{nif}/documentos
       body: { archivos: File[] }
       → { documentos_añadidos[], tipos_detectados[] }

POST   /api/onboarding/wizard/{lote_id}/procesar
       body: { nombre: string }
       → 202 Accepted, procesa en background (igual que modo ZIP)

POST   /api/onboarding/perfiles/{perfil_id}/completar
       body: { archivos: File[] }
       → { nuevo_estado, score, bloqueos[], advertencias[] }
```

### Lógica fusión (Capa C)

`Acumulador.desde_perfil_existente(perfil)` — método nuevo que deserializa el JSON del perfil guardado y reconstruye el acumulador para continuar incorporando documentos.

```python
def completar_perfil(perfil_id, archivos, sesion):
    perfil = sesion.get(OnboardingPerfil, perfil_id)
    acum = Acumulador.desde_perfil_existente(perfil)

    for archivo in archivos:
        clf = clasificar_documento(archivo)
        datos = _extraer_datos(clf.tipo, archivo)
        acum.incorporar(clf.tipo.value, datos)

    nuevo_perfil = acum.obtener_perfil()
    resultado = Validador().validar(nuevo_perfil)

    perfil.datos_json = serializar(nuevo_perfil)
    perfil.confianza = resultado.score
    perfil.bloqueos_json = resultado.bloqueos
    perfil.estado = _calcular_estado(resultado)

    if resultado.score >= 60:
        _crear_notificacion(perfil, resultado)

    sesion.commit()
```

Detección automática de 036 suelto: si el CIF del 036 subido coincide con un perfil bloqueado del mismo lote, se fusiona aunque el endpoint llamado sea el de completar de otro perfil_id. Si no hay match → empresa nueva independiente.

---

## Testing

### Backend (~14 tests nuevos)

```
test_completar_perfil_bloqueado.py
  ✓ perfil bloqueado + 036 → estado "apto" (score ≥85)
  ✓ perfil bloqueado + 036 → estado "revisión" (score 60-84)
  ✓ perfil bloqueado + 036 con CIF distinto → error claro
  ✓ acumulador restaura datos previos correctamente
  ✓ notificación creada cuando score ≥60

test_wizard_onboarding.py
  ✓ iniciar lote wizard → estado "borrador"
  ✓ subir 036 válido → devuelve nif+nombre+forma_juridica
  ✓ subir archivo no-036 → advertencia "no reconocido"
  ✓ eliminar empresa del borrador
  ✓ añadir documentos extra a empresa
  ✓ procesar lote wizard → mismo resultado que modo ZIP equivalente
  ✓ procesar lote vacío → 400
  ✓ lote en borrador no aparece en listado hasta procesar
  ✓ procesar lote sin nombre → 422
```

### Frontend (~6 smoke tests)

```
  ✓ acordeón "¿Qué documentos necesito?" despliega contenido
  ✓ botón "Modo guiado" visible y navega al wizard
  ✓ wizard paso 1: 036 detectado muestra empresa con CIF
  ✓ wizard navegación atrás conserva archivos
  ✓ perfil bloqueado: botón "Añadir documentos" abre uploader inline
  ✓ notificación aparece tras fusión exitosa
```

**Total estimado: ~20 tests nuevos** sobre los 2530 existentes.

---

## Archivos afectados

### Backend
- `sfce/core/onboarding/perfil_empresa.py` — añadir `Acumulador.desde_perfil_existente()`
- `sfce/api/rutas/onboarding_masivo.py` — endpoint `completar` + endpoints wizard
- `sfce/db/migraciones/` — migración nueva columna `modo` en `onboarding_lotes`
- `tests/test_completar_perfil_bloqueado.py` — nuevo
- `tests/test_wizard_onboarding.py` — nuevo

### Frontend
- `dashboard/src/features/onboarding/onboarding-masivo-page.tsx` — acordeón + botón modo guiado
- `dashboard/src/features/onboarding/perfil-revision-card.tsx` — uploader inline bloqueados
- `dashboard/src/features/onboarding/wizard-onboarding-page.tsx` — nuevo (4 pasos)
- `dashboard/src/features/onboarding/wizard-paso1.tsx` — nuevo
- `dashboard/src/features/onboarding/wizard-paso2.tsx` — nuevo
- `dashboard/src/features/onboarding/wizard-paso3.tsx` — nuevo
- `dashboard/src/features/onboarding/wizard-paso4.tsx` — nuevo
- `dashboard/src/App.tsx` — ruta `/onboarding/wizard`
