# Diseño — App Móvil SFCE: Rediseño Home-First

**Fecha:** 2026-03-02
**Enfoque:** B — Home-first. Rediseñar la pantalla principal de cada rol como centro de mando, y construir las nuevas features desde ahí.
**Estado:** APROBADO

---

## Contexto

La app móvil actual (Expo SDK 54 + Expo Router v3) tiene las pantallas básicas implementadas pero carece de valor diferencial. El objetivo es convertirla en una herramienta útil a diario para dos perfiles muy distintos:

- **Cliente** (autónomo o empresario): quiere saber cuánto apartar para impuestos, si todo está en orden, y comunicarse con su gestor sin salir de la app.
- **Gestor/asesor**: quiere supervisar todos sus clientes de un vistazo, actuar sobre lo urgente, y no necesitar el ordenador para decisiones rápidas.

**Principio rector:** Móvil = visión rápida + acción inmediata. Web = detalle completo.

Una sola app, experiencia adaptada por rol al hacer login.

---

## Los 5 pilares

### 1. Ahorra X€ al mes

Traduce el IVA y el IRPF estimados del trimestre en un consejo mensual de ahorro. El cliente no necesita entender el 303 — solo sabe cuánto guardar cada mes.

**Cálculo:**
```
IVA neto Q actual = IVA cobrado en facturas - IVA pagado en compras
IRPF 130 estimado = resultado acumulado × tipo estimado (solo autónomos)
Meses restantes en el trimestre = 1, 2 o 3

Aparta al mes = (IVA neto + IRPF 130) / meses restantes
```

Basado en documentos ya registrados en BD. Se muestra con aviso: "basado en X facturas registradas hasta hoy".

**Ejemplo:**
> "Para no tener sorpresas en octubre, guarda **2.100€ al mes**
> IVA estimado Q3: 4.800€ · IRPF estimado Q3: 1.500€"

---

### 2. Semáforo fiscal por empresa

Estado inmediato sin necesidad de leer números.

| Color | Condición |
|-------|-----------|
| 🟢 Verde | Sin alertas, documentos al día |
| 🟡 Amarillo | Algo pendiente O vencimiento < 7 días |
| 🔴 Rojo | Vencimiento < 3 días, documentos rechazados, o resultado negativo importante |

---

### 3. Push notifications proactivas

La app habla primero. Máximo **4 notificaciones al día por empresa**. Silencio entre **22:00 y 8:00**.

**Para el cliente:**
| Cuándo | Mensaje |
|--------|---------|
| 10 días antes vencimiento (todo OK) | "El 303 de Q2 vence el 20 julio. Tu gestor ya tiene todo ✓" |
| 10 días antes vencimiento (faltan docs) | "Faltan 8 días para el 303. Aún no hemos recibido facturas de julio. ¿Las tienes?" |
| Documento rechazado | "Tu factura de Zara fue rechazada. Tu gestor te ha dejado un mensaje." |
| Mensaje nuevo del gestor | "Nuevo mensaje de Carlos sobre el 303 Q2" |
| Fin de mes | "Este mes aparta 580€ para tus impuestos" |

**Para el gestor:**
| Cuándo | Mensaje |
|--------|---------|
| Cliente sube documentos | "Marta Confecciones ha subido 3 documentos nuevos" |
| Documento en cuarentena | "Factura de Empresa C requiere revisión manual" |
| Vencimiento en 3 días | "🔴 303 de Empresa C vence en 2 días y no está presentado" |
| Cliente responde mensaje | "Marta ha respondido sobre la factura de Zara" |
| Onboarding pendiente | "Empresa B lleva 5 días sin completar el onboarding" |

El gestor puede configurar qué alertas recibe por cliente.

---

### 4. Comunicación contextual

Hilo de mensajes por empresa entre cliente y gestor. Cada mensaje puede ir ligado a un documento concreto o a un período fiscal.

**Flujo:**
- El gestor inicia un hilo desde un documento (cuarentena, rechazado) o desde el calendario fiscal
- El cliente ve el contexto inmediatamente — sabe de qué se habla sin buscar
- El cliente puede adjuntar foto enriquecida directamente desde el hilo
- Push notification al destinatario cuando hay mensaje nuevo

**Estructura de mensaje:**
```
[Contexto: Factura Zara · agosto 2025]  ← chip opcional
"Esta factura tiene el CIF incorrecto, ¿puedes resubirla?"
Gestor · 14:15
```

---

### 5. Foto enriquecida (mejora del flujo existente)

El flujo de tipo + campos adaptativos (Factura/Ticket/Nómina/Extracto/Otro + `ProveedorSelector`) se mantiene. Se añade:

1. **Nota libre para el gestor** — campo opcional para dar contexto humano
2. **Enlace al hilo de mensajes** — el documento llega como mensaje contextual, no solo como archivo en la cola del pipeline

---

## Pantallas

### Home cliente — 1 empresa

```
[Nombre empresa] [Ejercicio]

[SEMÁFORO grande con estado textual]

┌─ APARTA ESTE MES ──────────────┐
│  580€                          │
│  IVA Q2 estimado    1.240€     │
│  IRPF Q2 estimado     480€     │
│  Vence: 20 julio               │
└────────────────────────────────┘

⚠️ ALERTAS
· Falta factura de Zara (julio)

📄 ÚLTIMOS DOCUMENTOS
Factura Mango    · procesado  ✓
Factura H&M      · procesado  ✓
Ticket Primark   · revisión   ⏳

[+ Subir documento]  [💬 Mensajes]
```

### Home cliente — N empresas

```
Mis empresas          3 total

EMPRESA A        🟢  +142.000€
B78234512             sin alertas

EMPRESA B        🟡   +38.000€
A12345678          2 pendientes

EMPRESA C        🔴   -12.000€
C98765432        303 en 2 días
```
→ tap → entra al detalle con home de empresa única.

### Home gestor

Ordenado por urgencia: Rojo → Amarillo → Verde.

```
Mis clientes          8 total

🔴 URGENTE (2)

EMPRESA C        🔴
303 vence en 2 días · sin docs   [→]

MARTA CONFECCIONES  🔴
3 docs rechazados                [→]

🟡 REQUIEREN ATENCIÓN (3)
...

🟢 EN ORDEN (3)
...
```

### Detalle cliente (vista gestor)

Al entrar a un cliente desde la home del gestor:
- Semáforo + estado resumido
- Documentos pendientes de aprobación → aprobar/rechazar con un toque
- Alertas fiscales activas
- Hilo de mensajes contextuales
- Botón subir documento en nombre del cliente

---

## Lo que NO cambia

- Flujo de login y redirect por rol
- Pantallas existentes (documentos, notificaciones, perfil, alertas, onboarding)
- `ProveedorSelector` y campos adaptativos por tipo de documento
- Arquitectura: Expo Router, Zustand, TanStack Query, SecureStore

---

## Pendiente para iteraciones futuras

- Calendario fiscal visual en móvil
- Resultado neto proyectado a fin de año
- Comparativa trimestre actual vs trimestre anterior
- Configuración de alertas por cliente (gestor)
- Modo offline con datos en caché
