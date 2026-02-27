import { useState, useEffect } from 'react'
import { Menu, X } from 'lucide-react'

const links = [
  { label: 'Proceso', href: '#proceso' },
  { label: 'Documentos', href: '#documentos' },
  { label: 'Territorios', href: '#territorios' },
  { label: 'Resultados', href: '#resultados' },
]

/** SVG llama pequena para el logo */
function LogoLlama({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <path
        d="M12 2C12 2 6 10 6 18c0 6 3 10 6 12 3-2 6-6 6-12 0-8-6-16-6-16z"
        fill="currentColor"
        opacity="0.9"
      />
      <path
        d="M12 8c0 0-3 5-3 11 0 4 1.5 6.5 3 8 1.5-1.5 3-4 3-8 0-6-3-11-3-11z"
        fill="#d4a017"
        opacity="0.7"
      />
    </svg>
  )
}

function scrollA(href: string) {
  const id = href.replace('#', '')
  const el = document.getElementById(id)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth' })
  }
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuAbierto, setMenuAbierto] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 50)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Cerrar menu mobile al hacer scroll
  useEffect(() => {
    if (!menuAbierto) return
    const cerrar = () => setMenuAbierto(false)
    window.addEventListener('scroll', cerrar, { passive: true })
    return () => window.removeEventListener('scroll', cerrar)
  }, [menuAbierto])

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 h-16 flex items-center transition-all duration-300 ${
        scrolled
          ? 'bg-spice-bg/80 backdrop-blur-md shadow-lg shadow-black/20'
          : 'bg-transparent'
      }`}
    >
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        {/* Logo */}
        <a
          href="#inicio"
          onClick={(e) => {
            e.preventDefault()
            scrollA('#inicio')
          }}
          className="flex items-center gap-1.5 group"
        >
          <LogoLlama className="w-5 h-7 text-spice-emerald group-hover:text-spice-emerald-light transition-colors" />
          <span className="text-xl font-heading font-bold text-spice-emerald group-hover:text-spice-emerald-light transition-colors">
            SPICE
          </span>
        </a>

        {/* Links desktop */}
        <ul className="hidden md:flex items-center gap-8">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                onClick={(e) => {
                  e.preventDefault()
                  scrollA(link.href)
                }}
                className="text-sm text-spice-text-muted hover:text-spice-emerald transition-colors font-body"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        {/* Boton hamburguesa mobile */}
        <button
          onClick={() => setMenuAbierto(!menuAbierto)}
          className="md:hidden text-spice-text-muted hover:text-spice-emerald transition-colors p-2"
          aria-label={menuAbierto ? 'Cerrar menu' : 'Abrir menu'}
        >
          {menuAbierto ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Panel slide-in mobile */}
      <div
        className={`fixed inset-0 top-16 z-40 md:hidden transition-all duration-300 ${
          menuAbierto ? 'opacity-100 visible' : 'opacity-0 invisible'
        }`}
      >
        {/* Fondo oscuro */}
        <div
          className="absolute inset-0 bg-black/60"
          onClick={() => setMenuAbierto(false)}
        />

        {/* Panel */}
        <div
          className={`absolute top-0 right-0 w-64 h-full bg-spice-bg/95 backdrop-blur-lg border-l border-spice-border transition-transform duration-300 ${
            menuAbierto ? 'translate-x-0' : 'translate-x-full'
          }`}
        >
          <ul className="flex flex-col gap-2 p-6 pt-8">
            {links.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  onClick={(e) => {
                    e.preventDefault()
                    scrollA(link.href)
                    setMenuAbierto(false)
                  }}
                  className="block py-3 px-4 text-spice-text-muted hover:text-spice-emerald hover:bg-white/5 rounded-lg transition-colors font-body"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </nav>
  )
}
