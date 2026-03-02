import { PageTitle } from '@/components/ui/page-title'

const INSTRUCCIONES = [
  { frase: '"100% IVA", "furgoneta de reparto", "uso exclusivo negocio"', efecto: 'IVA 100% deducible' },
  { frase: '"50% IVA", "uso mixto", "coche particular y negocio"', efecto: 'IVA 50% deducible' },
  { frase: '"sin IVA", "IVA 0%"', efecto: 'IVA 0% deducible' },
  { frase: '"es de Fulano", "para Mengano SL"', efecto: 'Asigna a la empresa mencionada' },
  { frase: '"es del año pasado", "diciembre 2024"', efecto: 'Imputa al ejercicio 2024' },
  { frase: '"es intracomunitaria", "de la UE"', efecto: 'Régimen intracomunitario' },
  { frase: '"es una importación", "viene de fuera de la UE"', efecto: 'Régimen importación' },
  { frase: '"gastos de representación"', efecto: 'Categoría: representación' },
  { frase: '"es urgente", "urge contabilizar"', efecto: 'Marca como urgente' },
]

const FLUJOS = [
  {
    titulo: 'Cliente envía directamente',
    desc: 'El cliente adjunta la factura y la envía al email de su empresa en PROMETH-AI.',
    ejemplo: 'Para: fulanosl+fv@prometh-ai.es\nAsunto: Factura enero\nAdjunto: factura_luz.pdf',
  },
  {
    titulo: 'Gestor reenvía con instrucciones',
    desc: 'La gestoría reenvía la factura e incluye instrucciones en el cuerpo.',
    ejemplo: 'Para: gestoria-lopez@prometh-ai.es\nCuerpo: "gasolina de Fulano, 100% IVA es furgoneta de reparto"\nAdjunto: gasolina.pdf',
  },
  {
    titulo: 'Gestor reenvía múltiples clientes',
    desc: 'Un email con facturas de varios clientes e instrucciones distintas por cliente.',
    ejemplo: 'Para: gestoria-lopez@prometh-ai.es\nCuerpo: "gasolina Fulano 100% IVA / luz Mengano normal"\nAdjuntos: gasolina.pdf, luz.pdf',
  },
]

export function GuiaCorreoPage() {
  return (
    <div className="p-6 max-w-3xl space-y-8">
      <PageTitle titulo="Guía de envío por email" />
      <p className="text-muted-foreground">
        Puedes enviar documentos a PROMETH-AI directamente por email. El sistema los procesa automáticamente
        y aplica las instrucciones contables que incluyas en el cuerpo del mensaje.
      </p>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Cómo enviar</h2>
        <div className="space-y-4">
          {FLUJOS.map((f, i) => (
            <div key={i} className="rounded border p-4 space-y-2">
              <h3 className="font-medium">{f.titulo}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
              <pre className="text-xs bg-muted p-3 rounded whitespace-pre-wrap">{f.ejemplo}</pre>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Instrucciones reconocidas</h2>
        <p className="text-sm text-muted-foreground">
          Escribe estas frases en el cuerpo del email para que el sistema aplique instrucciones especiales:
        </p>
        <div className="rounded border divide-y">
          {INSTRUCCIONES.map((inst, i) => (
            <div key={i} className="grid grid-cols-2 gap-4 p-3 text-sm">
              <code className="text-blue-700">{inst.frase}</code>
              <span className="text-muted-foreground">{inst.efecto}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">¿Qué pasa si hay ambigüedad?</h2>
        <p className="text-sm text-muted-foreground">
          Si el sistema no entiende bien alguna instrucción, el email aparecerá en
          la sección <strong>Emails recibidos</strong> con el botón <strong>Confirmar</strong>.
          Con un solo clic puedes revisar y confirmar las instrucciones detectadas.
          Las confirmaciones se aprenden automáticamente para futuros emails similares.
        </p>
      </section>
    </div>
  )
}
