# PROMETH-AI — Guia de Producto

> **Publico:** Presentaciones comerciales, potenciales clientes, inversores
> **Actualizado:** 2026-03-01

---

## Que es PROMETH-AI?

Sistema SaaS de automatizacion contable y gestion fiscal para gestorias y empresas espanolas.
Procesa documentos fiscales (facturas, nominas, extractos bancarios) mediante IA con triple verificacion,
los registra automaticamente en contabilidad y gestiona todas las obligaciones fiscales.

Disenado para eliminar la entrada manual de datos: el profesional recibe un documento, el sistema
lo clasifica, extrae los datos, valida contra normativa BOE y registra el asiento contable sin
intervencion humana — con trazabilidad completa y auditoria RGPD.

---

## Capacidades clave

| Capacidad | Detalle |
|-----------|---------|
| OCR con triple verificacion | Mistral + GPT-4o + Gemini Flash — consenso automatico entre modelos |
| Clasificacion automatica | 8 tipos de documento, confianza por niveles, escalada progresiva |
| Registro contable automatico | Dual: software contable + BD local simultaneos |
| 28 modelos fiscales | BOE compliant, generacion automatica en texto y PDF |
| Calendario fiscal | iCal suscribible, vencimientos por forma juridica |
| Conciliacion bancaria | Norma 43 + XLS, match exacto y aproximado (tolerancia 1%) |
| Portal cliente | Acceso self-service con KPIs, documentos y calendario fiscal |
| Dashboard en tiempo real | WebSocket, 21 modulos, PWA instalable en movil y escritorio |
| Multi-gestoria | Arquitectura multi-tenant, aislamiento completo por gestoria |
| Seguridad empresarial | 2FA TOTP, rate limiting, lockout, export RGPD, audit log |
| Aprendizaje continuo | El sistema mejora con cada resolucion exitosa, sin reentrenamiento |
| Copiloto IA | Chat contextual con acceso a datos de la empresa en tiempo real |

---

## Para gestorias

PROMETH-AI esta disenado como plataforma multi-tenant: una gestoria puede gestionar todos sus
clientes desde un unico dashboard, con aislamiento completo entre empresas.

Cada empresa gestionada tiene su propio portal cliente con acceso self-service a sus documentos,
KPIs y calendario de obligaciones fiscales — reduciendo consultas de estado al gestor.

→ [13 — Dashboard: Los 21 Modulos](_temas/13-dashboard-modulos.md)
→ [02 — Arquitectura General SFCE](_temas/02-sfce-arquitectura.md)

## OCR con triple verificacion

El motor de OCR utiliza tres modelos de IA en cascada. Si el primer modelo (Mistral OCR3) extrae
los datos con alta confianza, el proceso termina. Si la confianza es baja, se activa un segundo
modelo (GPT-4o). Para documentos criticos o ambiguos, los tres modelos votan y el sistema
selecciona por consenso.

El resultado: tasa de error significativamente inferior a OCR tradicional, con coste optimizado
al usar el modelo mas caro solo cuando es necesario.

→ [05 — OCR e IA: Sistema de Tiers](_temas/05-ocr-ia-tiers.md)

## Motor de Reglas Contables

Las reglas contables siguen una jerarquia de 6 niveles: normativa BOE > Plan General Contable >
perfil fiscal de la empresa > sector de negocio > configuracion cliente > aprendizaje automatico.

Esto significa que el sistema aplica automaticamente las reglas correctas segun la forma juridica
(autonomo, S.L., S.A.), el regimen de IVA (general, recargo de equivalencia, simplificado) y el
territorio (peninsula, Canarias, Ceuta/Melilla) de cada empresa.

→ [06 — Motor de Reglas Contables](_temas/06-motor-reglas.md)

## 28 Modelos Fiscales

Generacion automatica de los modelos fiscales mas habituales directamente desde los datos
contabilizados: 303 (IVA trimestral), 111 (retenciones), 130 (IRPF autonomo), 347 (operaciones
relevantes), 390 (resumen anual IVA), 200 (Impuesto de Sociedades), y 22 modelos adicionales.

Los ficheros se generan en formato texto compatible con el sistema de presentacion telematica
de la AEAT, listos para subir directamente.

→ [15 — Modelos Fiscales](_temas/15-modelos-fiscales.md)

## Calendario Fiscal Inteligente

El sistema genera automaticamente el calendario de obligaciones fiscales de cada empresa segun
su forma juridica y regimen. El calendario es exportable como fichero `.ics` suscribible desde
Google Calendar, Apple Calendar o Outlook — los vencimientos aparecen directamente en el
calendario personal del gestor o del cliente.

→ [16 — Calendario Fiscal](_temas/16-calendario-fiscal.md)

## Conciliacion Bancaria Automatica

Importacion directa de extractos bancarios en Norma 43 (TXT) y formato XLS de CaixaBank.
El motor de conciliacion cruza automaticamente los movimientos bancarios con las facturas
registradas, con tolerancia del 1% para diferencias de redondeo y ventana de 2 dias para
desajustes de fecha de valor.

→ [19 — Modulo Bancario: Ingesta y Conciliacion](_temas/19-bancario.md)

## Portal Cliente

Cada empresa tiene acceso a un portal self-service donde puede consultar sus KPIs fiscales,
descargar documentos, revisar el estado de sus obligaciones y acceder a su calendario fiscal.
El acceso es independiente del dashboard de la gestoria, con autenticacion separada.

→ [13 — Dashboard: Los 21 Modulos](_temas/13-dashboard-modulos.md)

## Seguridad y Cumplimiento RGPD

Autenticacion con segundo factor (TOTP compatible con Google Authenticator), bloqueo tras intentos
fallidos, rate limiting por IP, log de auditoria inmutable de todas las acciones, y export de datos
personales en formato ZIP para cumplimiento RGPD.

Los datos de cada gestoria estan completamente aislados mediante arquitectura multi-tenant con
verificacion en cada request.

→ [22 — Seguridad: Auth, Rate Limiting, RGPD y Cifrado](_temas/22-seguridad.md)

## Integracion con Administraciones Publicas

Recepcion automatica de notificaciones de AEAT y Seguridad Social mediante integracion con
CertiGestor. Las notificaciones se registran en BD y se muestran en el dashboard con alertas
en tiempo real, evitando el riesgo de perder plazos de respuesta.

→ [21 — Certificados Digitales y Notificaciones AAPP](_temas/21-certificados-aapp.md)

## Copiloto IA

Chat integrado en el dashboard con contexto completo de la empresa activa: saldos por cuenta,
facturas pendientes de pago, estado de modelos fiscales, movimientos recientes. El gestor puede
preguntar en lenguaje natural y recibir respuestas basadas en datos reales.

→ [14 — Copiloto IA](_temas/14-copiloto-ia.md)

## Roadmap

Estado actual del producto y proximas funcionalidades en desarrollo.

→ [28 — Roadmap y Estado del Sistema](_temas/28-roadmap.md)
