// dashboard/src/features/advisor/sector-brain.tsx
// Sector Brain — benchmarks anónimos colectivos por CNAE
import { useQuery } from '@tanstack/react-query'
import { advisorApi } from './api'

interface SectorBrainProps {
  empresaId: number
  kpi?: string
}

type ColorSemaforo = 'rojo' | 'amarillo' | 'verde'

const COLOR_SEMAFORO: Record<ColorSemaforo, string> = {
  rojo: 'var(--adv-rojo)',
  amarillo: 'var(--adv-accent)',
  verde: 'var(--adv-verde)',
}

function GaugeBarra({
  p25,
  p50,
  p75,
  valorEmpresa,
}: {
  p25: number
  p50: number
  p75: number
  valorEmpresa?: number
}) {
  const min = p25 * 0.6
  const max = p75 * 1.4
  const rango = max - min

  const toPos = (v: number) => Math.min(Math.max(((v - min) / rango) * 100, 0), 100)

  const posP25 = toPos(p25)
  const posP50 = toPos(p50)
  const posP75 = toPos(p75)
  const posEmpresa = valorEmpresa != null ? toPos(valorEmpresa) : null

  return (
    <div style={{ position: 'relative', marginTop: 24, marginBottom: 32 }}>
      {/* Barra base */}
      <div
        style={{
          height: 10,
          borderRadius: 5,
          background: 'var(--adv-surface-2)',
          position: 'relative',
          overflow: 'visible',
        }}
      >
        {/* Zona verde (P50–P75) */}
        <div
          style={{
            position: 'absolute',
            left: `${posP50}%`,
            width: `${posP75 - posP50}%`,
            height: '100%',
            background: 'var(--adv-verde)',
            opacity: 0.25,
          }}
        />
        {/* Zona amarilla (P25–P50) */}
        <div
          style={{
            position: 'absolute',
            left: `${posP25}%`,
            width: `${posP50 - posP25}%`,
            height: '100%',
            background: 'var(--adv-accent)',
            opacity: 0.25,
          }}
        />
      </div>

      {/* Marcadores P25, P50, P75 */}
      {[
        { pos: posP25, label: 'P25' },
        { pos: posP50, label: 'P50' },
        { pos: posP75, label: 'P75' },
      ].map(({ pos, label }) => (
        <div
          key={label}
          style={{
            position: 'absolute',
            left: `${pos}%`,
            top: -6,
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
          }}
        >
          <div
            style={{
              width: 2,
              height: 22,
              background: 'var(--adv-border)',
            }}
          />
          <span
            style={{
              fontSize: 9,
              color: 'var(--adv-text-muted)',
              whiteSpace: 'nowrap',
              marginTop: 2,
            }}
          >
            {label}
          </span>
        </div>
      ))}

      {/* Marcador empresa */}
      {posEmpresa != null && (
        <div
          style={{
            position: 'absolute',
            left: `${posEmpresa}%`,
            top: -10,
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            zIndex: 2,
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: '50%',
              background: 'var(--adv-accent)',
              border: '2px solid var(--adv-bg)',
              boxShadow: '0 0 6px var(--adv-accent)',
            }}
          />
          <span style={{ fontSize: 9, color: 'var(--adv-accent)', fontWeight: 700, whiteSpace: 'nowrap' }}>
            Tú
          </span>
        </div>
      )}
    </div>
  )
}

export function SectorBrain({ empresaId, kpi = 'ticket_medio' }: SectorBrainProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['sector-brain', empresaId, kpi],
    queryFn: () => advisorApi.sectorBrain(empresaId, kpi),
    staleTime: 1000 * 60 * 10,
  })

  if (isLoading) {
    return (
      <div
        style={{
          background: 'var(--adv-surface)',
          border: '1px solid var(--adv-border)',
          borderRadius: 12,
          padding: 20,
          color: 'var(--adv-text-muted)',
          fontSize: 13,
        }}
      >
        Cargando Sector Brain...
      </div>
    )
  }

  if (error || !data) {
    return (
      <div
        style={{
          background: 'var(--adv-surface)',
          border: '1px solid var(--adv-border)',
          borderRadius: 12,
          padding: 20,
          color: 'var(--adv-rojo)',
          fontSize: 13,
        }}
      >
        Error cargando Sector Brain
      </div>
    )
  }

  if (!data.disponible) {
    return (
      <div
        style={{
          background: 'var(--adv-surface)',
          border: '1px solid var(--adv-border)',
          borderRadius: 12,
          padding: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span style={{ fontSize: 16 }}>🧠</span>
          <span style={{ fontWeight: 600, color: 'var(--adv-text)', fontSize: 14 }}>Sector Brain</span>
        </div>
        <p style={{ color: 'var(--adv-text-muted)', fontSize: 12, margin: 0 }}>
          {data.razon ?? 'Datos insuficientes (mín. 5 empresas del mismo sector)'}
        </p>
      </div>
    )
  }

  const { percentiles_sector, valor_empresa, posicion, cnae } = data
  const color: ColorSemaforo = (posicion?.color as ColorSemaforo) ?? 'amarillo'
  const colorHex = COLOR_SEMAFORO[color]

  return (
    <div
      style={{
        background: 'var(--adv-surface)',
        border: '1px solid var(--adv-border)',
        borderRadius: 12,
        padding: 20,
      }}
    >
      {/* Cabecera */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 16 }}>🧠</span>
          <span style={{ fontWeight: 600, color: 'var(--adv-text)', fontSize: 14 }}>Sector Brain</span>
          {cnae && (
            <span
              style={{
                fontSize: 10,
                padding: '2px 7px',
                borderRadius: 4,
                background: 'var(--adv-surface-2)',
                color: 'var(--adv-text-muted)',
              }}
            >
              CNAE {cnae}
            </span>
          )}
        </div>
        {posicion && (
          <span
            style={{
              fontSize: 11,
              padding: '3px 10px',
              borderRadius: 20,
              background: colorHex + '22',
              color: colorHex,
              fontWeight: 600,
              border: `1px solid ${colorHex}44`,
            }}
          >
            {posicion.etiqueta}
          </span>
        )}
      </div>

      {/* KPI actual */}
      {valor_empresa != null && (
        <div style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 28, fontWeight: 700, color: colorHex }}>
            {valor_empresa.toFixed(2)}
          </span>
          <span style={{ fontSize: 12, color: 'var(--adv-text-muted)', marginLeft: 4 }}>
            {kpi.replace(/_/g, ' ')}
          </span>
        </div>
      )}

      {/* Gauge percentiles */}
      {percentiles_sector && (
        <GaugeBarra
          p25={percentiles_sector.p25}
          p50={percentiles_sector.p50}
          p75={percentiles_sector.p75}
          valorEmpresa={valor_empresa}
        />
      )}

      {/* Leyenda percentiles */}
      {percentiles_sector && (
        <div
          style={{
            display: 'flex',
            gap: 16,
            marginTop: 4,
            padding: '8px 0 0',
            borderTop: '1px solid var(--adv-border)',
          }}
        >
          {[
            { label: 'P25', value: percentiles_sector.p25 },
            { label: 'P50', value: percentiles_sector.p50 },
            { label: 'P75', value: percentiles_sector.p75 },
          ].map(({ label, value }) => (
            <div key={label} style={{ flex: 1 }}>
              <div style={{ fontSize: 10, color: 'var(--adv-text-muted)', marginBottom: 2 }}>{label}</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--adv-text)' }}>
                {value.toFixed(2)}
              </div>
            </div>
          ))}
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 10, color: 'var(--adv-text-muted)', marginBottom: 2 }}>Empresas</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--adv-text)' }}>
              {percentiles_sector.n_empresas}
            </div>
          </div>
        </div>
      )}

      {/* Mensaje posición */}
      {posicion && (
        <p style={{ fontSize: 11, color: 'var(--adv-text-muted)', marginTop: 10, marginBottom: 0 }}>
          Tu empresa está en el{' '}
          <strong style={{ color: colorHex }}>{posicion.etiqueta}</strong>{' '}
          del sector (percentil {posicion.percentil}).
        </p>
      )}
    </div>
  )
}

export default SectorBrain
