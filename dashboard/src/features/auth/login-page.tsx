import { useState, type FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from =
    (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setEnviando(true)
    try {
      await login(email, password)
      // Clientes solo acceden al portal, no al dashboard de contabilidad
      const token = sessionStorage.getItem('sfce_token') ?? ''
      let rol = ''
      try { rol = JSON.parse(atob(token.split('.')[1]!))?.rol ?? '' } catch { /* */ }
      const destino = rol === 'cliente' ? '/portal' : from
      navigate(destino, { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de autenticacion')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 login-bg">
      {/* Glow ambar de fondo */}
      <div className="login-glow" />

      <div className="relative z-10 w-full max-w-sm">
        {/* Logo y titulo */}
        <div className="text-center mb-8">
          <div className="logo-amber inline-flex h-16 w-16 items-center justify-center rounded-2xl font-bold text-2xl text-[oklch(0.13_0.015_50)] mx-auto mb-4 login-logo-glow">
            S
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-gradient">SFCE</h1>
          <p className="text-sm text-muted-foreground mt-1">Sistema Fiscal Contable Evolutivo</p>
        </div>

        {/* Formulario */}
        <div className="login-card rounded-2xl p-6 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Correo electronico</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="usuario@ejemplo.com"
                className="login-input"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Contrasena</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                placeholder="••••••••"
                className="login-input"
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" className="w-full h-10 text-sm font-medium" disabled={enviando}>
              {enviando ? 'Iniciando sesion...' : 'Iniciar sesion'}
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
