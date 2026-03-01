import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

function _rolDesdeToken(token: string): string {
  try {
    return JSON.parse(atob(token.split('.')[1]!))?.rol ?? ''
  } catch {
    return ''
  }
}

export default function AceptarInvitacionPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const { loginConToken } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!token) {
      setError('El enlace de invitacion no contiene un token valido.')
      return
    }
    if (password.length < 8) {
      setError('La contrasena debe tener al menos 8 caracteres.')
      return
    }
    if (password !== confirmar) {
      setError('Las contrasenas no coinciden.')
      return
    }

    setEnviando(true)
    try {
      const respuesta = await fetch('/api/auth/aceptar-invitacion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      })

      if (!respuesta.ok) {
        const datos = await respuesta.json().catch(() => ({}))
        if (respuesta.status === 410) {
          throw new Error('El enlace ha expirado. Solicita una nueva invitacion.')
        }
        if (respuesta.status === 404) {
          throw new Error('Enlace no valido o ya utilizado.')
        }
        throw new Error(datos.detail ?? 'Error al activar la cuenta.')
      }

      const datos = await respuesta.json()
      await loginConToken(datos.access_token)
      const rol = _rolDesdeToken(datos.access_token)
      if (rol === 'cliente') {
        // Verificar si la empresa asignada necesita onboarding
        try {
          const miResp = await fetch('/api/auth/me', {
            headers: { Authorization: `Bearer ${datos.access_token}` },
          })
          const miDatos = await miResp.json()
          const empresaId = miDatos.empresas_asignadas?.[0]
          if (empresaId) {
            const onbResp = await fetch(`/api/onboarding/cliente/${empresaId}`, {
              headers: { Authorization: `Bearer ${datos.access_token}` },
            })
            const onb = await onbResp.json()
            if (onb.estado === 'pendiente_cliente') {
              navigate(`/onboarding/cliente/${empresaId}`, { replace: true })
              return
            }
          }
        } catch { /* ignorar, navegar a portal normal */ }
        navigate('/portal', { replace: true })
      } else {
        navigate('/', { replace: true })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error inesperado.')
    } finally {
      setEnviando(false)
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 login-bg">
        <div className="login-glow" />
        <div className="relative z-10 w-full max-w-sm text-center">
          <p className="text-destructive text-sm">Enlace de invitacion no valido.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 login-bg">
      <div className="login-glow" />

      <div className="relative z-10 w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="logo-amber inline-flex h-16 w-16 items-center justify-center rounded-2xl font-bold text-2xl text-[oklch(0.13_0.015_50)] mx-auto mb-4 login-logo-glow">
            S
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-gradient">SFCE</h1>
          <p className="text-sm text-muted-foreground mt-1">Activa tu cuenta</p>
        </div>

        <div className="login-card rounded-2xl p-6 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="password">Nueva contrasena</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Minimo 8 caracteres"
                className="login-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="confirmar">Confirmar contrasena</Label>
              <Input
                id="confirmar"
                type="password"
                value={confirmar}
                onChange={(e) => setConfirmar(e.target.value)}
                required
                autoComplete="new-password"
                placeholder="Repite la contrasena"
                className="login-input"
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" className="w-full h-10 text-sm font-medium" disabled={enviando}>
              {enviando ? 'Activando cuenta...' : 'Activar cuenta'}
            </Button>
          </form>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-6">
          Gestionado con seguridad · SFCE v2
        </p>
      </div>
    </div>
  )
}
