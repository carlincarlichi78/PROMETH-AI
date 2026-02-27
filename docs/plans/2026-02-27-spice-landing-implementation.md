# SPICE Landing Page — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Landing page de presentacion comercial de SPICE con 16 secciones y 8 diagramas SVG interactivos, optimizada para movil.

**Architecture:** SPA React single-page con scroll continuo. 17 componentes (1 por seccion + Navbar). Datos en archivos TS separados. SVGs inline con animaciones CSS. Hooks custom para IntersectionObserver y countUp. Sin router (una sola pagina).

**Tech Stack:** React 19 + TypeScript + Vite 7 + Tailwind CSS v4 (@tailwindcss/vite) + Lucide React

**Design doc:** `docs/plans/2026-02-27-spice-landing-design.md`

---

### Task 1: Scaffold proyecto

**Files:**
- Create: `spice-landing/package.json`
- Create: `spice-landing/vite.config.ts`
- Create: `spice-landing/tsconfig.json`
- Create: `spice-landing/tsconfig.app.json`
- Create: `spice-landing/tsconfig.node.json`
- Create: `spice-landing/eslint.config.js`
- Create: `spice-landing/index.html`
- Create: `spice-landing/src/main.tsx`
- Create: `spice-landing/src/App.tsx`
- Create: `spice-landing/src/index.css`
- Create: `spice-landing/src/vite-env.d.ts`
- Create: `spice-landing/public/favicon.svg`

**Step 1: Crear directorio y package.json**

```json
{
  "name": "spice-landing",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "lucide-react": "^0.575.0",
    "react": "^19.2.0",
    "react-dom": "^19.2.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.1",
    "@tailwindcss/vite": "^4.2.1",
    "@types/node": "^24.10.1",
    "@types/react": "^19.2.7",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^5.1.1",
    "eslint": "^9.39.1",
    "eslint-plugin-react-hooks": "^7.0.1",
    "eslint-plugin-react-refresh": "^0.4.24",
    "globals": "^16.5.0",
    "tailwindcss": "^4.2.1",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.48.0",
    "vite": "^7.3.1"
  }
}
```

**Step 2: Crear configs (vite, tsconfig, eslint)**

`vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5180,
    host: true,
  },
})
```

`tsconfig.json`:
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

`tsconfig.app.json`:
```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "types": ["vite/client"],
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}
```

`tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "types": ["node"],
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["vite.config.ts"]
}
```

`eslint.config.js`:
```javascript
import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
])
```

**Step 3: Crear index.html, main.tsx, App.tsx, index.css, vite-env.d.ts**

`index.html`:
```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="SPICE — Sistema Profesional Inteligente de Contabilidad Evolutiva. Automatizacion contable con IA." />
    <title>SPICE | Contabilidad Inteligente</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`src/index.css` — tema SPICE con Tailwind v4 syntax:
```css
@import "tailwindcss";

@theme {
  --color-spice-bg: #0a1628;
  --color-spice-bg-alt: #0d2818;
  --color-spice-emerald: #10b981;
  --color-spice-emerald-light: #34d399;
  --color-spice-emerald-dark: #059669;
  --color-spice-gold: #d4a017;
  --color-spice-gold-light: #f0c040;
  --color-spice-text: #f1f5f9;
  --color-spice-text-muted: #94a3b8;
  --color-spice-card: rgba(255, 255, 255, 0.05);
  --color-spice-border: rgba(255, 255, 255, 0.1);
  --color-spice-red: #ef4444;

  --font-heading: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
}

@layer base {
  html {
    scroll-behavior: smooth;
  }
  body {
    font-family: var(--font-body);
    background-color: var(--color-spice-bg);
    color: var(--color-spice-text);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-heading);
  }
}
```

`src/vite-env.d.ts`:
```typescript
/// <reference types="vite/client" />
```

`src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

`src/App.tsx` (placeholder con todas las secciones importadas pero vacias):
```tsx
export default function App() {
  return (
    <main className="min-h-screen">
      <p className="text-spice-emerald text-center pt-20 text-2xl">SPICE — en construccion</p>
    </main>
  )
}
```

`public/favicon.svg` — icono llama esmeralda:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <path d="M16 2c0 0-6 8-6 16s3 12 6 12 6-4 6-12S16 2 16 2z" fill="#10b981"/>
  <path d="M16 10c0 0-3 4-3 10s1.5 8 3 8 3-2 3-8-3-10-3-10z" fill="#d4a017"/>
</svg>
```

**Step 4: npm install**

Run: `cd spice-landing && npm install`

**Step 5: Verificar que compila**

Run: `cd spice-landing && npm run build`
Expected: Build exitoso sin errores

**Step 6: Commit**

```bash
git add spice-landing/
git commit -m "feat: scaffold proyecto SPICE landing — React 19 + Vite 7 + Tailwind v4 + TS"
```

---

### Task 2: Hooks custom + datos

**Files:**
- Create: `spice-landing/src/hooks/useInView.ts`
- Create: `spice-landing/src/hooks/useCountUp.ts`
- Create: `spice-landing/src/data/metricas.ts`
- Create: `spice-landing/src/data/tiposDocumento.ts`
- Create: `spice-landing/src/data/modelosFiscales.ts`
- Create: `spice-landing/src/data/formasJuridicas.ts`
- Create: `spice-landing/src/data/territorios.ts`
- Create: `spice-landing/src/data/pipeline.ts`

**Step 1: Crear useInView**

Hook que usa IntersectionObserver para detectar cuando un elemento entra en viewport (para animaciones on-scroll):

```typescript
import { useEffect, useRef, useState } from 'react'

export function useInView(opciones?: IntersectionObserverInit) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.unobserve(el)
        }
      },
      { threshold: 0.15, ...opciones }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [opciones])

  return { ref, visible }
}
```

**Step 2: Crear useCountUp**

Hook para animar numeros de 0 al valor final:

```typescript
import { useEffect, useState } from 'react'

export function useCountUp(objetivo: number, activo: boolean, duracion = 1500) {
  const [valor, setValor] = useState(0)

  useEffect(() => {
    if (!activo) return

    const inicio = performance.now()
    let frame: number

    const animar = (ahora: number) => {
      const progreso = Math.min((ahora - inicio) / duracion, 1)
      const eased = 1 - Math.pow(1 - progreso, 3)
      setValor(Math.round(eased * objetivo))

      if (progreso < 1) {
        frame = requestAnimationFrame(animar)
      }
    }

    frame = requestAnimationFrame(animar)
    return () => cancelAnimationFrame(frame)
  }, [objetivo, activo, duracion])

  return valor
}
```

**Step 3: Crear archivos de datos**

`data/metricas.ts`:
```typescript
export const metricas = [
  { valor: 99, sufijo: '%', etiqueta: 'precision en lectura' },
  { valor: 7, sufijo: '', etiqueta: 'pasos de verificacion' },
  { valor: 10, sufijo: '', etiqueta: 'tipos de documento' },
  { valor: 5, sufijo: '', etiqueta: 'territorios fiscales' },
  { valor: 11, sufijo: '', etiqueta: 'modelos fiscales automaticos' },
  { valor: 13, sufijo: '', etiqueta: 'formas juridicas soportadas' },
]

export const resultados = [
  { valor: '104/105', etiqueta: 'documentos contabilizados sin intervencion (99%)' },
  { valor: '127.807,44', etiqueta: 'EUR de balance cuadrado al centimo' },
  { valor: '3.138,14', etiqueta: 'EUR de liquidacion IVA identica al calculo manual' },
  { valor: '8/8', etiqueta: 'errores inyectados a proposito y detectados (100%)' },
  { valor: '189', etiqueta: 'pruebas automaticas de verificacion' },
  { valor: '2.343', etiqueta: 'documentos de prueba generados' },
]
```

`data/pipeline.ts`:
```typescript
export interface FasePipeline {
  numero: number
  nombre: string
  descripcion: string
  detalle: string
  datoClave: string
  icono: string
}

export const fases: FasePipeline[] = [
  {
    numero: 1,
    nombre: 'LECTURA',
    descripcion: 'Lectura inteligente del documento',
    detalle: 'Tres motores de inteligencia artificial leen cada documento y extraen todos los datos: emisor, CIF, fecha, base imponible, tipo de IVA, total, concepto y lineas de detalle.',
    datoClave: '15+ datos extraidos',
    icono: 'scan',
  },
  {
    numero: 2,
    nombre: 'COMPROBACIONES',
    descripcion: '9 verificaciones previas',
    detalle: 'Antes de contabilizar, se verifica: formato del CIF, cuadre aritmetico (base + IVA = total), que no sea duplicado, que la fecha este dentro del ejercicio y que el proveedor este dado de alta.',
    datoClave: '9 verificaciones',
    icono: 'shield-check',
  },
  {
    numero: 3,
    nombre: 'REGISTRO',
    descripcion: 'Contabilizacion automatica',
    detalle: 'Crea el apunte contable en el programa de gestion. Si algo falla (proveedor desconocido, subcuenta inexistente...), intenta resolverlo automaticamente antes de pedir ayuda al gestor.',
    datoClave: '6 estrategias de resolucion',
    icono: 'file-plus',
  },
  {
    numero: 4,
    nombre: 'VERIFICACION',
    descripcion: 'Comprobacion del asiento',
    detalle: 'Verifica que el asiento generado es correcto: que las partidas estan en el debe y haber correspondientes, que las subcuentas son las adecuadas y que los importes coinciden.',
    datoClave: 'Verificacion completa',
    icono: 'book-open',
  },
  {
    numero: 5,
    nombre: 'CORRECCION',
    descripcion: '7 correcciones automaticas',
    detalle: 'Convierte divisas extranjeras a euros, reclasifica suplidos aduaneros (de gasto a HP deudora), invierte notas de credito, genera autorepercusion en intracomunitarias y corrige subcuentas.',
    datoClave: '7 tipos de correccion',
    icono: 'wrench',
  },
  {
    numero: 6,
    nombre: 'COMPROBACION GLOBAL',
    descripcion: '13 verificaciones cruzadas',
    detalle: 'Verifica que el balance cuadra, que el IVA repercutido coincide con las facturas emitidas, que el IVA soportado coincide con las recibidas, coherencia con modelo 347, y revision adicional por IA.',
    datoClave: '13 verificaciones + auditoria IA',
    icono: 'check-circle',
  },
  {
    numero: 7,
    nombre: 'RESULTADO',
    descripcion: 'Libros contables e informes',
    detalle: 'Genera el libro diario en Excel, los datos para los modelos fiscales, y un informe de auditoria completo con el indice de fiabilidad.',
    datoClave: 'Todo documentado',
    icono: 'file-output',
  },
]
```

`data/tiposDocumento.ts`:
```typescript
export interface TipoDocumento {
  codigo: string
  nombre: string
  descripcion: string
  asiento: string
  ejemplo: {
    concepto: string
    partidas: { subcuenta: string; nombre: string; debe?: number; haber?: number }[]
  }
  grupo: 'factura' | 'otro'
}

export const tiposDocumento: TipoDocumento[] = [
  {
    codigo: 'FC',
    nombre: 'Factura compra',
    descripcion: 'Facturas recibidas de proveedores',
    asiento: '6xx+472 @ 400',
    ejemplo: {
      concepto: 'Compra material oficina — 1.210 EUR',
      partidas: [
        { subcuenta: '629', nombre: 'Otros servicios', debe: 1000 },
        { subcuenta: '472', nombre: 'IVA soportado 21%', debe: 210 },
        { subcuenta: '400', nombre: 'Proveedor', haber: 1210 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'FV',
    nombre: 'Factura venta',
    descripcion: 'Facturas emitidas a clientes',
    asiento: '430 @ 7xx+477',
    ejemplo: {
      concepto: 'Prestacion servicios — 2.420 EUR',
      partidas: [
        { subcuenta: '430', nombre: 'Cliente', debe: 2420 },
        { subcuenta: '705', nombre: 'Prestacion servicios', haber: 2000 },
        { subcuenta: '477', nombre: 'IVA repercutido 21%', haber: 420 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'NC',
    nombre: 'Nota credito',
    descripcion: 'Abono o devolucion parcial',
    asiento: 'Inverso de FC/FV',
    ejemplo: {
      concepto: 'Abono parcial — 242 EUR',
      partidas: [
        { subcuenta: '400', nombre: 'Proveedor', debe: 242 },
        { subcuenta: '629', nombre: 'Otros servicios', haber: 200 },
        { subcuenta: '472', nombre: 'IVA soportado', haber: 42 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'ANT',
    nombre: 'Anticipo',
    descripcion: 'Pago anticipado a proveedor',
    asiento: '407 @ 572',
    ejemplo: {
      concepto: 'Anticipo proveedor — 500 EUR',
      partidas: [
        { subcuenta: '407', nombre: 'Anticipos proveedores', debe: 500 },
        { subcuenta: '572', nombre: 'Bancos', haber: 500 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'REC',
    nombre: 'Recargo equivalencia',
    descripcion: 'Factura con recargo de equivalencia',
    asiento: '6xx+472+472RE @ 400',
    ejemplo: {
      concepto: 'Compra mercaderia RE — 1.262 EUR',
      partidas: [
        { subcuenta: '600', nombre: 'Compras', debe: 1000 },
        { subcuenta: '472', nombre: 'IVA soportado 21%', debe: 210 },
        { subcuenta: '472', nombre: 'Recargo equiv. 5.2%', debe: 52 },
        { subcuenta: '400', nombre: 'Proveedor', haber: 1262 },
      ],
    },
    grupo: 'factura',
  },
  {
    codigo: 'NOM',
    nombre: 'Nomina',
    descripcion: 'Nominas de empleados',
    asiento: '640+642 @ 476+4751+572',
    ejemplo: {
      concepto: 'Nomina enero — 2.500 EUR bruto',
      partidas: [
        { subcuenta: '640', nombre: 'Sueldos y salarios', debe: 2500 },
        { subcuenta: '642', nombre: 'SS empresa', debe: 750 },
        { subcuenta: '476', nombre: 'SS acreedora', haber: 908 },
        { subcuenta: '4751', nombre: 'IRPF retenciones', haber: 375 },
        { subcuenta: '572', nombre: 'Bancos (neto)', haber: 1967 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'SUM',
    nombre: 'Suministro',
    descripcion: 'Luz, agua, gas, telefono',
    asiento: '628+472 @ 410',
    ejemplo: {
      concepto: 'Factura electrica — 181.50 EUR',
      partidas: [
        { subcuenta: '628', nombre: 'Suministros', debe: 150 },
        { subcuenta: '472', nombre: 'IVA soportado 21%', debe: 31.50 },
        { subcuenta: '410', nombre: 'Acreedor', haber: 181.50 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'BAN',
    nombre: 'Bancario',
    descripcion: 'Comisiones y movimientos bancarios',
    asiento: '626/662 @ 572',
    ejemplo: {
      concepto: 'Comision mantenimiento — 15 EUR',
      partidas: [
        { subcuenta: '626', nombre: 'Servicios bancarios', debe: 15 },
        { subcuenta: '572', nombre: 'Bancos', haber: 15 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'RLC',
    nombre: 'Seguridad Social',
    descripcion: 'Recibos liquidacion cotizaciones',
    asiento: '642 @ 476',
    ejemplo: {
      concepto: 'Cuota SS autonomo — 294 EUR',
      partidas: [
        { subcuenta: '642', nombre: 'SS a cargo empresa', debe: 294 },
        { subcuenta: '476', nombre: 'SS acreedora', haber: 294 },
      ],
    },
    grupo: 'otro',
  },
  {
    codigo: 'IMP',
    nombre: 'Impuestos y tasas',
    descripcion: 'IBI, IAE, tasas municipales',
    asiento: '631 @ 572',
    ejemplo: {
      concepto: 'IBI local comercial — 450 EUR',
      partidas: [
        { subcuenta: '631', nombre: 'Otros tributos', debe: 450 },
        { subcuenta: '572', nombre: 'Bancos', haber: 450 },
      ],
    },
    grupo: 'otro',
  },
]
```

`data/modelosFiscales.ts`:
```typescript
export interface ModeloFiscal {
  modelo: string
  nombre: string
  periodicidad: string
  quien: string
  categoria: 'automatico' | 'semi' | 'asistido'
  descripcionCorta: string
}

export const modelosFiscales: ModeloFiscal[] = [
  { modelo: '303', nombre: 'IVA', periodicidad: 'Trimestral', quien: 'Todos (peninsula)', categoria: 'automatico', descripcionCorta: 'Liquidacion IVA: repercutido - soportado' },
  { modelo: '420', nombre: 'IGIC', periodicidad: 'Trimestral', quien: 'Canarias', categoria: 'automatico', descripcionCorta: 'Equivalente al 303 para Canarias' },
  { modelo: '390', nombre: 'Resumen anual IVA', periodicidad: 'Anual', quien: 'Todos', categoria: 'automatico', descripcionCorta: 'Resumen de los 4 trimestres de IVA' },
  { modelo: '111', nombre: 'Retenciones IRPF', periodicidad: 'Trimestral', quien: 'Con retencion', categoria: 'automatico', descripcionCorta: 'Retenciones practicadas a profesionales' },
  { modelo: '190', nombre: 'Resumen retenciones', periodicidad: 'Anual', quien: 'Con retencion', categoria: 'automatico', descripcionCorta: 'Resumen anual del 111' },
  { modelo: '115', nombre: 'Ret. alquileres', periodicidad: 'Trimestral', quien: 'Con alquiler', categoria: 'automatico', descripcionCorta: 'Retenciones sobre alquileres' },
  { modelo: '180', nombre: 'Resumen ret. alq.', periodicidad: 'Anual', quien: 'Con alquiler', categoria: 'automatico', descripcionCorta: 'Resumen anual del 115' },
  { modelo: '130', nombre: 'Pago fracc. IRPF', periodicidad: 'Trimestral', quien: 'Autonomos directa', categoria: 'automatico', descripcionCorta: '20% del rendimiento neto trimestral' },
  { modelo: '131', nombre: 'IRPF modulos', periodicidad: 'Trimestral', quien: 'Autonomos objetiva', categoria: 'automatico', descripcionCorta: 'Cuotas segun indices de actividad' },
  { modelo: '347', nombre: 'Operaciones terceros', periodicidad: 'Anual', quien: 'Todos >3.005 EUR', categoria: 'automatico', descripcionCorta: 'Operaciones >3.005,06 EUR con mismo tercero' },
  { modelo: '349', nombre: 'Intracomunitarias', periodicidad: 'Trimestral', quien: 'Intra-UE', categoria: 'automatico', descripcionCorta: 'Operaciones intracomunitarias' },
  { modelo: '200', nombre: 'Impuesto Sociedades', periodicidad: 'Anual', quien: 'S.L. / S.A.', categoria: 'semi', descripcionCorta: 'SPICE pre-rellena resultado contable. Gestor completa ajustes extracontables.' },
  { modelo: '202', nombre: 'Pago fracc. IS', periodicidad: 'Trimestral', quien: 'S.L. / S.A.', categoria: 'semi', descripcionCorta: '18% del ultimo IS. SPICE calcula, gestor valida.' },
  { modelo: 'CC.AA.', nombre: 'Cuentas anuales', periodicidad: 'Anual', quien: 'Juridicas', categoria: 'semi', descripcionCorta: 'Balance, PyG, memoria basica auto. Informe gestion manual.' },
  { modelo: '100', nombre: 'IRPF', periodicidad: 'Anual', quien: 'Personas fisicas', categoria: 'asistido', descripcionCorta: 'SPICE aporta rendimientos actividad economica. Gestor completa en Renta Web.' },
]
```

`data/territorios.ts`:
```typescript
export interface Territorio {
  id: string
  nombre: string
  impuesto: string
  tipos: { nombre: string; pct: number }[]
  is: string
  color: string
  modelos: string
}

export const territorios: Territorio[] = [
  {
    id: 'peninsula',
    nombre: 'Peninsula + Baleares',
    impuesto: 'IVA',
    tipos: [
      { nombre: 'General', pct: 21 },
      { nombre: 'Reducido', pct: 10 },
      { nombre: 'Superreducido', pct: 4 },
    ],
    is: '25% general / 23% pymes / 15% nueva creacion',
    color: '#10b981',
    modelos: '303, 390, 111, 130, 347',
  },
  {
    id: 'canarias',
    nombre: 'Canarias',
    impuesto: 'IGIC',
    tipos: [
      { nombre: 'General', pct: 7 },
      { nombre: 'Reducido', pct: 3 },
      { nombre: 'Tipo cero', pct: 0 },
      { nombre: 'Incrementado', pct: 9.5 },
      { nombre: 'Especial', pct: 15 },
    ],
    is: '25% general / 23% pymes / 15% nueva creacion',
    color: '#d4a017',
    modelos: '420 (equiv. 303), 390, 347',
  },
  {
    id: 'ceuta',
    nombre: 'Ceuta y Melilla',
    impuesto: 'IPSI',
    tipos: [
      { nombre: 'Tipo 1', pct: 0.5 },
      { nombre: 'Tipo 4', pct: 4 },
      { nombre: 'Tipo 8', pct: 8 },
      { nombre: 'Tipo 10', pct: 10 },
    ],
    is: '25% con bonificacion 50%',
    color: '#06b6d4',
    modelos: 'IPSI propio, 347',
  },
  {
    id: 'navarra',
    nombre: 'Navarra',
    impuesto: 'IVA (foral)',
    tipos: [
      { nombre: 'General', pct: 21 },
      { nombre: 'Reducido', pct: 10 },
      { nombre: 'Superreducido', pct: 4 },
    ],
    is: '28% general / 23% pequena / 20% micro',
    color: '#8b5cf6',
    modelos: '303 foral, 390, 347',
  },
  {
    id: 'pais_vasco',
    nombre: 'Pais Vasco',
    impuesto: 'IVA (foral)',
    tipos: [
      { nombre: 'General', pct: 21 },
      { nombre: 'Reducido', pct: 10 },
      { nombre: 'Superreducido', pct: 4 },
    ],
    is: '24% general / 22% pequena / 20% micro',
    color: '#f97316',
    modelos: '303 foral, 390, 347',
  },
]
```

`data/formasJuridicas.ts`:
```typescript
export interface FormaJuridica {
  id: string
  nombre: string
  tipo: 'fisica' | 'juridica'
  modelos: string[]
  particularidades: string
  regimen: string
}

export const formasJuridicas: FormaJuridica[] = [
  { id: 'autonomo', nombre: 'Autonomo persona fisica', tipo: 'fisica', modelos: ['303','130','390','347','100'], particularidades: '6 regimenes IRPF + 3 de IVA', regimen: 'IRPF directa/objetiva + IVA general/simplificado/RE' },
  { id: 'profesional', nombre: 'Profesional con retencion', tipo: 'fisica', modelos: ['303','130','111','190','390','347','100'], particularidades: 'Retencion 15% en facturas emitidas', regimen: 'IRPF directa + IVA general' },
  { id: 'sl', nombre: 'Sociedad Limitada (S.L.)', tipo: 'juridica', modelos: ['303','111','190','200','202','390','347'], particularidades: 'IS 25%, cuentas anuales RM', regimen: 'IS + IVA general' },
  { id: 'slu', nombre: 'S.L. Unipersonal', tipo: 'juridica', modelos: ['303','111','190','200','202','390','347'], particularidades: 'Igual que SL, socio unico', regimen: 'IS + IVA general' },
  { id: 'sa', nombre: 'Sociedad Anonima (S.A.)', tipo: 'juridica', modelos: ['303','111','190','200','202','390','347'], particularidades: 'IS 25%, auditoria si grande', regimen: 'IS + IVA general' },
  { id: 'sll', nombre: 'Sociedad Laboral', tipo: 'juridica', modelos: ['303','111','200','390','347'], particularidades: 'Mayoria capital en trabajadores', regimen: 'IS + IVA general' },
  { id: 'cb', nombre: 'Comunidad de Bienes', tipo: 'fisica', modelos: ['303','130','390','347','100'], particularidades: 'Tributa en IRPF de los comuneros', regimen: 'IRPF atribucion rentas + IVA' },
  { id: 'scp', nombre: 'Sociedad Civil Particular', tipo: 'fisica', modelos: ['303','130','390','347','100'], particularidades: 'Transparencia fiscal', regimen: 'IRPF atribucion rentas + IVA' },
  { id: 'cooperativa', nombre: 'Cooperativa', tipo: 'juridica', modelos: ['303','111','200','390','347'], particularidades: 'IS 20%, SS regimen especial', regimen: 'IS cooperativas + IVA' },
  { id: 'asociacion', nombre: 'Asociacion', tipo: 'juridica', modelos: ['303','200','390','347'], particularidades: 'Sin animo lucro, IS reducido', regimen: 'IS parcial + IVA si actividad' },
  { id: 'comunidad_prop', nombre: 'Comunidad de propietarios', tipo: 'juridica', modelos: [], particularidades: 'Sin IVA, sin IS, solo cuotas', regimen: 'Sin impuestos indirectos' },
  { id: 'fundacion', nombre: 'Fundacion', tipo: 'juridica', modelos: ['200','347'], particularidades: 'IS 10% si cumple requisitos', regimen: 'IS reducido + IVA exento parcial' },
]
```

**Step 4: Verificar que compila**

Run: `cd spice-landing && npm run build`
Expected: Build exitoso

**Step 5: Commit**

```bash
git add spice-landing/src/hooks/ spice-landing/src/data/
git commit -m "feat: hooks useInView/useCountUp + 6 archivos datos SPICE"
```

---

### Task 3: Navbar + Hero + Problema (secciones 1-2)

**Files:**
- Create: `spice-landing/src/components/Navbar.tsx`
- Create: `spice-landing/src/components/Hero.tsx`
- Create: `spice-landing/src/components/Problema.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear Navbar**

Navbar fija transparente con logo SPICE y links de scroll a secciones principales. Fondo blur al hacer scroll.

**Step 2: Crear Hero**

Seccion hero con:
- Logo SVG llama esmeralda+dorado
- Titulo "SPICE" en Space Grotesk 4xl/6xl
- Subtitulo "Sistema Profesional Inteligente de Contabilidad Evolutiva"
- Descripcion breve
- Boton CTA esmeralda "Descubre como funciona" con smooth scroll
- Fondo: particulas CSS (divs absolutos con opacity animation)
- Mobile: todo centrado, padding generoso

**Step 3: Crear Problema**

4 tarjetas glassmorphism con pain points:
- Icono Lucide en rojo (Clock, FileWarning, AlertTriangle, CalendarClock)
- Titulo bold
- Descripcion con numero destacado
- Visual inferior: "10 horas/mes → 15 minutos/mes"

**Step 4: Actualizar App.tsx con los 3 componentes**

**Step 5: Verificar visualmente**

Run: `cd spice-landing && npm run dev`
Verificar en http://localhost:5180

**Step 6: Commit**

```bash
git add spice-landing/src/components/ spice-landing/src/App.tsx
git commit -m "feat: Navbar + Hero + Problema — secciones 1-2 SPICE"
```

---

### Task 4: Vision + Diagrama Pipeline (secciones 3-4)

**Files:**
- Create: `spice-landing/src/components/Vision.tsx`
- Create: `spice-landing/src/components/DiagramaPipeline.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear Vision**

- Frase destacada en dorado
- Grid 2x3 (mobile) / 3x2 (desktop) con 6 metricas
- Cada metrica: numero grande (useCountUp) + etiqueta
- Tarjetas glassmorphism con borde esmeralda sutil

**Step 2: Crear DiagramaPipeline**

SVG inline vertical con 7 nodos conectados:
- Linea vertical central con animacion stroke-dashoffset (CSS)
- Cada nodo: circulo numerado (fondo esmeralda) + caja con titulo, descripcion, dato clave dorado
- Entrada arriba: caja doble borde "PDFs en inbox"
- Salida abajo: caja doble borde "Contabilidad lista — Score 95%+"
- Animacion: nodos aparecen secuencialmente con useInView + transition-delay
- Mobile: full-width, scroll natural vertical

**Step 3: Actualizar App.tsx**

**Step 4: Verificar visualmente**

**Step 5: Commit**

```bash
git commit -m "feat: Vision + DiagramaPipeline — secciones 3-4 SPICE"
```

---

### Task 5: Diagrama OCR Tiers + Tipos documento (secciones 5-6)

**Files:**
- Create: `spice-landing/src/components/DiagramaOCR.tsx`
- Create: `spice-landing/src/components/TiposDocumento.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear DiagramaOCR**

Flowchart SVG de decision con 3 caminos:
- Nodo inicial: "PDF llega"
- Caja Mistral OCR3
- Diamante decision: "Confianza >= 85%?"
- SI → Tier 0 (verde, "~70% docs, 1 motor")
- NO → Caja GPT-4o → Diamante "Mistral = GPT?"
- SI → Tier 1 (amarillo, "~25% docs, 2 motores")
- NO → Caja Gemini → "Votacion 2-de-3" → Tier 2 (naranja, "~5% docs, 3 motores")
- Texto explicativo debajo
- Animacion: aparece con useInView

**Step 2: Crear TiposDocumento**

- Grid 2x5 (mobile) de tarjetas compactas
- Cada tarjeta: codigo (FC/FV/NC...) con color, nombre, subcuentas
- Expandible al click: muestra asiento completo con tabla debe/haber
- Usa datos de `data/tiposDocumento.ts`
- Dos grupos visuales: "Facturas" y "Otros documentos"

**Step 3: Actualizar App.tsx**

**Step 4: Commit**

```bash
git commit -m "feat: DiagramaOCR + TiposDocumento — secciones 5-6 SPICE"
```

---

### Task 6: Jerarquia reglas + Clasificador (secciones 7-8)

**Files:**
- Create: `spice-landing/src/components/DiagramaJerarquia.tsx`
- Create: `spice-landing/src/components/DiagramaClasificador.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear DiagramaJerarquia**

Piramide invertida SVG (trapezoides apilados, ancho decrece):
- Nivel 0 (mas ancho): NORMATIVA — fondo dorado oscuro
- Nivel 1: PGC — fondo dorado medio
- Nivel 2: PERFIL FISCAL — fondo transicion
- Nivel 3: REGLAS NEGOCIO — fondo esmeralda oscuro
- Nivel 4: REGLAS CLIENTE — fondo esmeralda medio
- Nivel 5 (mas estrecho): APRENDIZAJE — fondo esmeralda claro
- Flecha lateral "AUTORIDAD" de arriba a abajo
- Texto destacado: "Los niveles superiores NUNCA se violan"
- Ejemplo interactivo: factura recorre la cascada

**Step 2: Crear DiagramaClasificador**

Flowchart SVG vertical con 6 diamantes de decision:
- Cada diamante tiene pregunta + porcentaje de confianza si match
- Linea principal vertical, salidas laterales derechas
- Final: caja CUARENTENA (borde rojo) → APRENDIZAJE (borde dorado)
- Barras de confianza visuales junto a cada salida (verde/amarillo)
- Colores: verde alto, amarillo medio, rojo cuarentena

**Step 3: Actualizar App.tsx**

**Step 4: Commit**

```bash
git commit -m "feat: DiagramaJerarquia + DiagramaClasificador — secciones 7-8 SPICE"
```

---

### Task 7: Trazabilidad + Mapa territorios (secciones 9-10)

**Files:**
- Create: `spice-landing/src/components/Trazabilidad.tsx`
- Create: `spice-landing/src/components/MapaTerritorios.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear Trazabilidad**

Tarjeta grande tipo "recibo de decision contable":
- Fondo ligeramente mas claro, borde dorado
- Header: nombre archivo PDF
- Razonamiento: 5 lineas con checkmarks verdes y explicacion
- Tabla asiento: 3 filas (subcuenta, debe, haber) con formato contable
- Verificaciones: 4 badges verdes
- OCR info: motor, tier, confianza
- Texto explicativo debajo

**Step 2: Crear MapaTerritorios**

SVG simplificado del mapa de Espana con 5 zonas:
- Cada zona coloreada segun `data/territorios.ts`
- Al click/tap: panel lateral/inferior con detalle completo
- Tipos impositivos en tarjetas dentro del panel
- Info IS, modelos especificos
- Mobile: mapa arriba, detalle debajo (sin overlay)

**Step 3: Actualizar App.tsx**

**Step 4: Commit**

```bash
git commit -m "feat: Trazabilidad + MapaTerritorios — secciones 9-10 SPICE"
```

---

### Task 8: Ciclo contable + Modelos fiscales (secciones 11-12)

**Files:**
- Create: `spice-landing/src/components/DiagramaCiclo.tsx`
- Create: `spice-landing/src/components/ModelosFiscales.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear DiagramaCiclo**

Timeline SVG horizontal scrollable:
- 12 marcas de meses (ENE-DIC)
- Barras mensuales recurrentes (amortizacion, provision) como fondo
- 4 bloques trimestrales destacados (ABR, JUL, OCT, ENE)
- Bloque anual grande DIC-ENE (cierre)
- Accordion expandible con los 10 pasos de cierre
- Mobile: scroll horizontal con CSS scroll-snap

**Step 2: Crear ModelosFiscales**

3 tabs (Automaticos / Semi-automaticos / Asistidos):
- Tab automaticos: lista 11 modelos con icono, nombre, periodicidad, quien
- Tab semi: 3 modelos + mockup visual del borrador 200
- Tab asistido: modelo 100 con explicacion
- Usa datos de `data/modelosFiscales.ts`

**Step 3: Actualizar App.tsx**

**Step 4: Commit**

```bash
git commit -m "feat: DiagramaCiclo + ModelosFiscales — secciones 11-12 SPICE"
```

---

### Task 9: Aprendizaje + Formas juridicas (secciones 13-14)

**Files:**
- Create: `spice-landing/src/components/DiagramaAprendizaje.tsx`
- Create: `spice-landing/src/components/FormasJuridicas.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear DiagramaAprendizaje**

Ciclo SVG con flechas curvadas:
- Documento → Registrar → Error? (diamante)
- NO → OK
- SI → Patron conocido? → SI → Aplicar → Exito → REFORZAR
- NO → 6 estrategias (lista) → Alguna funciona?
- SI → APRENDER (caja dorada con icono libro)
- NO → CUARENTENA (caja roja) → Gestor decide → APRENDER
- Flecha retroalimentacion cerrando ciclo
- Ejemplo: "Dia 1: desconocido → Dia 2: automatico"

**Step 2: Crear FormasJuridicas**

Grid expandible con 12 formas juridicas:
- Dos secciones: "Personas fisicas" y "Personas juridicas"
- Cada tarjeta: nombre, modelos (badges), regimen
- Expandible al click: particularidades completas
- Usa datos de `data/formasJuridicas.ts`

**Step 3: Actualizar App.tsx**

**Step 4: Commit**

```bash
git commit -m "feat: DiagramaAprendizaje + FormasJuridicas — secciones 13-14 SPICE"
```

---

### Task 10: Resultados + Footer (secciones 15-16)

**Files:**
- Create: `spice-landing/src/components/Resultados.tsx`
- Create: `spice-landing/src/components/Footer.tsx`
- Modify: `spice-landing/src/App.tsx`

**Step 1: Crear Resultados**

- 6 metricas grandes con countUp animado
- Caso destacado: tarjeta glassmorphism "Pastorino Costa del Sol"
  - 46 facturas, 11 proveedores, 3 divisas
  - IVA identico, balance cuadrado
- Score de fiabilidad: barra visual con 6 capas
- Tabla de capas con pesos

**Step 2: Crear Footer**

- Timeline roadmap: Hoy → Dashboard → SaaS (3 nodos)
- "Desarrollado por Carlos Canete Gomez"
- Link a carloscanetegomez.dev
- Copyright
- Gradiente inferior sutil

**Step 3: Actualizar App.tsx con TODOS los componentes (orden final)**

```tsx
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import Problema from './components/Problema'
import Vision from './components/Vision'
import DiagramaPipeline from './components/DiagramaPipeline'
import DiagramaOCR from './components/DiagramaOCR'
import TiposDocumento from './components/TiposDocumento'
import DiagramaJerarquia from './components/DiagramaJerarquia'
import DiagramaClasificador from './components/DiagramaClasificador'
import Trazabilidad from './components/Trazabilidad'
import MapaTerritorios from './components/MapaTerritorios'
import DiagramaCiclo from './components/DiagramaCiclo'
import ModelosFiscales from './components/ModelosFiscales'
import DiagramaAprendizaje from './components/DiagramaAprendizaje'
import FormasJuridicas from './components/FormasJuridicas'
import Resultados from './components/Resultados'
import Footer from './components/Footer'

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Problema />
        <Vision />
        <DiagramaPipeline />
        <DiagramaOCR />
        <TiposDocumento />
        <DiagramaJerarquia />
        <DiagramaClasificador />
        <Trazabilidad />
        <MapaTerritorios />
        <DiagramaCiclo />
        <ModelosFiscales />
        <DiagramaAprendizaje />
        <FormasJuridicas />
        <Resultados />
      </main>
      <Footer />
    </>
  )
}
```

**Step 4: Verificar build completo**

Run: `cd spice-landing && npm run build`
Expected: Build exitoso, 0 errores TypeScript, 0 warnings

**Step 5: Commit**

```bash
git commit -m "feat: Resultados + Footer + App completo — secciones 15-16 SPICE"
```

---

### Task 11: Pulido visual + responsive + animaciones

**Files:**
- Modify: `spice-landing/src/index.css` (animaciones globales)
- Modify: todos los componentes que necesiten ajustes responsive
- Modify: `spice-landing/src/App.tsx` (separadores entre secciones)

**Step 1: Agregar animaciones CSS globales**

En `index.css`, agregar keyframes para:
- `fade-in-up`: opacity 0→1 + translateY 20px→0
- `dash-offset`: para lineas SVG del pipeline
- `pulse-glow`: para el boton CTA
- `float`: para particulas del hero

**Step 2: Verificar responsive en 3 breakpoints**

Verificar cada seccion en:
- Mobile (375px)
- Tablet (768px)
- Desktop (1280px)

Ajustar paddings, font sizes, grid layouts segun necesidad.

**Step 3: Verificar accesibilidad basica**

- Contraste texto/fondo
- aria-labels en SVGs
- Focus visible en elementos interactivos
- Scroll suave funciona

**Step 4: Commit**

```bash
git commit -m "feat: pulido visual, responsive y animaciones SPICE landing"
```

---

### Task 12: Build + configurar launch.json para preview

**Files:**
- Create: `spice-landing/.claude/launch.json`

**Step 1: Crear launch.json**

```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "spice-dev",
      "runtimeExecutable": "npm",
      "runtimeArgs": ["run", "dev"],
      "port": 5180
    }
  ]
}
```

**Step 2: Build final**

Run: `cd spice-landing && npm run build`
Expected: Build exitoso

**Step 3: Verificar con preview**

Run: `npm run preview`
Verificar que sirve correctamente en http://localhost:4173

**Step 4: Commit final**

```bash
git commit -m "feat: SPICE landing completa — 16 secciones, 8 diagramas, mobile-first"
```

---

### Task 13: Deploy a spice.carloscanetegomez.dev

**Files:**
- Crear config Nginx en servidor

**Step 1: Build produccion**

Run: `cd spice-landing && npm run build`

**Step 2: Subir dist/ al servidor**

```bash
scp -r spice-landing/dist/* carli@65.108.60.69:/opt/apps/spice-landing/
```

**Step 3: Configurar Nginx**

SSH al servidor y crear `/opt/infra/nginx/conf.d/spice.conf`:
```nginx
server {
    listen 80;
    server_name spice.carloscanetegomez.dev;

    location / {
        root /opt/apps/spice-landing;
        try_files $uri $uri/ /index.html;
    }
}
```

**Step 4: SSL con certbot**

```bash
sudo certbot --nginx -d spice.carloscanetegomez.dev
```

**Step 5: DNS en Porkbun**

Crear registro A: `spice` → `65.108.60.69`

**Step 6: Verificar**

Abrir https://spice.carloscanetegomez.dev en navegador y movil.

**Step 7: Commit**

```bash
git commit -m "chore: deploy SPICE landing a spice.carloscanetegomez.dev"
```
