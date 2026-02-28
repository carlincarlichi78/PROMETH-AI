// Copiloto IA — Componente de mensaje individual
import type { MensajeCopilot } from '@/types/copilot'

interface Props {
  mensaje: MensajeCopilot
  onFeedback?: (valoracion: 1 | 5) => void
}

export function CopilotMessage({ mensaje, onFeedback }: Props) {
  const esUsuario = mensaje.rol === 'user'
  const fecha = new Date(mensaje.timestamp).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{
      display: 'flex',
      flexDirection: esUsuario ? 'row-reverse' : 'row',
      gap: 8, marginBottom: 16, alignItems: 'flex-start',
    }}>
      {/* Avatar */}
      <div style={{
        width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
        background: esUsuario ? '#1e293b' : '#f1f5f9',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700, color: esUsuario ? '#fff' : '#475569',
      }}>
        {esUsuario ? 'U' : 'AI'}
      </div>

      {/* Burbuja */}
      <div style={{ maxWidth: '82%' }}>
        <div style={{
          padding: '10px 14px',
          borderRadius: esUsuario ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
          background: esUsuario ? '#1e293b' : '#f8fafc',
          color: esUsuario ? '#fff' : '#1e293b',
          fontSize: 14, lineHeight: 1.55,
          border: esUsuario ? 'none' : '1px solid #e5e7eb',
        }}>
          {/* Texto del mensaje — soporta saltos de linea */}
          {mensaje.contenido.split('\n').map((linea, i) => (
            <span key={i}>
              {linea}
              {i < mensaje.contenido.split('\n').length - 1 && <br />}
            </span>
          ))}
        </div>

        {/* Datos enriquecidos: tablas */}
        {mensaje.datos_enriquecidos?.tablas?.map((tabla, ti) => (
          <div key={ti} style={{ marginTop: 8, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
            {tabla.titulo && <div style={{ padding: '8px 12px', borderBottom: '1px solid #e5e7eb', fontWeight: 600, fontSize: 13, color: '#374151' }}>{tabla.titulo}</div>}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                {tabla.filas.length > 0 && (
                  <thead>
                    <tr>
                      {Object.keys(tabla.filas[0] ?? {}).map((col) => (
                        <th key={col} style={{ padding: '6px 10px', textAlign: 'left', color: '#6b7280', fontWeight: 600, borderBottom: '1px solid #e5e7eb' }}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {tabla.filas.map((fila, ri) => (
                    <tr key={ri} style={{ borderBottom: '1px solid #f3f4f6' }}>
                      {Object.values(fila).map((val, ci) => (
                        <td key={ci} style={{ padding: '6px 10px', color: '#374151' }}>{String(val)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}

        {/* Links de accion */}
        {mensaje.datos_enriquecidos?.links && mensaje.datos_enriquecidos.links.length > 0 && (
          <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {mensaje.datos_enriquecidos.links.map((link, li) => (
              <a key={li} href={link.ruta} style={{ padding: '4px 12px', background: '#eff6ff', color: '#3b82f6', borderRadius: 20, fontSize: 12, textDecoration: 'none', fontWeight: 500 }}>
                {link.texto} →
              </a>
            ))}
          </div>
        )}

        {/* Footer: hora + feedback */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
          <span style={{ fontSize: 11, color: '#9ca3af' }}>{fecha}</span>
          {!esUsuario && onFeedback && (
            <div style={{ display: 'flex', gap: 4 }}>
              <button onClick={() => onFeedback(5)} title="Util" style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, opacity: 0.6, padding: '0 2px' }}>👍</button>
              <button onClick={() => onFeedback(1)} title="No util" style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, opacity: 0.6, padding: '0 2px' }}>👎</button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
