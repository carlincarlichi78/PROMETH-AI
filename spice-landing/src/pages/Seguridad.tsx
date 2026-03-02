import PageLayout from '../components/layout/PageLayout'
import { Shield, Lock, Users, Database, Server, FileCheck } from 'lucide-react'

const bloques = [
  {
    icono: Users,
    titulo: 'Multi-tenant con aislamiento total',
    items: [
      'Aislamiento por gestoria_id + empresa_id en cada query',
      'Un usuario nunca puede ver datos de otra gestoría',
      'JWT con gestoria_id firmado en cada request',
      'Verificación de acceso en todos los endpoints de la API',
    ],
  },
  {
    icono: Lock,
    titulo: 'Autenticación y acceso',
    items: [
      'JWT con expiración configurable (sessionStorage, no localStorage)',
      '2FA TOTP (Google Authenticator compatible)',
      'Lockout automático tras 5 intentos fallidos — 30 minutos',
      'Rate limiting separado: 5 login/min, protección anti-fuerza bruta',
    ],
  },
  {
    icono: Shield,
    titulo: 'Protección de datos',
    items: [
      "SSL/TLS Let's Encrypt + HSTS activo en todos los dominios",
      'Passwords con bcrypt (factor 12)',
      'Credenciales IMAP cifradas con Fernet',
      'Tokens RGPD de uso único con TTL 24h (nonce anti-replay)',
    ],
  },
  {
    icono: Database,
    titulo: 'Backups y disponibilidad',
    items: [
      'PostgreSQL 16 en servidor dedicado Hetzner (Nuremberg)',
      'Backups diarios automáticos a las 02:00',
      '6 bases PostgreSQL + 2 MariaDB + configs + certificados SSL',
      'Destino: Hetzner Object Storage Helsinki (separación geográfica)',
      'Retención: 7 diarios / 4 semanales / 12 mensuales',
    ],
  },
  {
    icono: Server,
    titulo: 'Infraestructura',
    items: [
      'Servidor Hetzner (Alemania/Finlandia) — GDPR compliant',
      'Firewall ufw activo + DOCKER-USER chain para contenedores',
      'Puertos internos bloqueados del exterior (PostgreSQL, Redis no expuestos)',
      'nginx hardened: server_tokens off, X-Frame-Options, X-Content-Type, Referrer-Policy, Permissions-Policy',
    ],
  },
  {
    icono: FileCheck,
    titulo: 'Cumplimiento RGPD',
    items: [
      'Exportación completa de datos en ZIP a petición del titular',
      'audit_log_seguridad: registro de todas las acciones críticas',
      'Política de retención configurable por gestoría',
      'Derecho al olvido implementado (borrado completo por empresa)',
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
