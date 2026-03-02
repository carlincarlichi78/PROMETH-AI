import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CuentaCorreo {
  id: number
  nombre: string
  tipo_cuenta: string
  usuario: string
  servidor: string | null
  activa: boolean
  ultimo_uid: number
  empresa_id: number | null
  gestoria_id: number | null
}

interface Props {
  cuenta: CuentaCorreo
  onDesactivar: (id: number) => void
}

const TIPO_LABEL: Record<string, string> = {
  dedicada: "Catch-all",
  gestoria: "Gestoría",
  sistema: "Sistema",
  empresa: "Empresa",
}

const TIPO_COLOR: Record<string, string> = {
  dedicada: "bg-blue-100 text-blue-800",
  gestoria: "bg-green-100 text-green-800",
  sistema: "bg-gray-100 text-gray-700",
  empresa: "bg-amber-100 text-amber-800",
}

export function CuentaCorreoCard({ cuenta, onDesactivar }: Props) {
  return (
    <Card className="border border-border/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{cuenta.nombre}</CardTitle>
          <div className="flex gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TIPO_COLOR[cuenta.tipo_cuenta] ?? ""}`}>
              {TIPO_LABEL[cuenta.tipo_cuenta] ?? cuenta.tipo_cuenta}
            </span>
            <Badge variant={cuenta.activa ? "default" : "secondary"}>
              {cuenta.activa ? "Activa" : "Inactiva"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{cuenta.usuario}</p>
        {cuenta.servidor && (
          <p className="text-xs text-muted-foreground mt-0.5">{cuenta.servidor}</p>
        )}
        <p className="text-xs text-muted-foreground mt-1">Último UID: {cuenta.ultimo_uid}</p>
        {cuenta.activa && (
          <Button
            variant="ghost"
            size="sm"
            className="mt-2 text-red-600 hover:text-red-700"
            onClick={() => onDesactivar(cuenta.id)}
          >
            Desactivar
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
