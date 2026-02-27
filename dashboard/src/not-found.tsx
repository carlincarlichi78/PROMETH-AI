import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="text-muted-foreground">Pagina no encontrada</p>
      <Button asChild variant="outline"><Link to="/">Volver al inicio</Link></Button>
    </div>
  )
}
