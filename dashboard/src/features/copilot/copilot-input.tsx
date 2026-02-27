// Copiloto IA — Input de mensaje
import { useState, useRef, type KeyboardEvent } from 'react'

interface Props {
  onEnviar: (mensaje: string) => void
  cargando: boolean
  placeholder?: string
}

export function CopilotInput({ onEnviar, cargando, placeholder = 'Pregunta sobre ratios, fiscal, facturas...' }: Props) {
  const [texto, setTexto] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const enviar = () => {
    const msg = texto.trim()
    if (!msg || cargando) return
    onEnviar(msg)
    setTexto('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      enviar()
    }
  }

  const handleInput = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
    }
  }

  return (
    <div style={{
      display: 'flex', gap: 8, alignItems: 'flex-end',
      padding: '10px 12px', borderTop: '1px solid #e5e7eb', background: '#fff',
    }}>
      <textarea
        ref={textareaRef}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder={placeholder}
        rows={1}
        disabled={cargando}
        style={{
          flex: 1, resize: 'none', border: '1px solid #e5e7eb', borderRadius: 8,
          padding: '8px 12px', fontSize: 14, fontFamily: 'inherit',
          outline: 'none', lineHeight: 1.5, overflowY: 'hidden',
          background: cargando ? '#f9fafb' : '#fff',
        }}
      />
      <button
        onClick={enviar}
        disabled={cargando || !texto.trim()}
        style={{
          width: 36, height: 36, borderRadius: 8, border: 'none',
          background: (!texto.trim() || cargando) ? '#f3f4f6' : '#1e293b',
          color: (!texto.trim() || cargando) ? '#9ca3af' : '#fff',
          cursor: (!texto.trim() || cargando) ? 'default' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0, transition: 'background 0.15s',
        }}
        title="Enviar (Enter)"
      >
        {cargando ? (
          <span style={{ fontSize: 16 }}>⏳</span>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
          </svg>
        )}
      </button>
    </div>
  )
}
