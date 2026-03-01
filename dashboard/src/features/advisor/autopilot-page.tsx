// dashboard/src/features/advisor/autopilot-page.tsx
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, AlertCircle, CheckCircle, ChevronDown, ChevronUp, Bot } from 'lucide-react'
import { advisorApi } from './api'

type ItemBriefing = {
  empresa_id: number
  empresa_nombre: string
  urgencia: 'rojo' | 'amarillo' | 'verde'
  titulo: string
  descripcion: string
  acciones: string[]
  borrador_mensaje: string | null
}

const COLORES_URGENCIA = {
  rojo:     'var(--adv-rojo)',
  amarillo: 'var(--adv-accent)',
  verde:    'var(--adv-verde)',
}

const ICONOS_URGENCIA = {
  rojo:     AlertTriangle,
  amarillo: AlertCircle,
  verde:    CheckCircle,
}

function BriefingCard({ item }: { item: ItemBriefing }) {
  const [borradorAbierto, setBorradorAbierto] = useState(false)
  const color = COLORES_URGENCIA[item.urgencia]
  const IconoUrgencia = ICONOS_URGENCIA[item.urgencia]

  return (
    <div style={{
      background: 'var(--adv-surface)',
      border: `1px solid ${color}33`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 10,
      padding: '18px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
    }}>
      {/* Cabecera */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: `${color}22`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          <IconoUrgencia size={18} color={color} />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
            <span style={{
              fontSize: 11, fontWeight: 600, textTransform: 'uppercase',
              letterSpacing: '0.05em', color,
            }}>
              {item.urgencia}
            </span>
          </div>
          <h3 style={{ color: 'var(--adv-text)', fontSize: 15, fontWeight: 700, margin: '0 0 4px' }}>
            {item.empresa_nombre}
          </h3>
          <p style={{ color: 'var(--adv-text-muted)', fontSize: 13, margin: 0 }}>
            {item.titulo}
          </p>
        </div>
      </div>

      {/* Descripción */}
      <p style={{ color: 'var(--adv-text-muted)', fontSize: 12, margin: 0 }}>
        {item.descripcion}
      </p>

      {/* Acciones */}
      {item.acciones.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {item.acciones.map((accion, idx) => (
            <div key={idx} style={{
              display: 'flex', alignItems: 'flex-start', gap: 8,
              background: 'var(--adv-surface-2)', borderRadius: 6, padding: '8px 10px',
            }}>
              <span style={{ color, fontSize: 12, flexShrink: 0, marginTop: 1 }}>→</span>
              <span style={{ color: 'var(--adv-text)', fontSize: 13 }}>{accion}</span>
            </div>
          ))}
        </div>
      )}

      {/* Borrador mensaje */}
      {item.borrador_mensaje && (
        <div>
          <button
            onClick={() => setBorradorAbierto(v => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: 'var(--adv-accent)', fontSize: 13, fontWeight: 600, padding: 0,
            }}
          >
            {borradorAbierto ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {borradorAbierto ? 'Ocultar borrador' : 'Ver borrador de mensaje'}
          </button>
          {borradorAbierto && (
            <textarea
              defaultValue={item.borrador_mensaje}
              rows={8}
              style={{
                marginTop: 8,
                width: '100%',
                background: 'var(--adv-surface-2)',
                border: '1px solid var(--adv-border)',
                borderRadius: 6,
                color: 'var(--adv-text)',
                fontSize: 13,
                fontFamily: 'inherit',
                lineHeight: 1.6,
                padding: '10px 12px',
                resize: 'vertical',
                boxSizing: 'border-box',
              }}
            />
          )}
        </div>
      )}
    </div>
  )
}

export default function AutopilotPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['autopilot-briefing'],
    queryFn: () => advisorApi.autopilotBriefing(),
  })

  return (
    <div className="advisor-dark" style={{ minHeight: '100vh', background: 'var(--adv-bg)', padding: '32px 24px' }}>
      {/* Encabezado */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: 'var(--adv-surface)',
          border: '1px solid var(--adv-accent)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Bot size={20} color="var(--adv-accent)" />
        </div>
        <div>
          <h1 style={{ color: 'var(--adv-text)', fontSize: 22, fontWeight: 800, margin: 0 }}>
            Advisor Autopilot
          </h1>
          <p style={{ color: 'var(--adv-text-muted)', fontSize: 13, margin: 0 }}>
            Briefing semanal — empresas priorizadas por urgencia
          </p>
        </div>
      </div>

      {/* Fecha y resumen */}
      {data && (
        <div style={{
          display: 'flex', gap: 16, marginBottom: 24, marginTop: 20,
          flexWrap: 'wrap',
        }}>
          <div style={{
            background: 'var(--adv-surface)', borderRadius: 8, padding: '10px 16px',
            fontSize: 12, color: 'var(--adv-text-muted)',
          }}>
            Generado el {data.fecha}
          </div>
          <div style={{
            background: 'var(--adv-surface)', borderRadius: 8, padding: '10px 16px',
            fontSize: 12, color: 'var(--adv-text)',
          }}>
            <span style={{ fontWeight: 700 }}>{data.total_empresas}</span> empresas
          </div>
          {data.urgentes > 0 && (
            <div style={{
              background: 'var(--adv-rojo)22', border: '1px solid var(--adv-rojo)44',
              borderRadius: 8, padding: '10px 16px',
              fontSize: 12, color: 'var(--adv-rojo)', fontWeight: 700,
            }}>
              {data.urgentes} urgente{data.urgentes > 1 ? 's' : ''}
            </div>
          )}
        </div>
      )}

      {/* Estados */}
      {isLoading && (
        <div style={{ color: 'var(--adv-text-muted)', fontSize: 14, textAlign: 'center', paddingTop: 80 }}>
          Generando briefing…
        </div>
      )}

      {error && (
        <div style={{
          background: 'var(--adv-rojo)22', border: '1px solid var(--adv-rojo)44',
          borderRadius: 10, padding: '16px 20px',
          color: 'var(--adv-rojo)', fontSize: 14,
        }}>
          Error al cargar el briefing. Comprueba la conexión con el servidor.
        </div>
      )}

      {data && data.items.length === 0 && (
        <div style={{
          textAlign: 'center', paddingTop: 80,
          color: 'var(--adv-text-muted)', fontSize: 14,
        }}>
          No hay empresas asignadas en este momento.
        </div>
      )}

      {/* Lista de empresas */}
      {data && data.items.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 760 }}>
          {data.items.map(item => (
            <BriefingCard key={item.empresa_id} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
