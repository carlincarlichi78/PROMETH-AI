# Tablero de Usuarios SFCE — Design

**Fecha**: 2026-03-01
**Estado**: Aprobado

## Visión

El sistema SFCE funciona como un tablero de juego por niveles. No se avanza al siguiente nivel hasta que el anterior está completamente controlado y probado de punta a punta. El objetivo final es que gestorías, gestores y clientes puedan "jugar" de forma autónoma — sin intervención manual del super-admin en cada paso.

---

## Jerarquía de usuarios

```
Super-admin
├── Gestoría A
│   ├── Admin gestoría
│   ├── Gestor 1 → Cliente X (empresa 1, empresa 2)
│   └── Gestor 2 → Cliente Y (empresa 3)
├── Gestoría B (asesor autónomo = gestoría de 1 persona)
│   └── Admin gestoría (= el asesor)
│       └── Cliente Z (empresa 4)
└── Clientes directos del super-admin (sin gestoría)
    └── Cliente Pastorino, Cliente Gerardo...
```

**Reglas:**
- Asesor autónomo = gestoría de 1 persona. Mismo modelo, sin gestores adicionales.
- Cliente = 1 cuenta, puede ver N empresas (su grupo económico).
- Empresa = 1 CIF = 1 entidad contable. Autónomo y S.L. del mismo dueño son dos clientes distintos.
- Grupo económico = agrupación de empresas bajo un mismo administrador. Vista comparativa futura.
- El cliente es **pasivo**: solo aporta documentación. El gestor y el sistema hacen todo lo demás.

**Roles en BD:**
`superadmin` | `admin_gestoria` | `asesor` | `asesor_independiente` | `cliente`

---

## El Tablero — 4 niveles

### Nivel 0 — Super-admin operativo (casilla de salida)

El árbitro del juego. Siempre puede hacer todo: crear gestorías, gestores, clientes, empresas, procesar documentos, ver toda la cartera.

**Estado actual:**
- API crear/listar gestorías: ✓ existe
- API invitar usuarios a gestoría: ✓ existe (genera token 7 días)
- UI gestorías en dashboard: ✗ no existe
- Clientes directos sin gestoría_id: ✗ modelo no lo contempla

**Resquicios a resolver:**

| ID | Resquicio | Descripción |
|----|-----------|-------------|
| R0-A | UI gestorías | Página en dashboard para crear, listar y gestionar gestorías |
| R0-B | Clientes directos | Super-admin puede crear clientes sin gestoría padre (gestoria_id=NULL) |

---

### Nivel 1 — La gestoría puede jugar

Super-admin crea gestoría → admin gestoría recibe acceso → entra al dashboard → crea y gestiona sus gestores.

**Estado actual:**
- Token de invitación: ✓ se genera
- Endpoint aceptar-invitación: ✗ no existe
- UI de gestión de gestores/clientes para admin_gestoria: ✗ no existe
- Servicio de email: ✗ no existe (el token se devuelve en JSON, hay que enviarlo manualmente)

**Resquicios a resolver:**

| ID | Resquicio | Descripción |
|----|-----------|-------------|
| R1-A | Endpoint aceptar-invitación | `POST /api/auth/aceptar-invitacion?token=xxx` — canjea token, establece password, activa cuenta |
| R1-B | UI panel gestoría | Dashboard para admin_gestoria: ver gestores, invitar gestores, ver clientes |
| R1-C | Servicio email | SMTP básico para enviar invitaciones automáticamente (no manual) |

---

### Nivel 2 — Alta de cliente con historia

El gestor recibe documentación del cliente → OCR la procesa → perfil fiscal pre-rellenado → gestor confirma → sistema carga historia contable → empresa lista.

**El cliente es pasivo**: solo envía documentos. No toca el sistema hasta el nivel 3.

**Documentos por tipo de cliente:**

| Tipo | Documentos mínimos | Datos extraíbles |
|------|-------------------|-----------------|
| Autónomo | Modelo 036/037 | NIF, nombre, domicilio, régimen IVA, epígrafe IAE, fecha alta |
| S.L. / S.A. | 036 societario + escritura o cert. RM | NIF, denominación, domicilio, objeto social, administradores |
| Comunidad de Bienes | 036 de cada comunero | NIFs, porcentajes |

**Documentos opcionales (enriquecen el perfil):**
- Modelo 303 → confirma régimen IVA real, periodicidad, intracomunitarias
- Modelo 100/200 → confirma módulos/directa, si tributa en IS
- Certificado AEAT al corriente → detecta deudas antes de aceptar

**Migración histórica (cuentas anuales + libros de IVA):**
- Libro facturas recibidas → proveedores habituales pre-cargados
- Libro facturas emitidas → clientes habituales pre-cargados
- Balance/cuentas anuales → saldos iniciales del ejercicio actual
- El MCF arranca con historia real: clasifica correctamente desde el primer día

**Estado actual:**
- OCR para FC/FV/NC/NOM/SUM/BAN/RLC/IMP: ✓ existe
- OCR para 036/037 y escrituras: ✗ no implementado
- Wizard empresa (5 pasos): ✓ existe (UI)
- FS setup automatizado (crear empresa + ejercicio + PGC): ✗ pendiente verificar
- Migración histórica (libros IVA + cuentas anuales): ✗ no existe

**Resquicios a resolver:**

| ID | Resquicio | Descripción |
|----|-----------|-------------|
| R2-A | OCR 036/037 | Parser para Modelo 036/037: extrae NIF, nombre, domicilio, régimen IVA, epígrafe, fecha alta |
| R2-B | OCR escrituras | Parser para escrituras de constitución: extrae denominación, NIF, objeto social, administradores |
| R2-C | FS setup auto | Automatizar: crear empresa en FS + crear ejercicio + importar PGC (hoy es manual) |
| R2-D | Migración histórica | Módulo para cargar libros de IVA (CSV/Excel/PDF) y cuentas anuales → proveedores, clientes, saldos iniciales |

---

### Nivel 3 — Cliente en su portal

Cuando el nivel 2 está completo, el cliente recibe acceso y ve sus datos reales. El cliente no hace nada técnico — solo consulta.

**Estado actual:**
- Portal UI (`portal-page.tsx`): ✓ existe (resumen + documentos + ical)
- API portal (`/api/portal/{id}/resumen` y `/documentos`): ✓ existe
- Portal multi-empresa (índice "mis empresas"): ✗ solo existe `/portal/:id` individual
- Flujo invitación rol cliente: ✗ depende de R1-A (mismo mecanismo)

**Resquicios a resolver:**

| ID | Resquicio | Descripción |
|----|-----------|-------------|
| R3-A | Portal índice | Pantalla `/portal` que lista todas las empresas del cliente y permite seleccionar |
| R3-B | Invitación cliente | Flujo para invitar al cliente final (mismo token que gestores, rol=cliente) |

---

## Resumen de todos los resquicios

| ID | Nivel | Bloqueante | Descripción corta |
|----|-------|-----------|-------------------|
| R0-A | 0 | Sí | UI gestorías en dashboard |
| R0-B | 0 | Parcial | Clientes directos sin gestoría |
| R1-A | 1 | Sí | Endpoint aceptar-invitación |
| R1-B | 1 | Sí | UI panel gestoría |
| R1-C | 1 | Parcial | Servicio email SMTP |
| R2-A | 2 | Sí | OCR Modelo 036/037 |
| R2-B | 2 | Parcial | OCR escrituras |
| R2-C | 2 | Sí | FS setup automatizado |
| R2-D | 2 | Sí | Migración histórica (libros + cuentas anuales) |
| R3-A | 3 | Sí | Portal multi-empresa (índice) |
| R3-B | 3 | Sí | Flujo invitación cliente |

---

## Principios de implementación

1. **No se avanza de nivel sin que el anterior funcione end-to-end.**
2. **El cliente es siempre pasivo.** Solo aporta documentos. El gestor y el sistema procesan.
3. **El super-admin siempre puede hacer todo**, independientemente del nivel en el que esté el resto.
4. **Un cliente = un acceso, N empresas.** El grupo económico es organización visual, se implementa después de los 4 niveles.
5. **La migración histórica no es opcional.** Sin historia, el sistema no clasifica bien y el cliente no ve valor desde el día 1.

---

## Fuera de alcance (próximas fases)

- Vista comparativa entre empresas del grupo económico
- Facturación / suscripciones por gestoría
- Subida de documentos nuevos por el cliente desde el portal
- App móvil para clientes
