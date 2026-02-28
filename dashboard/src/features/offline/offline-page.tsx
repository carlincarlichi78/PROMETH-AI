export default function OfflinePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-muted/30 gap-6 p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground font-bold text-3xl">
        S
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-bold text-foreground">Sin conexion</h1>
        <p className="text-muted-foreground max-w-sm">
          Tus datos estan seguros. Vuelve a conectarte para sincronizar.
        </p>
      </div>
      <button
        onClick={() => window.location.reload()}
        className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
      >
        Reintentar
      </button>
    </div>
  )
}
