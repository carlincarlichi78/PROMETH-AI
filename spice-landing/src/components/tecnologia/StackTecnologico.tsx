import {
  Server,
  Monitor,
  Brain,
  Cloud,
  Shield,
  FlaskConical,
} from 'lucide-react'
import { useInView } from '../../hooks/useInView'

interface TecnologiaItem {
  nombre: string
  detalle?: string
}

interface Categoria {
  icono: React.ComponentType<{ size?: number; className?: string; strokeWidth?: number }>
  titulo: string
  color: string
  items: TecnologiaItem[]
}

const categorias: Categoria[] = [
  {
    icono: Server,
    titulo: 'Backend',
    color: '#f59e0b',
    items: [
      { nombre: 'FastAPI', detalle: 'Python 3.12' },
      { nombre: 'SQLAlchemy 2.0', detalle: 'ORM async' },
      { nombre: 'PostgreSQL 16', detalle: 'Base de datos' },
      { nombre: 'Uvicorn', detalle: 'ASGI server' },
      { nombre: 'Alembic', detalle: 'Migraciones' },
      { nombre: 'Pydantic v2', detalle: 'Validacion' },
    ],
  },
  {
    icono: Monitor,
    titulo: 'Frontend',
    color: '#60a5fa',
    items: [
      { nombre: 'React 18', detalle: 'TypeScript strict' },
      { nombre: 'Vite 6', detalle: 'Bundler' },
      { nombre: 'Tailwind CSS v4', detalle: 'Estilos' },
      { nombre: 'shadcn/ui + Radix', detalle: 'Componentes' },
      { nombre: 'TanStack Query v5', detalle: 'Server state' },
      { nombre: 'Zustand', detalle: 'Client state' },
    ],
  },
  {
    icono: Brain,
    titulo: 'IA / OCR',
    color: '#a78bfa',
    items: [
      { nombre: 'Mistral OCR3', detalle: 'Tier 0 — primario' },
      { nombre: 'GPT-4o', detalle: 'Tier 1 — fallback' },
      { nombre: 'Gemini Flash', detalle: 'Tier 2 — consenso' },
      { nombre: 'pdfplumber', detalle: 'Extraccion PDF' },
      { nombre: 'Cache SHA256', detalle: 'OCR sin repetir' },
      { nombre: 'Motor reglas 6 niveles', detalle: 'YAML jerarquico' },
    ],
  },
  {
    icono: Cloud,
    titulo: 'Infraestructura',
    color: '#34d399',
    items: [
      { nombre: 'Docker + Compose', detalle: 'Contenedores' },
      { nombre: 'GitHub Actions', detalle: 'CI/CD' },
      { nombre: 'Nginx', detalle: 'Proxy reverso' },
      { nombre: "Let's Encrypt", detalle: 'TLS automatico' },
      { nombre: 'Hetzner VPS', detalle: 'Alemania / GDPR' },
      { nombre: 'Uptime Kuma', detalle: 'Monitorizacion' },
    ],
  },
  {
    icono: Shield,
    titulo: 'Seguridad',
    color: '#f87171',
    items: [
      { nombre: 'JWT RS256', detalle: 'Autenticacion' },
      { nombre: '2FA TOTP', detalle: 'Google Authenticator' },
      { nombre: 'bcrypt', detalle: 'Factor 12' },
      { nombre: 'Fernet AES-128', detalle: 'Credenciales IMAP' },
      { nombre: 'Rate limiting', detalle: 'Por IP y usuario' },
      { nombre: 'RGPD Export ZIP', detalle: 'Derecho al olvido' },
    ],
  },
  {
    icono: FlaskConical,
    titulo: 'Calidad',
    color: '#fbbf24',
    items: [
      { nombre: '2.413 tests PASS', detalle: 'pytest' },
      { nombre: '75+ endpoints', detalle: 'API REST' },
      { nombre: '39 tablas BD', detalle: 'Esquema normalizado' },
      { nombre: 'Cache OCR SHA256', detalle: '0 reprocesados' },
      { nombre: 'CHANGELOG sesiones', detalle: 'Trazabilidad total' },
      { nombre: 'Expo SDK 54', detalle: 'App movil' },
    ],
  },
]

function TarjetaCategoria({ cat, indice }: { cat: Categoria; indice: number }) {
  const { ref, visible } = useInView()
  const Icono = cat.icono

  return (
    <div
      ref={ref}
      className="glass-card p-6 transition-all duration-600"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(24px)',
        transitionDelay: `${indice * 100}ms`,
      }}
    >
      {/* Cabecera */}
      <div className="flex items-center gap-3 mb-5">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${cat.color}18`, border: `1px solid ${cat.color}30`, color: cat.color }}
        >
          <Icono size={20} strokeWidth={1.5} />
        </div>
        <h3 className="font-heading font-bold text-prometh-text">{cat.titulo}</h3>
      </div>

      {/* Lista de items */}
      <ul className="space-y-2.5">
        {cat.items.map((item) => (
          <li key={item.nombre} className="flex items-center justify-between gap-2">
            <span className="text-sm text-prometh-text font-medium">{item.nombre}</span>
            {item.detalle && (
              <span className="text-xs text-prometh-muted shrink-0">{item.detalle}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function StackTecnologico() {
  const { ref, visible } = useInView()

  return (
    <section id="stack" className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Titulo */}
        <div
          ref={ref}
          className="text-center mb-12 transition-all duration-600"
          style={{
            opacity: visible ? 1 : 0,
            transform: visible ? 'translateY(0)' : 'translateY(24px)',
          }}
        >
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-4 uppercase tracking-widest">
            Stack tecnologico
          </span>
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            Cada capa, elegida con criterio
          </h2>
          <p className="text-prometh-muted text-base md:text-lg max-w-2xl mx-auto">
            Tecnologias de produccion battle-tested, sin dependencias experimentales.
            Todo en contenedores Docker con CI/CD automatizado.
          </p>
        </div>

        {/* Grid de categorias */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categorias.map((cat, i) => (
            <TarjetaCategoria key={cat.titulo} cat={cat} indice={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
