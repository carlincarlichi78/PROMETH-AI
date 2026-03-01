# PROMETH-AI — Web Nueva: Design Document

**Fecha:** 2026-03-01
**Estado:** Aprobado — pendiente implementación
**Dominio:** prometh-ai.es (DNS propagación pendiente, nginx+SSL preparados)
**Source actual:** `spice-landing/` (React+Vite+Tailwind v4, se reutiliza la base)

---

## 1. Objetivo

Sustituir la landing de SPICE (muy técnica, sin orientación a venta) por una web multi-página de PROMETH-AI que:

- Tenga una **Cara A** comercial, hermosa y orientada a conversión
- Tenga **Caras B** técnicas con toda la profundidad del sistema (procesos, arquitectura, seguridad, sistemática)
- Presente **propuestas diferenciadas** según el perfil del visitante
- Capture leads y dirija a demo/contacto

---

## 2. Audiencias

| Perfil | Necesidad | Tono |
|--------|-----------|------|
| **Gestoría / Despacho** | Automatizar registro facturas, modelos fiscales, multi-cliente | Técnico-contable, eficiencia, ROI tiempo |
| **Asesor Fiscal** | Análisis económico-financiero + fiscal completo en tiempo real | Analítico, reporting, visión 360° |
| **Cliente Final** | Visibilidad de su negocio sin ser contable, propuestas variables | Simple, visual, beneficio claro |

---

## 3. Arquitectura del sitio

```
prometh-ai.es/
├── /                    → Home (Cara A) — conversión + selector de perfil
├── /gestorias           → Perfil gestoría: automatización contable
├── /asesores            → Perfil asesor: análisis económico-financiero
├── /clientes            → Perfil cliente final: visibilidad y propuestas
├── /como-funciona       → Pipeline técnico completo (todos los perfiles)
├── /seguridad           → Arquitectura seguridad, RGPD, cifrado, backups
└── /precios             → Planes por perfil + CTA
```

**Router**: React Router v6, rutas declarativas en `src/router.tsx`
**Navegación**: barra fija con las 6 rutas + botón "Solicitar demo" siempre visible
**Móvil**: menú hamburguesa, diseño mobile-first

---

## 4. Home — estructura

### 4.1 Hero (pantalla completa)
- Fondo oscuro con partículas de fuego/datos flotando animadas
- Logo PROMETH-AI (llama estilizada + wordmark)
- **Tagline**: *"Tu contabilidad, en piloto automático"*
- **Subtítulo**: *"IA que lee, contabiliza y presenta. Para gestorías, asesores y empresas."*
- CTA primario: *"Ver mi perfil"* (scroll suave al selector)
- Efecto glow ámbar animado

### 4.2 Selector de perfil (3 cards)
Cards grandes e interactivas, cada una enlaza a su página:

| Card | Icono | Título | Subtítulo |
|------|-------|--------|-----------|
| Gestoría | 🏢 | *"Automatiza tu despacho"* | Contabilidad de todos tus clientes sin intervención manual |
| Asesor Fiscal | 📊 | *"Análisis 360°"* | Económico, financiero y fiscal en tiempo real |
| Cliente Final | 👤 | *"Conoce tu negocio"* | Visibilidad y control sin ser experto contable |

### 4.3 Resultados reales (métricas animadas)
- 10h → 15 min/mes de trabajo manual
- 98% precisión OCR
- 28 modelos fiscales automatizados
- 1.793 tests pasando

### 4.4 Cómo funciona en 3 pasos
1. Subes o recibes el documento (email, drag & drop, escáner)
2. PROMETH-AI lo lee, clasifica y contabiliza con triple IA
3. Aparece en FacturaScripts + modelos fiscales generados

### 4.5 Screenshot hero del dashboard
Captura del dashboard principal (PyG / resumen empresa) en mockup de pantalla.
*(Pendiente: tomar screenshot del dashboard real)*

### 4.6 Seguridad en una línea
Enlace a `/seguridad`

### 4.7 Footer
Links a todas las páginas + email contacto + copyright

---

## 5. Páginas de perfil

### 5.1 `/gestorias`
- **Hero**: *"Tu despacho procesa 500 facturas al mes. PROMETH-AI las contabiliza solas."*
- Pain points: registro manual (10h/mes), plazos fiscales, errores de transcripción, formatos distintos
- Features destacadas:
  - Pipeline OCR 7 fases (triple IA: Mistral + GPT-4o + Gemini)
  - Multi-empresa con aislamiento de datos
  - 28 modelos fiscales generados automáticamente
  - Integración nativa con FacturaScripts
  - Motor de aprendizaje adaptativo
- Screenshot: dashboard multi-empresa / lista modelos fiscales generados
- CTA: *"Solicitar demo para mi despacho"*

### 5.2 `/asesores`
- **Hero**: *"Análisis económico-financiero en tiempo real. Sin exportar a Excel."*
- Pain points: reporting manual, datos dispersos, falta de visión financiera integrada
- Features destacadas:
  - PyG automático por período
  - Conciliación bancaria (Norma 43 + CaixaBank XLS)
  - Ratios y análisis financiero
  - Módulo fiscal completo (303, 111, 130, 347, 390...)
  - Dashboard con 16 módulos
- Screenshot: gráficos PyG + pantalla conciliación bancaria
- CTA: *"Ver demo de análisis financiero"*

### 5.3 `/clientes`
- **Hero**: *"Sabe exactamente cómo va tu negocio, sin ser contable."*
- Tono: simple, visual, beneficios concretos (no jerga técnica)
- Features destacadas:
  - Portal cliente con visibilidad de documentos
  - Alertas de vencimientos fiscales
  - Estado de facturas y pagos
  - Resumen financiero comprensible
- Propuestas variables: Básico / Completo / Premium (según necesidad)
- CTA: *"Hablar con un asesor"*

---

## 6. Páginas técnicas

### 6.1 `/como-funciona`
Contenido migrado y mejorado desde SPICE:
- Pipeline 7 fases con diagrama visual
- Triple OCR: Mistral (T0) → GPT-4o (T1) → Gemini (T2)
- Tipos de documento: FC, FV, NC, NOM, SUM, BAN, RLC, IMP
- Motor de aprendizaje adaptativo (6 estrategias, YAML auto-update)
- Jerarquía de reglas (6 niveles: normativa → PGC → perfil fiscal → negocio → cliente → aprendizaje)
- Clasificador de documentos
- Trazabilidad completa
- Integración FacturaScripts API
- Modelos fiscales: 28 modelos, MotorBOE, GeneradorPDF

### 6.2 `/seguridad`
- Arquitectura multi-tenant: aislamiento total por gestoría
- Autenticación: JWT + 2FA TOTP + lockout 5 intentos
- Rate limiting por IP/usuario
- RGPD: exportación completa en ZIP, tokens uso único
- Cifrado: TLS en tránsito, bcrypt passwords
- Backups: diarios 02:00, 6 PostgreSQL + 2 MariaDB + configs + SSL → Hetzner Helsinki. Retención 7d/4w/12m
- Firewall: ufw + DOCKER-USER chain
- Infraestructura: Hetzner Alemania, GDPR-compliant

### 6.3 `/precios`
- Tres columnas por perfil
- Precios: "Consultar" (hasta tener pricing definido)
- CTA por plan: *"Solicitar demo"* / *"Hablar con nosotros"*

---

## 7. Brand y visual

### Paleta de colores
```
--color-bg:        #0a0a0f    (fondo negro profundo)
--color-surface:   #111118    (cards, superficies)
--color-border:    #1e1e2e    (bordes sutiles)
--color-amber:     #f59e0b    (acento principal — fuego)
--color-orange:    #ea580c    (acento secundario — gradientes)
--color-text:      #f8fafc    (texto principal)
--color-muted:     #94a3b8    (texto secundario)
--color-red:       #ef4444    (errores, alertas)
```

### Tipografía
- Headings: **Space Grotesk** (700) — ya instalada
- Body: **Inter** (400/500/600) — ya instalada

### Elementos visuales
- Partículas de fuego/datos flotando animadas (hero)
- Cards con efecto glassmorphism + borde ámbar sutil
- Gradientes: `from-amber-500 to-orange-600`
- Glow effects en CTAs y elementos destacados
- Logo: llama SVG estilizada (evolución del logo SPICE) + wordmark "PROMETH-AI"
- Screenshots del dashboard en mockup de pantalla (añadir en iteración 2)

### Tono de copia
- Cara A (home + perfiles): profesional, directo, beneficios concretos. Sin jerga.
- Caras B (técnicas): preciso, completo, basado en hechos reales del sistema.

---

## 8. Stack técnico

```
spice-landing/ (renombrar a prometh-ai-web/)
├── src/
│   ├── router.tsx           → React Router v6 rutas
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Gestorias.tsx
│   │   ├── Asesores.tsx
│   │   ├── Clientes.tsx
│   │   ├── ComoFunciona.tsx
│   │   ├── Seguridad.tsx
│   │   └── Precios.tsx
│   ├── components/
│   │   ├── layout/          → Navbar, Footer
│   │   ├── home/            → Hero, SelectorPerfil, Metricas, Pasos
│   │   ├── gestorias/
│   │   ├── asesores/
│   │   ├── clientes/
│   │   ├── como-funciona/   → diagramas técnicos (migrar de SPICE)
│   │   └── shared/          → componentes reutilizables
│   └── styles/
│       └── tailwind.css     → variables brand + utilidades
├── public/
│   └── images/              → screenshots dashboard (añadir después)
└── package.json
```

**Dependencias nuevas**:
- `react-router-dom` v6 (navegación multi-página)
- Resto: igual que SPICE (Tailwind v4, Lucide, Vite)

---

## 9. Fases de implementación

| Fase | Contenido | Prioridad |
|------|-----------|-----------|
| 1 | Setup router + Navbar + Footer + brand tokens | Alta |
| 2 | Home completo (Hero + Selector + Métricas + Pasos) | Alta |
| 3 | `/gestorias` + `/asesores` + `/clientes` | Alta |
| 4 | `/como-funciona` (migrar diagramas de SPICE) | Media |
| 5 | `/seguridad` | Media |
| 6 | `/precios` | Media |
| 7 | Screenshots reales del dashboard | Baja (iteración 2) |
| 8 | Deploy en prometh-ai.es + SSL | Bloqueado por DNS propagación |

---

## 10. Deploy

**Servidor**: 65.108.60.69 (Hetzner)
**Ruta**: `/opt/apps/spice-landing/` → sustituir con build nuevo
**Nginx**: `/opt/infra/nginx/conf.d/prometh-ai.conf` (HTTP listo, SSL pendiente DNS)
**Build**: `npm run build` → copiar `dist/` a `/opt/apps/spice-landing/`
**SSL**: script auto-certbot corriendo en servidor, se ejecuta automáticamente cuando propague DNS
