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
