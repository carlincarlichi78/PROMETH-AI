import {
  Smartphone,
  BarChart3,
  Mail,
  Users,
} from 'lucide-react'
import { useInView } from '../../hooks/useInView'

interface PuntoTecnico {
  texto: string
}

interface Modulo {
  icono: React.ComponentType<{ size?: number; className?: string; strokeWidth?: number }>
  titulo: string
  subtitulo: string
  color: string
  puntos: PuntoTecnico[]
  etiqueta: string
}

const modulos: Modulo[] = [
  {
    icono: Smartphone,
    titulo: 'App Movil',
    subtitulo: 'Expo SDK 54 + React Native',
    color: '#60a5fa',
    etiqueta: 'Expo Router v3',
    puntos: [
      { texto: 'Expo Router v3 + autenticacion JWT via expo-secure-store' },
      { texto: 'Subida de documentos: camara + galeria (expo-image-picker)' },
      { texto: 'Vista empresario: sube docs + historial + notificaciones' },
      { texto: 'Vista gestor: lista empresas + gestion multi-empresa' },
      { texto: 'Formulario adaptativo por tipo de documento (Factura/Nomina/Extracto)' },
      { texto: 'Onboarding wizard en 3 pasos para nuevos clientes' },
    ],
  },
  {
    icono: BarChart3,
    titulo: 'Advisor Intelligence Platform',
    subtitulo: 'Star schema OLAP-lite + benchmarking sectorial',
    color: '#a78bfa',
    etiqueta: '6 dashboards',
    puntos: [
      { texto: 'Star schema OLAP-lite: fact_caja, fact_venta, fact_compra, fact_personal, alertas' },
      { texto: 'SectorEngine: clasificacion CNAE via YAML con fallback jerarquico' },
      { texto: 'BenchmarkEngine: percentiles P25/P50/P75 (minimo 5 empresas)' },
      { texto: 'Autopilot: briefing semanal generado automaticamente' },
      { texto: '6 dashboards: CommandCenter, Restaurant360, ProductIntelligence, SectorBrain, Autopilot, SalaEstrategia' },
      { texto: 'Guard de tier premium con overlay CTA upgrade' },
    ],
  },
  {
    icono: Mail,
    titulo: 'Email Ingestion',
    subtitulo: 'Daemon IMAP + pipeline automatico',
    color: '#34d399',
    etiqueta: 'Zoho Mail + IMAP',
    puntos: [
      { texto: 'Daemon IMAP que monitoriza buzones Zoho Mail en tiempo real' },
      { texto: 'Extractor de adjuntos: PDF, XML FacturaE, imagenes' },
      { texto: 'Parser FacturaE: XML v3.2.1 y v3.2.2 validado contra XSD' },
      { texto: 'Score de confianza por email + whitelist de remitentes conocidos' },
      { texto: 'ACK automatico al remitente tras procesar exitosamente' },
      { texto: 'Filtro anti-spam + deduplicacion por SHA256 de adjunto' },
    ],
  },
  {
    icono: Users,
    titulo: 'Onboarding Masivo',
    subtitulo: 'Alta de empresas en lote via PDF',
    color: '#fbbf24',
    etiqueta: 'OCR 036/037',
    puntos: [
      { texto: 'Carga de lotes de escrituras y modelos 036/037 en PDF' },
      { texto: 'OCR especializado: extrae CIF, denominacion, capital, administradores, regimen IVA' },
      { texto: 'Perfil de empresa generado automaticamente desde los documentos' },
      { texto: 'Workflow de revision + aprobacion por el gestor responsable' },
      { texto: 'Provisioning automatico en FacturaScripts (empresa + ejercicio + PGC)' },
      { texto: 'Acumulador de datos: consolida multiples PDFs de una misma empresa' },
    ],
  },
]

function TarjetaModulo({ modulo, indice }: { modulo: Modulo; indice: number }) {
  const { ref, visible } = useInView()
  const Icono = modulo.icono

  return (
    <div
      ref={ref}
      className="glass-card p-6 md:p-8 transition-all duration-700"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(32px)',
        transitionDelay: `${indice * 120}ms`,
      }}
    >
      {/* Cabecera */}
      <div className="flex items-start justify-between gap-4 mb-6">
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: `${modulo.color}15`, border: `1px solid ${modulo.color}30`, color: modulo.color }}
          >
            <Icono size={24} strokeWidth={1.5} />
          </div>
          <div>
            <h3 className="font-heading font-bold text-prometh-text text-lg leading-tight">
              {modulo.titulo}
            </h3>
            <p className="text-prometh-muted text-sm mt-0.5">{modulo.subtitulo}</p>
          </div>
        </div>

        {/* Etiqueta */}
        <span
          className="text-xs font-bold px-3 py-1 rounded-full shrink-0 hidden sm:block"
          style={{
            background: `${modulo.color}15`,
            color: modulo.color,
            border: `1px solid ${modulo.color}30`,
          }}
        >
          {modulo.etiqueta}
        </span>
      </div>

      {/* Puntos tecnicos */}
      <ul className="space-y-2.5">
        {modulo.puntos.map((punto) => (
          <li key={punto.texto} className="flex items-start gap-2.5">
            <div
              className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0"
              style={{ background: modulo.color }}
            />
            <span className="text-sm text-prometh-muted leading-relaxed">
              {punto.texto}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function ModulosNuevos() {
  const { ref, visible } = useInView()

  return (
    <section className="py-20 px-4">
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
            Modulos avanzados
          </span>
          <h2 className="text-3xl md:text-4xl font-heading font-bold text-prometh-text mb-3">
            Mas alla del pipeline documental
          </h2>
          <p className="text-prometh-muted text-base md:text-lg max-w-2xl mx-auto">
            Cuatro modulos que extienden la plataforma con capacidades moviles, analiticas, ingesta automatica y onboarding masivo.
          </p>
        </div>

        {/* Grid de modulos — 2x2 en desktop */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {modulos.map((modulo, i) => (
            <TarjetaModulo key={modulo.titulo} modulo={modulo} indice={i} />
          ))}
        </div>
      </div>
    </section>
  )
}
