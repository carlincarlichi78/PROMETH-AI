// Portal Cliente — índice de empresas accesibles para el usuario
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent } from '@/components/ui/card'
import { Building2, ArrowRight, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface EmpresaPortal {
  id: number
  nombre: string
  ejercicio: string | null
}

const CLAVE_TOKEN = 'sfce_token'

async function fetchMisEmpresas(token: string): Promise<{ empresas: EmpresaPortal[] }> {
  const res = await fetch('/api/portal/mis-empresas', {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export default function MisEmpresasPage() {
  const navigate = useNavigate()
  const token = sessionStorage.getItem(CLAVE_TOKEN)

  const [empresas, setEmpresas] = useState<EmpresaPortal[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      navigate('/login', { replace: true })
      return
    }
    setCargando(true)
    fetchMisEmpresas(token)
      .then((data) => {
        const lista = data.empresas ?? []
        // Redirección automática si solo hay una empresa
        if (lista.length === 1 && lista[0]) {
          navigate(`/portal/${lista[0].id}`, { replace: true })
          return
        }
        setEmpresas(lista)
        setCargando(false)
      })
      .catch((err: Error) => {
        if (err.message === '401') {
          sessionStorage.removeItem(CLAVE_TOKEN)
          navigate('/login', { replace: true })
        } else {
          setError('No se pudieron cargar las empresas.')
          setCargando(false)
        }
      })
  }, [token, navigate])

  if (cargando) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-sm text-muted-foreground">Cargando...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md space-y-4">
        <h1 className="text-xl font-bold text-center mb-6">Mis empresas</h1>

        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {!error && empresas.length === 0 && (
          <p className="text-sm text-center text-muted-foreground py-8">
            No tienes empresas asignadas. Contacta con tu gestor.
          </p>
        )}

        {empresas.map((e) => (
          <Card
            key={e.id}
            className="cursor-pointer hover:shadow-md transition-shadow"
            onClick={() => navigate(`/portal/${e.id}`)}
          >
            <CardContent className="flex items-center justify-between py-4 px-5">
              <div className="flex items-center gap-3">
                <Building2 className="h-5 w-5 text-slate-400" />
                <div>
                  <p className="font-medium text-sm">{e.nombre}</p>
                  {e.ejercicio && (
                    <p className="text-xs text-muted-foreground">Ejercicio {e.ejercicio}</p>
                  )}
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-slate-400" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
