# PROMETH-AI Web — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Convertir la landing de SPICE (single-page técnica) en una web multi-página de PROMETH-AI orientada a venta con profundidad técnica en páginas secundarias.

**Architecture:** Multi-página con React Router v6. Home comercial → selector de 3 perfiles (gestorías, asesores, clientes) → páginas de perfil + páginas técnicas (/como-funciona, /seguridad, /precios). Brand: paleta ámbar/fuego sobre fondo negro profundo.

**Tech Stack:** React 19 + TypeScript + Vite 7 + Tailwind v4 + react-router-dom v6 + Lucide React. Trabajar en `spice-landing/` (renombrado mentalmente a prometh-ai-web).

**Design doc:** `docs/plans/2026-03-01-prometh-ai-web-design.md`

**Verificación:** `npm run build` después de cada tarea (TypeScript + Vite). `npm run dev` para ver visualmente.

---

## Task 1: Instalar react-router-dom + restructurar directorios

**Files:**
- Modify: `spice-landing/package.json`
- Create: `spice-landing/src/router.tsx`
- Modify: `spice-landing/src/main.tsx`
- Create: `spice-landing/src/pages/Home.tsx`
- Create: `spice-landing/src/pages/Gestorias.tsx`
- Create: `spice-landing/src/pages/Asesores.tsx`
- Create: `spice-landing/src/pages/Clientes.tsx`
- Create: `spice-landing/src/pages/ComoFunciona.tsx`
- Create: `spice-landing/src/pages/Seguridad.tsx`
- Create: `spice-landing/src/pages/Precios.tsx`

**Step 1: Instalar react-router-dom**

```bash
cd spice-landing
npm install react-router-dom
```

**Step 2: Crear el router**

`src/router.tsx`:
```tsx
import { createBrowserRouter } from 'react-router-dom'
import Home from './pages/Home'
import Gestorias from './pages/Gestorias'
import Asesores from './pages/Asesores'
import Clientes from './pages/Clientes'
import ComoFunciona from './pages/ComoFunciona'
import Seguridad from './pages/Seguridad'
import Precios from './pages/Precios'

export const router = createBrowserRouter([
  { path: '/',               element: <Home /> },
  { path: '/gestorias',      element: <Gestorias /> },
  { path: '/asesores',       element: <Asesores /> },
  { path: '/clientes',       element: <Clientes /> },
  { path: '/como-funciona',  element: <ComoFunciona /> },
  { path: '/seguridad',      element: <Seguridad /> },
  { path: '/precios',        element: <Precios /> },
])
```

**Step 3: Actualizar main.tsx**

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './router'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
```

**Step 4: Crear páginas placeholder (cada una igual, cambiar el texto)**

`src/pages/Home.tsx`:
```tsx
export default function Home() {
  return <div className="min-h-screen flex items-center justify-center text-prometh-text text-2xl">Home — en construcción</div>
}
```
Repetir para Gestorias, Asesores, Clientes, ComoFunciona, Seguridad, Precios (cambiar texto).

**Step 5: Verificar build**

```bash
npm run build
```
Esperado: sin errores TypeScript.

**Step 6: Commit**

```bash
git add spice-landing/
git commit -m "feat: setup react-router-dom + estructura multi-página PROMETH-AI"
```

---

## Task 2: Brand tokens PROMETH-AI (reemplazar SPICE)

**Files:**
- Modify: `spice-landing/src/index.css`
- Modify: `spice-landing/index.html`

**Step 1: Reemplazar tokens de color y tipografía**

`src/index.css` — reemplazar todo el bloque `@theme` y `body`:

```css
@import "tailwindcss";

@theme {
  /* Paleta PROMETH-AI — fuego/ámbar sobre negro profundo */
  --color-prometh-bg:         #0a0a0f;
  --color-prometh-surface:    #111118;
  --color-prometh-border:     rgba(245, 158, 11, 0.15);
  --color-prometh-amber:      #f59e0b;
  --color-prometh-amber-light:#fbbf24;
  --color-prometh-amber-dark: #d97706;
  --color-prometh-orange:     #ea580c;
  --color-prometh-text:       #f8fafc;
  --color-prometh-muted:      #94a3b8;
  --color-prometh-card:       rgba(245, 158, 11, 0.04);
  --color-prometh-red:        #ef4444;
  --color-prometh-green:      #10b981;

  --font-heading: 'Space Grotesk', sans-serif;
  --font-body:    'Inter', sans-serif;
}

@layer base {
  html { scroll-behavior: smooth; }
  body {
    font-family: var(--font-body);
    background-color: var(--color-prometh-bg);
    color: var(--color-prometh-text);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  h1, h2, h3, h4, h5, h6 { font-family: var(--font-heading); }
}

/* Animaciones */
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes pulse-glow-amber {
  0%, 100% { box-shadow: 0 0 20px rgba(245, 158, 11, 0.3); }
  50%       { box-shadow: 0 0 50px rgba(245, 158, 11, 0.7); }
}

@keyframes float {
  0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.12; }
  33%       { transform: translateY(-12px) rotate(2deg); opacity: 0.2; }
  66%       { transform: translateY(6px) rotate(-1deg); opacity: 0.1; }
}

@keyframes flame-flicker {
  0%, 100% { transform: scaleY(1) scaleX(1); }
  25%       { transform: scaleY(1.05) scaleX(0.97); }
  75%       { transform: scaleY(0.97) scaleX(1.03); }
}

/* Utilidades globales */
@layer components {
  .glass-card {
    background: var(--color-prometh-card);
    border: 1px solid var(--color-prometh-border);
    border-radius: 0.75rem;
    backdrop-filter: blur(8px);
  }
  .btn-primary {
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    color: white;
    font-weight: 600;
    padding: 0.875rem 2rem;
    border-radius: 0.75rem;
    transition: opacity 0.2s, transform 0.2s;
  }
  .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
  .animate-fade-in-up  { animation: fade-in-up 0.6s ease-out forwards; }
  .animate-float       { animation: float 7s ease-in-out infinite; }
  .animate-pulse-amber { animation: pulse-glow-amber 2.5s ease-in-out infinite; }
  .animate-flame       { animation: flame-flicker 3s ease-in-out infinite; }
  .gradient-text {
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}
```

**Step 2: Actualizar index.html**

```html
<title>PROMETH-AI | Contabilidad Inteligente</title>
<meta name="description" content="PROMETH-AI — IA que lee, contabiliza y presenta. Para gestorías, asesores fiscales y empresas." />
```

**Step 3: Verificar build**

```bash
npm run build
```

**Step 4: Commit**

```bash
git add spice-landing/
git commit -m "feat: brand tokens PROMETH-AI — paleta ambar/fuego, animaciones"
```

---

## Task 3: Logo SVG + componente compartido

**Files:**
- Create: `spice-landing/src/components/shared/LogoPrometh.tsx`
- Create: `spice-landing/src/components/shared/SectionWrapper.tsx`

**Step 1: Logo — llama estilizada + wordmark**

`src/components/shared/LogoPrometh.tsx`:
```tsx
interface Props {
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
}

const sizes = {
  sm: { flame: 'w-6 h-8',  text: 'text-lg' },
  md: { flame: 'w-8 h-11', text: 'text-2xl' },
  lg: { flame: 'w-12 h-16',text: 'text-4xl' },
}

export default function LogoPrometh({ size = 'md', showText = true }: Props) {
  const s = sizes[size]
  return (
    <div className="flex items-center gap-2">
      <svg viewBox="0 0 40 56" fill="none" className={`${s.flame} animate-flame`} aria-hidden="true">
        {/* Llama exterior — ámbar */}
        <path d="M20 2C20 2 6 20 6 36c0 11 6 18 14 20 8-2 14-9 14-20 0-16-14-34-14-34z"
          fill="url(#grad-outer)" />
        {/* Llama interior — naranja */}
        <path d="M20 14c0 0-7 12-7 24 0 7 3.5 12 7 14 3.5-2 7-7 7-14 0-12-7-24-7-24z"
          fill="url(#grad-inner)" opacity="0.9" />
        {/* Núcleo brillante */}
        <path d="M20 28c0 0-3 5-3 12 0 4 1.5 7 3 8 1.5-1 3-4 3-8 0-7-3-12-3-12z"
          fill="#fef3c7" opacity="0.8" />
        <defs>
          <linearGradient id="grad-outer" x1="20" y1="2" x2="20" y2="56" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#fbbf24" />
            <stop offset="100%" stopColor="#ea580c" />
          </linearGradient>
          <linearGradient id="grad-inner" x1="20" y1="14" x2="20" y2="52" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#dc2626" />
          </linearGradient>
        </defs>
      </svg>
      {showText && (
        <span className={`font-heading font-bold gradient-text ${s.text} tracking-tight`}>
          PROMETH-AI
        </span>
      )}
    </div>
  )
}
```

**Step 2: SectionWrapper — contenedor estándar**

`src/components/shared/SectionWrapper.tsx`:
```tsx
interface Props {
  id?: string
  className?: string
  children: React.ReactNode
}

export default function SectionWrapper({ id, className = '', children }: Props) {
  return (
    <section id={id} className={`py-20 px-4 ${className}`}>
      <div className="max-w-6xl mx-auto">
        {children}
      </div>
    </section>
  )
}
```

**Step 3: Verificar build**

```bash
npm run build
```

**Step 4: Commit**

```bash
git add spice-landing/src/components/shared/
git commit -m "feat: logo PROMETH-AI SVG + SectionWrapper compartido"
```

---

## Task 4: Navbar + Footer

**Files:**
- Create: `spice-landing/src/components/layout/Navbar.tsx`
- Create: `spice-landing/src/components/layout/Footer.tsx`
- Create: `spice-landing/src/components/layout/PageLayout.tsx`

**Step 1: Navbar responsive con links + CTA**

`src/components/layout/Navbar.tsx`:
```tsx
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import LogoPrometh from '../shared/LogoPrometh'

const links = [
  { href: '/gestorias',     label: 'Gestorías' },
  { href: '/asesores',      label: 'Asesores' },
  { href: '/clientes',      label: 'Clientes' },
  { href: '/como-funciona', label: 'Cómo funciona' },
  { href: '/seguridad',     label: 'Seguridad' },
  { href: '/precios',       label: 'Precios' },
]

export default function Navbar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', handler)
    return () => window.removeEventListener('scroll', handler)
  }, [])

  useEffect(() => { setOpen(false) }, [pathname])

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'bg-prometh-bg/95 backdrop-blur-md border-b border-prometh-border' : ''
    }`}>
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/"><LogoPrometh size="sm" /></Link>

        {/* Desktop */}
        <div className="hidden md:flex items-center gap-6">
          {links.map(l => (
            <Link key={l.href} to={l.href}
              className={`text-sm font-body transition-colors hover:text-prometh-amber ${
                pathname === l.href ? 'text-prometh-amber' : 'text-prometh-muted'
              }`}>
              {l.label}
            </Link>
          ))}
          <a href="mailto:hola@prometh-ai.es"
            className="btn-primary text-sm py-2 px-4 rounded-lg">
            Solicitar demo
          </a>
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-prometh-text" onClick={() => setOpen(!open)}>
          {open ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden bg-prometh-surface border-b border-prometh-border px-4 py-4 flex flex-col gap-4">
          {links.map(l => (
            <Link key={l.href} to={l.href}
              className={`text-sm font-body py-2 border-b border-prometh-border/50 ${
                pathname === l.href ? 'text-prometh-amber' : 'text-prometh-text'
              }`}>
              {l.label}
            </Link>
          ))}
          <a href="mailto:hola@prometh-ai.es" className="btn-primary text-center text-sm">
            Solicitar demo
          </a>
        </div>
      )}
    </nav>
  )
}
```

**Step 2: Footer**

`src/components/layout/Footer.tsx`:
```tsx
import { Link } from 'react-router-dom'
import { Mail } from 'lucide-react'
import LogoPrometh from '../shared/LogoPrometh'

const cols = [
  { titulo: 'Perfiles', links: [
    { href: '/gestorias', label: 'Gestorías' },
    { href: '/asesores',  label: 'Asesores Fiscales' },
    { href: '/clientes',  label: 'Clientes' },
  ]},
  { titulo: 'Producto', links: [
    { href: '/como-funciona', label: 'Cómo funciona' },
    { href: '/seguridad',     label: 'Seguridad' },
    { href: '/precios',       label: 'Precios' },
  ]},
]

export default function Footer() {
  return (
    <footer className="border-t border-prometh-border bg-prometh-surface mt-20">
      <div className="max-w-6xl mx-auto px-4 py-12 grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="md:col-span-2">
          <LogoPrometh size="sm" />
          <p className="mt-3 text-prometh-muted text-sm max-w-xs leading-relaxed">
            IA que lee, contabiliza y presenta. Para gestorías, asesores y empresas.
          </p>
          <a href="mailto:hola@prometh-ai.es"
            className="mt-4 inline-flex items-center gap-2 text-prometh-amber text-sm hover:text-prometh-amber-light transition-colors">
            <Mail size={16} />
            hola@prometh-ai.es
          </a>
        </div>
        {cols.map(col => (
          <div key={col.titulo}>
            <h4 className="font-heading font-bold text-prometh-text text-sm mb-3">{col.titulo}</h4>
            <ul className="space-y-2">
              {col.links.map(l => (
                <li key={l.href}>
                  <Link to={l.href} className="text-prometh-muted text-sm hover:text-prometh-amber transition-colors">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-prometh-border px-4 py-4 text-center text-prometh-muted text-xs">
        © {new Date().getFullYear()} PROMETH-AI. Todos los derechos reservados.
      </div>
    </footer>
  )
}
```

**Step 3: PageLayout — envuelve todas las páginas**

`src/components/layout/PageLayout.tsx`:
```tsx
import Navbar from './Navbar'
import Footer from './Footer'

export default function PageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-prometh-bg">
      <Navbar />
      <main className="pt-16">{children}</main>
      <Footer />
    </div>
  )
}
```

**Step 4: Actualizar páginas placeholder para usar PageLayout**

En cada `src/pages/*.tsx`:
```tsx
import PageLayout from '../components/layout/PageLayout'

export default function Home() {
  return (
    <PageLayout>
      <div className="min-h-screen flex items-center justify-center text-prometh-text text-2xl">
        Home — en construcción
      </div>
    </PageLayout>
  )
}
```

**Step 5: Verificar build + visual**

```bash
npm run build && npm run dev
```
Esperado: navbar fija con logo + links, footer al final de cada página.

**Step 6: Commit**

```bash
git add spice-landing/src/components/layout/ spice-landing/src/pages/
git commit -m "feat: Navbar responsive + Footer + PageLayout PROMETH-AI"
```

---

## Task 5: Home — Hero

**Files:**
- Create: `spice-landing/src/components/home/Hero.tsx`
- Modify: `spice-landing/src/pages/Home.tsx`

**Step 1: Componente Hero**

`src/components/home/Hero.tsx`:
```tsx
import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import LogoPrometh from '../shared/LogoPrometh'

/** Partículas flotantes — documentos y números financieros */
const particulas = [
  { texto: 'PDF', top: '15%', left: '7%',  delay: '0s',   dur: '7s' },
  { texto: '303', top: '20%', right: '10%', delay: '1.2s', dur: '6s' },
  { texto: 'IVA', top: '55%', left: '5%',  delay: '2.4s', dur: '8s' },
  { texto: '347', top: '70%', right: '8%', delay: '0.8s', dur: '7s' },
  { texto: '130', top: '35%', left: '14%', delay: '3.1s', dur: '6.5s' },
  { texto: 'OCR', top: '42%', right: '17%',delay: '1.8s', dur: '7.5s' },
  { texto: '472', top: '80%', left: '20%', delay: '0.5s', dur: '6s' },
  { texto: '111', top: '25%', right: '25%',delay: '2.8s', dur: '8s' },
  { texto: 'XML', top: '62%', left: '28%', delay: '3.5s', dur: '7s' },
  { texto: '390', top: '85%', right: '15%',delay: '1.5s', dur: '6.5s' },
]

export default function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-4">
      {/* Partículas flotantes */}
      {particulas.map(p => (
        <span key={p.texto + p.top}
          className="absolute font-heading font-bold text-prometh-amber/10 text-2xl md:text-4xl select-none pointer-events-none animate-float"
          style={{ top: p.top, left: p.left, right: p.right, animationDelay: p.delay, animationDuration: p.dur }}>
          {p.texto}
        </span>
      ))}

      {/* Glow radial central */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(245,158,11,0.07) 0%, transparent 70%)' }} />

      {/* Contenido */}
      <div className="relative z-10 text-center flex flex-col items-center gap-6 max-w-4xl animate-fade-in-up">
        <LogoPrometh size="lg" />

        <h1 className="text-5xl md:text-7xl font-heading font-bold text-prometh-text tracking-tight leading-tight">
          Tu contabilidad,<br />
          <span className="gradient-text">en piloto automático</span>
        </h1>

        <p className="text-lg md:text-xl text-prometh-muted max-w-2xl leading-relaxed">
          IA que lee facturas, nóminas y extractos, los contabiliza en FacturaScripts
          y genera los modelos fiscales. Sin intervención manual.
        </p>

        <p className="text-sm text-prometh-muted/70">
          Para gestorías · Asesores fiscales · Empresas
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mt-2">
          <button
            onClick={() => document.getElementById('perfiles')?.scrollIntoView({ behavior: 'smooth' })}
            className="btn-primary animate-pulse-amber">
            Ver mi perfil
          </button>
          <Link to="/como-funciona"
            className="px-8 py-3.5 rounded-xl border border-prometh-border text-prometh-text font-semibold hover:border-prometh-amber/50 transition-colors">
            Ver cómo funciona
          </Link>
        </div>
      </div>

      {/* Indicador scroll */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 opacity-50">
        <div className="w-0.5 h-8 bg-gradient-to-b from-prometh-amber to-transparent" />
      </div>
    </section>
  )
}
```

**Step 2: Verificar build**

```bash
npm run build
```

**Step 3: Actualizar Home.tsx para incluir Hero**

```tsx
import PageLayout from '../components/layout/PageLayout'
import Hero from '../components/home/Hero'

export default function Home() {
  return (
    <PageLayout>
      <Hero />
    </PageLayout>
  )
}
```

**Step 4: Verificar visual**

```bash
npm run dev
```
Ir a http://localhost:5173 — verificar: logo, título, partículas flotantes, glow, dos botones CTA.

**Step 5: Commit**

```bash
git add spice-landing/src/components/home/Hero.tsx spice-landing/src/pages/Home.tsx
git commit -m "feat: Hero PROMETH-AI — llama, tagline, partículas flotantes"
```

---

## Task 6: Home — SelectorPerfil

**Files:**
- Create: `spice-landing/src/components/home/SelectorPerfil.tsx`
- Modify: `spice-landing/src/pages/Home.tsx`

**Step 1: Componente SelectorPerfil**

`src/components/home/SelectorPerfil.tsx`:
```tsx
import { Link } from 'react-router-dom'
import { Building2, BarChart3, User, ArrowRight } from 'lucide-react'

const perfiles = [
  {
    href: '/gestorias',
    icono: Building2,
    titulo: 'Soy Gestoría',
    subtitulo: 'Automatiza tu despacho',
    descripcion: 'Contabiliza las facturas de todos tus clientes sin intervención manual. Pipeline OCR + 28 modelos fiscales.',
    items: ['Multi-empresa con aislamiento', 'Triple IA: Mistral + GPT-4o + Gemini', '28 modelos fiscales automatizados'],
    color: 'hover:border-prometh-amber/50',
    badge: 'Más popular',
  },
  {
    href: '/asesores',
    icono: BarChart3,
    titulo: 'Soy Asesor Fiscal',
    subtitulo: 'Análisis 360°',
    descripcion: 'Visión económico-financiera y fiscal completa en tiempo real. Sin exportar a Excel.',
    items: ['PyG y ratios automáticos', 'Conciliación bancaria', 'Dashboard con 16 módulos'],
    color: 'hover:border-orange-500/50',
    badge: null,
  },
  {
    href: '/clientes',
    icono: User,
    titulo: 'Soy Cliente/Empresa',
    subtitulo: 'Conoce tu negocio',
    descripcion: 'Visibilidad total de tu empresa sin ser experto contable. Alertas, documentos y estado en tiempo real.',
    items: ['Portal cliente personalizado', 'Alertas de vencimientos', 'Propuestas adaptadas a tu necesidad'],
    color: 'hover:border-prometh-amber/30',
    badge: null,
  },
]

export default function SelectorPerfil() {
  return (
    <section id="perfiles" className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            ¿Cuál es tu perfil?
          </h2>
          <p className="text-prometh-muted text-lg">
            PROMETH-AI se adapta a tu rol y necesidades específicas
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {perfiles.map(p => {
            const Icono = p.icono
            return (
              <Link key={p.href} to={p.href}
                className={`glass-card p-8 flex flex-col gap-4 transition-all duration-300 group ${p.color} hover:-translate-y-1`}>
                {p.badge && (
                  <span className="self-start text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full">
                    {p.badge}
                  </span>
                )}
                <div className="w-12 h-12 rounded-xl bg-prometh-amber/10 flex items-center justify-center group-hover:bg-prometh-amber/20 transition-colors">
                  <Icono className="text-prometh-amber" size={24} />
                </div>
                <div>
                  <p className="text-prometh-muted text-sm mb-1">{p.subtitulo}</p>
                  <h3 className="text-xl font-heading font-bold text-prometh-text">{p.titulo}</h3>
                </div>
                <p className="text-prometh-muted text-sm leading-relaxed flex-1">{p.descripcion}</p>
                <ul className="space-y-2">
                  {p.items.map(item => (
                    <li key={item} className="flex items-center gap-2 text-xs text-prometh-muted">
                      <div className="w-1.5 h-1.5 rounded-full bg-prometh-amber shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <div className="flex items-center gap-2 text-prometh-amber text-sm font-semibold mt-2">
                  Ver propuesta <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Verificar build**

```bash
npm run build
```

**Step 3: Añadir SelectorPerfil al Home**

```tsx
import PageLayout from '../components/layout/PageLayout'
import Hero from '../components/home/Hero'
import SelectorPerfil from '../components/home/SelectorPerfil'

export default function Home() {
  return (
    <PageLayout>
      <Hero />
      <SelectorPerfil />
    </PageLayout>
  )
}
```

**Step 4: Commit**

```bash
git add spice-landing/src/components/home/SelectorPerfil.tsx spice-landing/src/pages/Home.tsx
git commit -m "feat: SelectorPerfil — 3 cards gestoria/asesor/cliente con links"
```

---

## Task 7: Home — Métricas + Pasos + completar Home

**Files:**
- Create: `spice-landing/src/components/home/Metricas.tsx`
- Create: `spice-landing/src/components/home/Pasos.tsx`
- Create: `spice-landing/src/components/home/BannerSeguridad.tsx`
- Modify: `spice-landing/src/pages/Home.tsx`

**Step 1: Métricas animadas**

`src/components/home/Metricas.tsx`:
```tsx
import { useInView } from '../../hooks/useInView'

const metricas = [
  { valor: '98%',    label: 'Precisión OCR',              color: 'text-prometh-amber' },
  { valor: '15 min', label: 'de supervisión al mes',      color: 'text-prometh-amber' },
  { valor: '28',     label: 'Modelos fiscales',           color: 'text-prometh-amber' },
  { valor: '1.793',  label: 'Tests pasando',              color: 'text-prometh-green' },
  { valor: '3',      label: 'Motores IA en paralelo',     color: 'text-prometh-amber' },
  { valor: '100%',   label: 'Balance cuadrado al céntimo',color: 'text-prometh-green' },
]

export default function Metricas() {
  const { ref, visible } = useInView()
  return (
    <section className="py-16 px-4 border-y border-prometh-border bg-prometh-surface/50">
      <div className="max-w-6xl mx-auto">
        <p className="text-center text-prometh-muted text-sm mb-8 uppercase tracking-widest">
          Resultados reales con datos de producción
        </p>
        <div ref={ref}
          className={`grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 transition-all duration-700 ${
            visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
          {metricas.map((m, i) => (
            <div key={i} className="text-center" style={{ transitionDelay: `${i * 80}ms` }}>
              <div className={`text-2xl md:text-3xl font-heading font-bold ${m.color}`}>{m.valor}</div>
              <div className="text-prometh-muted text-xs mt-1 leading-tight">{m.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
```

**Step 2: Cómo funciona en 3 pasos**

`src/components/home/Pasos.tsx`:
```tsx
import { Link } from 'react-router-dom'
import { Upload, Cpu, CheckCircle, ArrowRight } from 'lucide-react'
import { useInView } from '../../hooks/useInView'

const pasos = [
  {
    num: '01',
    icono: Upload,
    titulo: 'Recibes el documento',
    descripcion: 'Por email, drag & drop, escáner o carpeta vigilada. PROMETH-AI acepta facturas, nóminas, extractos bancarios y más.',
  },
  {
    num: '02',
    icono: Cpu,
    titulo: 'La IA lo procesa',
    descripcion: 'Triple motor OCR (Mistral + GPT-4o + Gemini) lee, clasifica, extrae datos y valida con 6 capas de confianza.',
  },
  {
    num: '03',
    icono: CheckCircle,
    titulo: 'Aparece en FacturaScripts',
    descripcion: 'Asiento contable creado, IVA aplicado, modelo fiscal actualizado. Todo en menos de 30 segundos por documento.',
  },
]

export default function Pasos() {
  const { ref, visible } = useInView()
  return (
    <section className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            Así de simple
          </h2>
          <p className="text-prometh-muted text-lg">De documento a asiento contable en 3 pasos</p>
        </div>

        <div ref={ref} className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {pasos.map((paso, i) => {
            const Icono = paso.icono
            return (
              <div key={i}
                className={`relative transition-all duration-700 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
                style={{ transitionDelay: `${i * 150}ms` }}>
                {i < pasos.length - 1 && (
                  <ArrowRight className="hidden md:block absolute -right-4 top-8 text-prometh-border" size={24} />
                )}
                <div className="glass-card p-6 h-full">
                  <div className="flex items-center gap-3 mb-4">
                    <span className="text-3xl font-heading font-bold text-prometh-amber/30">{paso.num}</span>
                    <div className="w-10 h-10 rounded-lg bg-prometh-amber/10 flex items-center justify-center">
                      <Icono className="text-prometh-amber" size={20} />
                    </div>
                  </div>
                  <h3 className="font-heading font-bold text-prometh-text mb-2">{paso.titulo}</h3>
                  <p className="text-prometh-muted text-sm leading-relaxed">{paso.descripcion}</p>
                </div>
              </div>
            )
          })}
        </div>

        <div className="text-center mt-10">
          <Link to="/como-funciona"
            className="inline-flex items-center gap-2 text-prometh-amber hover:text-prometh-amber-light transition-colors font-semibold">
            Ver el proceso completo <ArrowRight size={16} />
          </Link>
        </div>
      </div>
    </section>
  )
}
```

**Step 3: Banner seguridad**

`src/components/home/BannerSeguridad.tsx`:
```tsx
import { Link } from 'react-router-dom'
import { Shield, Lock, Server, ArrowRight } from 'lucide-react'

const items = [
  { icono: Shield, texto: 'Multi-tenant con aislamiento total' },
  { icono: Lock,   texto: '2FA + cifrado en tránsito y reposo' },
  { icono: Server, texto: 'Backups diarios · Hetzner Alemania · GDPR' },
]

export default function BannerSeguridad() {
  return (
    <section className="py-12 px-4 bg-prometh-surface/50 border-y border-prometh-border">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex flex-wrap justify-center md:justify-start gap-6">
          {items.map(({ icono: Icono, texto }) => (
            <div key={texto} className="flex items-center gap-2 text-sm text-prometh-muted">
              <Icono size={16} className="text-prometh-amber shrink-0" />
              {texto}
            </div>
          ))}
        </div>
        <Link to="/seguridad"
          className="whitespace-nowrap flex items-center gap-2 text-prometh-amber text-sm font-semibold hover:text-prometh-amber-light transition-colors">
          Ver arquitectura de seguridad <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  )
}
```

**Step 4: Home completo**

```tsx
import PageLayout from '../components/layout/PageLayout'
import Hero from '../components/home/Hero'
import SelectorPerfil from '../components/home/SelectorPerfil'
import Metricas from '../components/home/Metricas'
import Pasos from '../components/home/Pasos'
import BannerSeguridad from '../components/home/BannerSeguridad'

export default function Home() {
  return (
    <PageLayout>
      <Hero />
      <Metricas />
      <SelectorPerfil />
      <Pasos />
      <BannerSeguridad />
    </PageLayout>
  )
}
```

**Step 5: Verificar visual completo del Home**

```bash
npm run build && npm run dev
```

**Step 6: Commit**

```bash
git add spice-landing/src/components/home/ spice-landing/src/pages/Home.tsx
git commit -m "feat: Home completo — Métricas + SelectorPerfil + Pasos + BannerSeguridad"
```

---

## Task 8: Página /gestorias

**Files:**
- Create: `spice-landing/src/pages/Gestorias.tsx`
- Create: `spice-landing/src/components/gestorias/HeroGestorias.tsx`
- Create: `spice-landing/src/components/gestorias/FeaturesGestorias.tsx`

**Step 1: Hero Gestorías**

`src/components/gestorias/HeroGestorias.tsx`:
```tsx
import { ArrowRight, Clock, CheckCircle } from 'lucide-react'

export default function HeroGestorias() {
  return (
    <section className="pt-12 pb-20 px-4">
      <div className="max-w-5xl mx-auto text-center">
        <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
          Para gestorías y despachos
        </span>
        <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
          Tu despacho procesa<br />
          <span className="gradient-text">500 facturas al mes.</span><br />
          PROMETH-AI las contabiliza solas.
        </h1>
        <p className="text-lg text-prometh-muted max-w-2xl mx-auto mb-8 leading-relaxed">
          Elimina el registro manual, reduce los errores a cero y cumple todos los plazos fiscales
          de forma automática. Tú supervisas; PROMETH-AI ejecuta.
        </p>

        {/* Comparativo */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 mb-10">
          <div className="glass-card px-6 py-4 text-center border-red-500/30">
            <p className="text-3xl font-heading font-bold text-red-400">10 h</p>
            <p className="text-sm text-prometh-muted mt-1">de registro manual al mes</p>
          </div>
          <ArrowRight className="text-prometh-amber rotate-90 sm:rotate-0" size={28} />
          <div className="glass-card px-6 py-4 text-center border-prometh-amber/40">
            <p className="text-3xl font-heading font-bold text-prometh-amber">15 min</p>
            <p className="text-sm text-prometh-muted mt-1">de supervisión al mes</p>
          </div>
        </div>

        <a href="mailto:hola@prometh-ai.es?subject=Demo gestoria"
          className="btn-primary inline-flex items-center gap-2">
          Solicitar demo para mi despacho <ArrowRight size={16} />
        </a>
      </div>
    </section>
  )
}
```

**Step 2: Features Gestorías**

`src/components/gestorias/FeaturesGestorias.tsx`:
```tsx
import { Brain, FileText, Building2, Shield, RefreshCw, Zap } from 'lucide-react'

const features = [
  {
    icono: Brain,
    titulo: 'Triple motor OCR',
    desc: 'Mistral OCR (primario) → GPT-4o (fallback) → Gemini Flash (validación). 98% de precisión con cualquier formato de factura.',
  },
  {
    icono: Building2,
    titulo: 'Multi-empresa',
    desc: 'Gestiona todos tus clientes desde un único dashboard. Datos completamente aislados entre empresas.',
  },
  {
    icono: FileText,
    titulo: '28 modelos fiscales',
    desc: 'Modelo 303, 111, 130, 347, 390... generados automáticamente desde los datos contabilizados. Formato AEAT listo para presentar.',
  },
  {
    icono: RefreshCw,
    titulo: 'Motor de aprendizaje',
    desc: 'El sistema aprende de cada documento. Con el tiempo, reconoce los proveedores habituales de tu cliente sin necesidad de configuración.',
  },
  {
    icono: Zap,
    titulo: 'Integración FacturaScripts',
    desc: 'Asientos creados directamente vía API. Sin exportar, sin importar, sin re-introducir datos.',
  },
  {
    icono: Shield,
    titulo: 'Aislamiento multi-tenant',
    desc: 'Cada gestoría tiene su espacio completamente aislado. Los datos de un cliente nunca son visibles para otro.',
  },
]

export default function FeaturesGestorias() {
  return (
    <section className="py-20 px-4 bg-prometh-surface/30">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl font-heading font-bold text-prometh-text text-center mb-12">
          Todo lo que necesita tu despacho
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(f => {
            const Icono = f.icono
            return (
              <div key={f.titulo} className="glass-card p-6">
                <Icono className="text-prometh-amber mb-4" size={28} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-prometh-text mb-2">{f.titulo}</h3>
                <p className="text-prometh-muted text-sm leading-relaxed">{f.desc}</p>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
```

**Step 3: Página Gestorias.tsx**

```tsx
import PageLayout from '../components/layout/PageLayout'
import HeroGestorias from '../components/gestorias/HeroGestorias'
import FeaturesGestorias from '../components/gestorias/FeaturesGestorias'

export default function Gestorias() {
  return (
    <PageLayout>
      <HeroGestorias />
      <FeaturesGestorias />
    </PageLayout>
  )
}
```

**Step 4: Verificar build**

```bash
npm run build
```

**Step 5: Commit**

```bash
git add spice-landing/src/pages/Gestorias.tsx spice-landing/src/components/gestorias/
git commit -m "feat: página /gestorias — hero comparativo + 6 features"
```

---

## Task 9: Páginas /asesores y /clientes

**Files:**
- Create: `spice-landing/src/pages/Asesores.tsx`
- Create: `spice-landing/src/pages/Clientes.tsx`

**Step 1: Asesores.tsx**

```tsx
import PageLayout from '../components/layout/PageLayout'
import { BarChart3, PieChart, CreditCard, FileCheck, TrendingUp, Database, ArrowRight } from 'lucide-react'

const features = [
  { icono: BarChart3,  titulo: 'PyG automático',             desc: 'Cuenta de pérdidas y ganancias generada por período sin intervención manual.' },
  { icono: CreditCard, titulo: 'Conciliación bancaria',      desc: 'Importa extractos Norma 43 y CaixaBank XLS. Match automático con asientos.' },
  { icono: PieChart,   titulo: 'Ratios y análisis',          desc: 'Liquidez, solvencia, rentabilidad. Calculados automáticamente sobre datos reales.' },
  { icono: FileCheck,  titulo: 'Módulo fiscal completo',     desc: '303, 111, 130, 347, 390 y más. Datos pre-calculados, solo revisar y presentar.' },
  { icono: TrendingUp, titulo: 'Dashboard 16 módulos',       desc: 'Una pantalla con todo: económico, fiscal, bancario, documentos, RRHH.' },
  { icono: Database,   titulo: 'Historial completo',         desc: 'Acceso a todos los ejercicios. Comparativas interanuales en un clic.' },
]

export default function Asesores() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Para asesores fiscales
          </span>
          <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
            Análisis económico-financiero<br />
            <span className="gradient-text">en tiempo real.</span><br />
            Sin exportar a Excel.
          </h1>
          <p className="text-lg text-prometh-muted max-w-2xl mx-auto mb-8">
            Toda la información contable, fiscal y financiera de tus clientes centralizada.
            PROMETH-AI la procesa; tú la interpretas y asesoras.
          </p>
          <a href="mailto:hola@prometh-ai.es?subject=Demo asesor fiscal"
            className="btn-primary inline-flex items-center gap-2">
            Ver demo de análisis financiero <ArrowRight size={16} />
          </a>
        </div>
      </section>

      <section className="py-20 px-4 bg-prometh-surface/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map(f => {
              const Icono = f.icono
              return (
                <div key={f.titulo} className="glass-card p-6">
                  <Icono className="text-prometh-amber mb-4" size={28} strokeWidth={1.5} />
                  <h3 className="font-heading font-bold text-prometh-text mb-2">{f.titulo}</h3>
                  <p className="text-prometh-muted text-sm leading-relaxed">{f.desc}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>
    </PageLayout>
  )
}
```

**Step 2: Clientes.tsx**

```tsx
import PageLayout from '../components/layout/PageLayout'
import { Eye, Bell, FileText, MessageCircle, ArrowRight, Check } from 'lucide-react'

const features = [
  { icono: Eye,         titulo: 'Visibilidad de tu negocio',   desc: 'Ve cómo va tu empresa: ingresos, gastos, impuestos. Sin necesitar saber contabilidad.' },
  { icono: Bell,        titulo: 'Alertas de vencimientos',      desc: 'Recibe notificaciones antes de cada plazo fiscal. Nunca más una sanción por olvido.' },
  { icono: FileText,    titulo: 'Tus documentos centralizados', desc: 'Facturas, nóminas, modelos presentados. Todo organizado y accesible desde tu portal.' },
  { icono: MessageCircle, titulo: 'Habla con tu asesor',        desc: 'Canal directo con tu gestoría desde la misma plataforma. Sin emails perdidos.' },
]

const propuestas = [
  { nombre: 'Básico', desc: 'Visibilidad y alertas fiscales', items: ['Portal cliente', 'Alertas vencimientos', 'Documentos básicos'] },
  { nombre: 'Completo', desc: 'Análisis + asesoría integrada', items: ['Todo lo básico', 'Dashboard financiero', 'Chat con asesor', 'Informes mensuales'], destacado: true },
  { nombre: 'Premium', desc: 'Solución total a medida', items: ['Todo lo completo', 'Asesor dedicado', 'Informes a medida', 'Integración ERP'] },
]

export default function Clientes() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Para empresas y autónomos
          </span>
          <h1 className="text-4xl md:text-6xl font-heading font-bold text-prometh-text mb-6 leading-tight">
            Sabe exactamente<br />
            <span className="gradient-text">cómo va tu negocio.</span><br />
            Sin ser contable.
          </h1>
          <p className="text-lg text-prometh-muted max-w-2xl mx-auto mb-8">
            Tu gestoría usa PROMETH-AI para llevar tus cuentas. Tú tienes acceso en tiempo real
            a todo lo que importa de tu empresa.
          </p>
          <a href="mailto:hola@prometh-ai.es?subject=Informacion cliente"
            className="btn-primary inline-flex items-center gap-2">
            Hablar con un asesor <ArrowRight size={16} />
          </a>
        </div>
      </section>

      <section className="py-16 px-4 bg-prometh-surface/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-20">
            {features.map(f => {
              const Icono = f.icono
              return (
                <div key={f.titulo} className="glass-card p-6">
                  <Icono className="text-prometh-amber mb-3" size={24} strokeWidth={1.5} />
                  <h3 className="font-heading font-bold text-prometh-text mb-2 text-sm">{f.titulo}</h3>
                  <p className="text-prometh-muted text-xs leading-relaxed">{f.desc}</p>
                </div>
              )
            })}
          </div>

          <h2 className="text-2xl font-heading font-bold text-prometh-text text-center mb-8">
            Propuestas según tu necesidad
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {propuestas.map(p => (
              <div key={p.nombre}
                className={`glass-card p-6 ${p.destacado ? 'border-prometh-amber/50' : ''}`}>
                {p.destacado && (
                  <span className="text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full mb-3 inline-block">
                    Más elegido
                  </span>
                )}
                <h3 className="font-heading font-bold text-prometh-text text-xl mb-1">{p.nombre}</h3>
                <p className="text-prometh-muted text-sm mb-4">{p.desc}</p>
                <ul className="space-y-2 mb-6">
                  {p.items.map(item => (
                    <li key={item} className="flex items-center gap-2 text-sm text-prometh-muted">
                      <Check size={14} className="text-prometh-amber shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
                <a href="mailto:hola@prometh-ai.es"
                  className={`block text-center py-2 rounded-lg text-sm font-semibold transition-colors ${
                    p.destacado
                      ? 'btn-primary'
                      : 'border border-prometh-border text-prometh-text hover:border-prometh-amber/50'
                  }`}>
                  Consultar
                </a>
              </div>
            ))}
          </div>
        </div>
      </section>
    </PageLayout>
  )
}
```

**Step 3: Verificar build**

```bash
npm run build
```

**Step 4: Commit**

```bash
git add spice-landing/src/pages/Asesores.tsx spice-landing/src/pages/Clientes.tsx
git commit -m "feat: páginas /asesores y /clientes con hero + features + propuestas"
```

---

## Task 10: Página /como-funciona (migrar diagramas de SPICE)

**Files:**
- Modify: `spice-landing/src/pages/ComoFunciona.tsx`
- Reutilizar: `spice-landing/src/components/DiagramaPipeline.tsx`, `DiagramaOCR.tsx`, `TiposDocumento.tsx`, etc.

**Step 1: Los componentes de diagrama ya existen en SPICE**

Los siguientes componentes se pueden reutilizar directamente (cambiar solo colores spice-* → prometh-*):
- `DiagramaPipeline.tsx`
- `DiagramaOCR.tsx`
- `TiposDocumento.tsx`
- `DiagramaJerarquia.tsx`
- `DiagramaClasificador.tsx`
- `DiagramaAprendizaje.tsx`
- `ModelosFiscales.tsx`

**Step 2: Actualizar colores en los diagramas**

Hacer replace global en todos esos archivos:
```bash
cd spice-landing/src/components
# En cada archivo de diagrama: reemplazar clases spice-* por prometh-*
# spice-emerald → prometh-amber
# spice-text → prometh-text
# spice-text-muted → prometh-muted
# spice-bg → prometh-bg
# spice-card → prometh-surface
# spice-border → prometh-border
```

**Step 3: ComoFunciona.tsx**

```tsx
import PageLayout from '../components/layout/PageLayout'
import DiagramaPipeline from '../components/DiagramaPipeline'
import DiagramaOCR from '../components/DiagramaOCR'
import TiposDocumento from '../components/TiposDocumento'
import DiagramaJerarquia from '../components/DiagramaJerarquia'
import DiagramaClasificador from '../components/DiagramaClasificador'
import DiagramaAprendizaje from '../components/DiagramaAprendizaje'
import ModelosFiscales from '../components/ModelosFiscales'

export default function ComoFunciona() {
  return (
    <PageLayout>
      <section className="pt-12 pb-8 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Documentación técnica
          </span>
          <h1 className="text-4xl md:text-5xl font-heading font-bold text-prometh-text mb-4">
            Cómo funciona PROMETH-AI
          </h1>
          <p className="text-prometh-muted text-lg">
            Arquitectura detallada del pipeline de automatización contable
          </p>
        </div>
      </section>
      <DiagramaPipeline />
      <DiagramaOCR />
      <TiposDocumento />
      <DiagramaJerarquia />
      <DiagramaClasificador />
      <DiagramaAprendizaje />
      <ModelosFiscales />
    </PageLayout>
  )
}
```

**Step 4: Verificar build**

```bash
npm run build
```
Si hay errores de clases Tailwind no reconocidas (spice-*), buscar y reemplazar en los componentes afectados.

**Step 5: Commit**

```bash
git add spice-landing/src/
git commit -m "feat: página /como-funciona — diagramas técnicos migrados a brand PROMETH-AI"
```

---

## Task 11: Páginas /seguridad y /precios

**Files:**
- Modify: `spice-landing/src/pages/Seguridad.tsx`
- Modify: `spice-landing/src/pages/Precios.tsx`

**Step 1: Seguridad.tsx**

```tsx
import PageLayout from '../components/layout/PageLayout'
import { Shield, Lock, Users, Database, Server, FileCheck, Key, Eye, ArrowRight } from 'lucide-react'

const bloques = [
  {
    icono: Users,
    titulo: 'Multi-tenant con aislamiento total',
    items: [
      'Cada gestoría tiene su espacio completamente separado',
      'Un usuario nunca puede ver datos de otra gestoría',
      'JWT con gestoria_id en cada request',
      'Verificación de acceso en todos los endpoints',
    ],
  },
  {
    icono: Lock,
    titulo: 'Autenticación y acceso',
    items: [
      'JWT con expiración configurable (sessionStorage, no localStorage)',
      '2FA TOTP (Google Authenticator compatible)',
      'Lockout automático tras 5 intentos fallidos — 30 minutos',
      'Rate limiting por IP y usuario (5 login/min, 100 auth/min)',
    ],
  },
  {
    icono: Shield,
    titulo: 'Protección de datos',
    items: [
      'TLS 1.2+ en todo el tráfico (Let\'s Encrypt)',
      'Passwords con bcrypt (factor 12)',
      'Credenciales IMAP cifradas con Fernet',
      'Tokens RGPD de uso único con TTL 24h',
    ],
  },
  {
    icono: Database,
    titulo: 'Backups y disponibilidad',
    items: [
      'Backups diarios automáticos a las 02:00',
      '6 bases PostgreSQL + 2 MariaDB + configs + SSL',
      'Destino: Hetzner Helsinki (geográficamente separado)',
      'Retención: 7 diarios / 4 semanales / 12 mensuales',
    ],
  },
  {
    icono: Server,
    titulo: 'Infraestructura',
    items: [
      'Servidor Hetzner (Alemania) — GDPR compliant',
      'Firewall ufw + DOCKER-USER chain',
      'Puertos internos bloqueados del exterior',
      'nginx con HSTS, X-Frame-Options, CSP headers',
    ],
  },
  {
    icono: FileCheck,
    titulo: 'Cumplimiento RGPD',
    items: [
      'Exportación completa de datos en ZIP a petición',
      'Audit log de acciones de seguridad',
      'Política de retención configurable',
      'Derecho al olvido implementado',
    ],
  },
]

export default function Seguridad() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-3xl mx-auto text-center mb-16">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Seguridad y cumplimiento
          </span>
          <h1 className="text-4xl md:text-5xl font-heading font-bold text-prometh-text mb-4">
            Tus datos, protegidos
          </h1>
          <p className="text-prometh-muted text-lg">
            Arquitectura diseñada para cumplir RGPD y proteger información contable sensible
          </p>
        </div>

        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {bloques.map(b => {
            const Icono = b.icono
            return (
              <div key={b.titulo} className="glass-card p-6">
                <Icono className="text-prometh-amber mb-4" size={28} strokeWidth={1.5} />
                <h3 className="font-heading font-bold text-prometh-text mb-4">{b.titulo}</h3>
                <ul className="space-y-2">
                  {b.items.map(item => (
                    <li key={item} className="flex items-start gap-2 text-xs text-prometh-muted leading-relaxed">
                      <div className="w-1 h-1 rounded-full bg-prometh-amber mt-1.5 shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </section>
    </PageLayout>
  )
}
```

**Step 2: Precios.tsx**

```tsx
import PageLayout from '../components/layout/PageLayout'
import { Check, ArrowRight } from 'lucide-react'

const planes = [
  {
    perfil: 'Gestoría',
    subtitulo: 'Para despachos y asesorías',
    precio: 'Consultar',
    descripcion: 'Según volumen de clientes y documentos',
    items: [
      'Pipeline OCR completo',
      'Multi-empresa ilimitada',
      '28 modelos fiscales',
      'Dashboard gestoría',
      'Soporte prioritario',
    ],
    cta: 'Solicitar demo',
    href: 'mailto:hola@prometh-ai.es?subject=Precio gestoria',
  },
  {
    perfil: 'Asesor Fiscal',
    subtitulo: 'Para asesores independientes',
    precio: 'Consultar',
    descripcion: 'Según número de clientes gestionados',
    items: [
      'Todo lo de Gestoría',
      'Módulo análisis financiero',
      'Conciliación bancaria',
      'Ratios y reporting',
      'Portal cliente incluido',
    ],
    cta: 'Hablar con ventas',
    href: 'mailto:hola@prometh-ai.es?subject=Precio asesor',
    destacado: true,
  },
  {
    perfil: 'Empresa / Cliente',
    subtitulo: 'Para empresas con gestoría',
    precio: 'Incluido',
    descripcion: 'En el plan de tu gestoría',
    items: [
      'Portal cliente',
      'Visibilidad en tiempo real',
      'Alertas fiscales',
      'Documentos centralizados',
      'Chat con asesor',
    ],
    cta: 'Hablar con un asesor',
    href: 'mailto:hola@prometh-ai.es?subject=Informacion empresa',
  },
]

export default function Precios() {
  return (
    <PageLayout>
      <section className="pt-12 pb-20 px-4">
        <div className="max-w-3xl mx-auto text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-heading font-bold text-prometh-text mb-4">
            Planes y precios
          </h1>
          <p className="text-prometh-muted text-lg">
            Adaptados a cada perfil. Sin permanencia. Sin sorpresas.
          </p>
        </div>

        <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
          {planes.map(p => (
            <div key={p.perfil}
              className={`glass-card p-8 flex flex-col ${p.destacado ? 'border-prometh-amber/50' : ''}`}>
              {p.destacado && (
                <span className="text-xs font-bold bg-prometh-amber/20 text-prometh-amber px-2 py-1 rounded-full mb-4 self-start">
                  Más completo
                </span>
              )}
              <h2 className="text-xl font-heading font-bold text-prometh-text">{p.perfil}</h2>
              <p className="text-prometh-muted text-sm mb-4">{p.subtitulo}</p>
              <div className="mb-1">
                <span className="text-3xl font-heading font-bold gradient-text">{p.precio}</span>
              </div>
              <p className="text-prometh-muted text-xs mb-6">{p.descripcion}</p>
              <ul className="space-y-2 flex-1 mb-8">
                {p.items.map(item => (
                  <li key={item} className="flex items-center gap-2 text-sm text-prometh-muted">
                    <Check size={14} className="text-prometh-amber shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
              <a href={p.href}
                className={`flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm transition-colors ${
                  p.destacado ? 'btn-primary' : 'border border-prometh-border text-prometh-text hover:border-prometh-amber/50'
                }`}>
                {p.cta} <ArrowRight size={14} />
              </a>
            </div>
          ))}
        </div>

        <p className="text-center text-prometh-muted text-sm mt-8">
          ¿Necesitas algo específico?{' '}
          <a href="mailto:hola@prometh-ai.es" className="text-prometh-amber hover:text-prometh-amber-light">
            Escríbenos
          </a>{' '}
          y lo diseñamos juntos.
        </p>
      </section>
    </PageLayout>
  )
}
```

**Step 3: Verificar build completo**

```bash
npm run build
```
Esperado: 0 errores TypeScript, bundle generado en `dist/`.

**Step 4: Commit**

```bash
git add spice-landing/src/pages/Seguridad.tsx spice-landing/src/pages/Precios.tsx
git commit -m "feat: páginas /seguridad y /precios — arquitectura detallada + planes"
```

---

## Task 12: Deploy en prometh-ai.es

**Prerequisito:** DNS propagado + SSL activo (verificar `/tmp/certbot_done` en el servidor)

**Step 1: Actualizar nginx con HTTPS**

Cuando `/tmp/certbot_done` exista, añadir bloque HTTPS al nginx:

```bash
ssh carli@65.108.60.69 "cat > /opt/infra/nginx/conf.d/prometh-ai.conf << 'EOF'
# PROMETH-AI — prometh-ai.es

server {
    listen 80;
    listen [::]:80;
    server_name prometh-ai.es www.prometh-ai.es;
    location /.well-known/acme-challenge/ { root /opt/apps/spice-landing; }
    location / { return 301 https://prometh-ai.es\$request_uri; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name prometh-ai.es www.prometh-ai.es;

    ssl_certificate     /etc/letsencrypt/live/prometh-ai.es/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/prometh-ai.es/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # www → apex
    if (\$host = www.prometh-ai.es) { return 301 https://prometh-ai.es\$request_uri; }

    root /opt/apps/spice-landing;
    index index.html;
    location / { try_files \$uri \$uri/ /index.html; }
    location ~* \.(js|css|png|jpg|svg|ico|woff2)$ {
        expires 1y;
        add_header Cache-Control \"public, immutable\";
    }
}
EOF
docker exec nginx nginx -s reload && echo 'OK'"
```

**Step 2: Build local**

```bash
cd spice-landing
npm run build
```

**Step 3: Deploy al servidor**

```bash
rsync -av --delete spice-landing/dist/ carli@65.108.60.69:/opt/apps/spice-landing/
```

**Step 4: Verificar en el browser**

Abrir https://prometh-ai.es — verificar:
- [ ] SSL activo (candado verde)
- [ ] Home carga correctamente
- [ ] Navbar links funcionan
- [ ] Las 6 rutas responden
- [ ] Mobile responsive

**Step 5: Commit final**

```bash
git add spice-landing/
git commit -m "feat: deploy PROMETH-AI web en prometh-ai.es — multi-página completa"
```

---

## Resumen de tareas

| Task | Descripción | Tiempo est. |
|------|-------------|-------------|
| 1  | Setup react-router + estructura | 15 min |
| 2  | Brand tokens PROMETH-AI | 10 min |
| 3  | Logo SVG + SectionWrapper | 10 min |
| 4  | Navbar + Footer + PageLayout | 20 min |
| 5  | Home — Hero | 15 min |
| 6  | Home — SelectorPerfil | 15 min |
| 7  | Home — Métricas + Pasos + completo | 20 min |
| 8  | Página /gestorias | 20 min |
| 9  | Páginas /asesores + /clientes | 25 min |
| 10 | Página /como-funciona (migración) | 20 min |
| 11 | Páginas /seguridad + /precios | 20 min |
| 12 | Deploy prometh-ai.es | 15 min |

**Total estimado: ~3 horas de implementación**
