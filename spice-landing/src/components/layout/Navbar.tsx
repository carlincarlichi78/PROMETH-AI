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
          <a href="https://app.prometh-ai.es"
            className="text-sm font-semibold text-prometh-amber hover:text-prometh-amber/80 transition-colors">
            Acceder →
          </a>
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
          <a href="https://app.prometh-ai.es"
            className="text-sm font-semibold text-prometh-amber py-2">
            Acceder →
          </a>
          <a href="mailto:hola@prometh-ai.es" className="btn-primary text-center text-sm">
            Solicitar demo
          </a>
        </div>
      )}
    </nav>
  )
}
