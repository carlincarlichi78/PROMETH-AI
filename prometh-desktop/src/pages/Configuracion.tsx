/**
 * Pantalla de configuración de conexión con PROMETH-AI.
 * El gestor introduce la URL de su instancia, el JWT y el secreto HMAC.
 */
import { useState, useEffect } from 'react'
import type { ConfigPromethAI } from '../../electron/config/prometh-ai.config'

type Estado = 'idle' | 'probando' | 'ok' | 'error'

interface FormConfig {
  apiUrl: string
  token: string
  webhookSecret: string
  empresasCif: string // separados por coma
}

export function Configuracion() {
  const [form, setForm] = useState<FormConfig>({
    apiUrl: '',
    token: '',
    webhookSecret: '',
    empresasCif: '',
  })
  const [estado, setEstado] = useState<Estado>('idle')
  const [guardado, setGuardado] = useState(false)

  // Cargar config guardada al montar
  useEffect(() => {
    window.electron.ipcRenderer
      .invoke('prometh-ai:config:leer')
      .then((cfg: ConfigPromethAI) => {
        setForm({
          apiUrl: cfg.apiUrl ?? '',
          token: cfg.token ?? '',
          webhookSecret: cfg.webhookSecret ?? '',
          empresasCif: (cfg.empresasCif ?? []).join(', '),
        })
      })
      .catch(() => {/* config no guardada aún */})
  }, [])

  const probarConexion = async () => {
    if (!form.apiUrl) return
    setEstado('probando')
    setGuardado(false)
    const { ok } = await window.electron.ipcRenderer.invoke(
      'prometh-ai:config:probar-conexion',
      form.apiUrl,
    )
    setEstado(ok ? 'ok' : 'error')
  }

  const guardar = async () => {
    const config: Partial<ConfigPromethAI> = {
      apiUrl: form.apiUrl.trim(),
      token: form.token.trim(),
      webhookSecret: form.webhookSecret.trim(),
      empresasCif: form.empresasCif
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean),
    }
    await window.electron.ipcRenderer.invoke('prometh-ai:config:guardar', config)
    setGuardado(true)
    setTimeout(() => setGuardado(false), 3000)
  }

  const campo = (key: keyof FormConfig, label: string, tipo = 'text', placeholder = '') => (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-gray-200">{label}</label>
      <input
        type={tipo}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        placeholder={placeholder}
        className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm"
      />
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Conexión PROMETH-AI</h1>
          <p className="text-sm text-gray-400 mt-1">
            Configura la conexión con tu instancia PROMETH-AI para sincronizar
            notificaciones AAPP y certificados digitales.
          </p>
        </div>

        <div className="space-y-4">
          {campo('apiUrl', 'URL de tu instancia', 'text', 'https://api.prometh-ai.es')}
          {campo('token', 'Token JWT (gestor)', 'password', 'eyJhbGciOiJIUzI1NiIs...')}
          {campo('webhookSecret', 'Secreto webhook HMAC', 'password', 'Generado en panel PROMETH-AI')}
          {campo('empresasCif', 'CIFs de empresas (separados por coma)', 'text', 'B12345678, A98765432')}
        </div>

        <div className="flex gap-3">
          <button
            onClick={probarConexion}
            disabled={estado === 'probando' || !form.apiUrl}
            className="flex-1 py-2 px-4 border border-gray-600 rounded-md text-sm font-medium text-gray-200 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {estado === 'probando' ? 'Probando...' : 'Probar conexión'}
          </button>
          <button
            onClick={guardar}
            disabled={estado !== 'ok'}
            className="flex-1 py-2 px-4 bg-amber-500 hover:bg-amber-600 disabled:bg-amber-500/30 disabled:cursor-not-allowed rounded-md text-sm font-medium text-white transition-colors"
          >
            Guardar
          </button>
        </div>

        {estado === 'ok' && (
          <p className="text-green-400 text-sm">✓ Conexión exitosa con {form.apiUrl}</p>
        )}
        {estado === 'error' && (
          <p className="text-red-400 text-sm">✗ No se pudo conectar. Verifica la URL.</p>
        )}
        {guardado && (
          <p className="text-amber-400 text-sm">✓ Configuración guardada correctamente</p>
        )}
      </div>
    </div>
  )
}
