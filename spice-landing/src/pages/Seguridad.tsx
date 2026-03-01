import PageLayout from '../components/layout/PageLayout'
import { Shield, Lock, Users, Database, Server, FileCheck } from 'lucide-react'

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
      "TLS 1.2+ en todo el tráfico (Let's Encrypt)",
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
