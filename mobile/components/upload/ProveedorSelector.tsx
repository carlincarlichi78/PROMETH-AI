// mobile/components/upload/ProveedorSelector.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, TextInput, ActivityIndicator, StyleSheet } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { Plus, Check, ArrowLeft } from 'lucide-react-native'

interface Proveedor {
  cif: string; nombre: string
  base_imponible?: string; total?: string
  nif_trabajador?: string; salario_bruto?: string; retencion_irpf?: string; cuota_ss?: string
  entidad?: string; iban?: string; periodo?: string; saldo_final?: string
  descripcion?: string; importe?: string
}

interface Props {
  empresaId: number
  onSeleccionar: (p: Proveedor) => void
  seleccionado: Proveedor | null
  obligatorio?: boolean
  tipoDoc?: string
}

interface CampoDef {
  key: keyof Proveedor
  label: string
  placeholder: string
  keyboard?: 'default' | 'decimal-pad' | 'email-address'
  autoCapitalize?: 'none' | 'characters' | 'words' | 'sentences'
  requerido?: boolean
}

const CAMPOS_POR_TIPO: Record<string, CampoDef[]> = {
  Factura: [
    { key: 'nombre',         label: 'Nombre / Razón social',  placeholder: 'Ej: Repsol Butano S.A.',  autoCapitalize: 'words',      requerido: true },
    { key: 'cif',            label: 'CIF / NIF',              placeholder: 'Ej: B12345678',           autoCapitalize: 'characters', requerido: true },
    { key: 'base_imponible', label: 'Base imponible',         placeholder: '0.00 €',                  keyboard: 'decimal-pad' },
    { key: 'total',          label: 'Total factura',          placeholder: '0.00 €',                  keyboard: 'decimal-pad',      requerido: true },
  ],
  Ticket: [
    { key: 'nombre',         label: 'Establecimiento',        placeholder: 'Ej: Mercadona',           autoCapitalize: 'words',      requerido: true },
    { key: 'cif',            label: 'CIF (si aparece)',       placeholder: 'Ej: B12345678',           autoCapitalize: 'characters' },
    { key: 'total',          label: 'Importe total',          placeholder: '0.00 €',                  keyboard: 'decimal-pad',      requerido: true },
  ],
  Nomina: [
    { key: 'nombre',         label: 'Nombre del trabajador',  placeholder: 'Ej: Juan García López',   autoCapitalize: 'words',      requerido: true },
    { key: 'cif',            label: 'NIF / NIE',              placeholder: 'Ej: 12345678A',           autoCapitalize: 'characters', requerido: true },
    { key: 'salario_bruto',  label: 'Salario bruto',          placeholder: '0.00 €',                  keyboard: 'decimal-pad',      requerido: true },
    { key: 'retencion_irpf', label: 'Retención IRPF (%)',     placeholder: 'Ej: 15',                  keyboard: 'decimal-pad' },
    { key: 'cuota_ss',       label: 'Cuota SS trabajador',    placeholder: '0.00 €',                  keyboard: 'decimal-pad' },
  ],
  Extracto: [
    { key: 'entidad',        label: 'Entidad bancaria',       placeholder: 'Ej: CaixaBank',           autoCapitalize: 'words',      requerido: true },
    { key: 'iban',           label: 'IBAN',                   placeholder: 'Ej: ES76 0049...',        autoCapitalize: 'characters' },
    { key: 'periodo',        label: 'Período',                placeholder: 'Ej: Enero 2025',          autoCapitalize: 'sentences',  requerido: true },
    { key: 'saldo_final',    label: 'Saldo final',            placeholder: '0.00 €',                  keyboard: 'decimal-pad' },
  ],
  Otro: [
    { key: 'descripcion',    label: 'Descripción',            placeholder: 'Describe el documento',   autoCapitalize: 'sentences',  requerido: true },
    { key: 'importe',        label: 'Importe (si aplica)',    placeholder: '0.00 €',                  keyboard: 'decimal-pad' },
  ],
}

function _normalizarTipo(t: string): string {
  const map: Record<string, string> = {
    'Nómina': 'Nomina', 'nomina': 'Nomina', 'Nomina': 'Nomina',
    'Factura': 'Factura', 'Ticket': 'Ticket',
    'Extracto': 'Extracto', 'Otro': 'Otro',
  }
  return map[t] ?? 'Factura'
}

function FormularioDatos({
  campos, obligatorio, mostrarAlerta, onConfirmar, onVolver, tieneVolver,
}: {
  campos: CampoDef[]; obligatorio: boolean; mostrarAlerta: boolean
  onConfirmar: (v: Proveedor) => void; onVolver?: () => void; tieneVolver: boolean
}) {
  const [vals, setVals] = useState<Record<string, string>>({})
  const set = (k: string, v: string) => setVals((p) => ({ ...p, [k]: v }))

  const puedeConfirmar = !obligatorio || campos
    .filter((c) => c.requerido)
    .every((c) => (vals[c.key as string] ?? '').trim().length > 0)

  return (
    <View style={s.container}>
      {mostrarAlerta && (
        <View style={s.alertaObligatorio}>
          <Text style={s.alertaTexto}>📸 Foto detectada — introduce los datos para mejorar el OCR</Text>
        </View>
      )}
      {campos.map((c, i) => (
        <View key={c.key as string} style={i > 0 ? { marginTop: 14 } : undefined}>
          <Text style={s.label}>
            {c.label}
            {obligatorio && c.requerido
              ? <Text style={{ color: '#ef4444' }}> *</Text>
              : <Text style={{ color: '#475569' }}> (opcional)</Text>}
          </Text>
          <TextInput
            style={s.input}
            placeholder={c.placeholder}
            placeholderTextColor="#475569"
            value={vals[c.key as string] ?? ''}
            onChangeText={(v) => set(c.key as string, v)}
            keyboardType={c.keyboard ?? 'default'}
            autoCapitalize={c.autoCapitalize ?? 'sentences'}
          />
        </View>
      ))}
      <TouchableOpacity
        style={[s.botonPrimario, !puedeConfirmar && s.botonDesactivado]}
        onPress={() => {
          if (!puedeConfirmar) return
          const res: Proveedor = { cif: '', nombre: '' }
          for (const c of campos) (res as Record<string, string>)[c.key as string] = (vals[c.key as string] ?? '').trim()
          onConfirmar(res)
        }}
        disabled={!puedeConfirmar}
        activeOpacity={0.8}
      >
        <Text style={s.botonPrimarioTexto}>Confirmar datos</Text>
      </TouchableOpacity>
      {onVolver && tieneVolver && (
        <TouchableOpacity style={s.botonVolver} onPress={onVolver} activeOpacity={0.7}>
          <ArrowLeft size={16} color="#64748b" />
          <Text style={s.botonVolverTexto}>Volver a la lista</Text>
        </TouchableOpacity>
      )}
    </View>
  )
}

export function ProveedorSelector({ empresaId, onSeleccionar, seleccionado, obligatorio = false, tipoDoc = 'Factura' }: Props) {
  const [modoNuevo, setModoNuevo] = useState(false)
  const tipo = _normalizarTipo(tipoDoc)
  const campos = CAMPOS_POR_TIPO[tipo] ?? CAMPOS_POR_TIPO['Factura']
  const usaFrecuentes = tipo === 'Factura' || tipo === 'Ticket'

  const { data, isLoading } = useQuery({
    queryKey: ['proveedores', empresaId],
    queryFn: () => apiFetch<{ proveedores: Array<{ cif: string; nombre: string }> }>(`/api/portal/${empresaId}/proveedores-frecuentes`),
    enabled: usaFrecuentes,
  })

  if (isLoading) return <ActivityIndicator color="#f59e0b" size="large" style={{ marginVertical: 28 }} />

  const proveedores = usaFrecuentes ? (data?.proveedores ?? []) : []

  if (!usaFrecuentes || modoNuevo || (obligatorio && proveedores.length === 0)) {
    return (
      <FormularioDatos
        campos={campos}
        obligatorio={obligatorio}
        mostrarAlerta={obligatorio}
        onConfirmar={(v) => { onSeleccionar(v); setModoNuevo(false) }}
        onVolver={usaFrecuentes ? () => setModoNuevo(false) : undefined}
        tieneVolver={proveedores.length > 0}
      />
    )
  }

  return (
    <View style={s.container}>
      <Text style={s.desc}>Proveedores frecuentes</Text>
      {proveedores.map((p) => (
        <TouchableOpacity
          key={p.cif ?? p.nombre}
          style={[s.card, seleccionado?.nombre === p.nombre && s.cardSeleccionada]}
          onPress={() => onSeleccionar(p)}
          activeOpacity={0.7}
        >
          <View style={{ flex: 1 }}>
            <Text style={s.cardNombre}>{p.nombre}</Text>
            {p.cif ? <Text style={s.cardCif}>{p.cif}</Text> : null}
          </View>
          {seleccionado?.nombre === p.nombre && <View style={s.checkCircle}><Check size={16} color="#0f172a" /></View>}
        </TouchableOpacity>
      ))}
      <TouchableOpacity style={s.botonNuevo} onPress={() => setModoNuevo(true)} activeOpacity={0.7}>
        <View style={s.plusCircle}><Plus size={22} color="#f59e0b" /></View>
        <View>
          <Text style={s.botonNuevoTitulo}>Otro proveedor</Text>
          <Text style={s.botonNuevoDesc}>Introducir datos manualmente</Text>
        </View>
      </TouchableOpacity>
    </View>
  )
}

const s = StyleSheet.create({
  container: { gap: 10 },
  desc: { fontSize: 15, color: '#64748b', marginBottom: 6 },
  alertaObligatorio: { backgroundColor: '#f59e0b22', borderRadius: 14, padding: 14, borderWidth: 1, borderColor: '#f59e0b55', marginBottom: 10 },
  alertaTexto: { fontSize: 14, color: '#fbbf24', lineHeight: 20 },
  label: { fontSize: 15, fontWeight: '600', color: '#cbd5e1', marginBottom: 8 },
  input: { backgroundColor: '#0f172a', borderRadius: 14, paddingHorizontal: 18, paddingVertical: 16, fontSize: 16, color: '#ffffff', borderWidth: 1, borderColor: '#334155' },
  card: { backgroundColor: '#1e293b', borderRadius: 16, padding: 20, flexDirection: 'row', alignItems: 'center', borderWidth: 2, borderColor: 'transparent' },
  cardSeleccionada: { borderColor: '#f59e0b' },
  cardNombre: { fontSize: 17, fontWeight: '700', color: '#f1f5f9' },
  cardCif: { fontSize: 13, color: '#64748b', marginTop: 3 },
  checkCircle: { width: 30, height: 30, borderRadius: 15, backgroundColor: '#f59e0b', alignItems: 'center', justifyContent: 'center' },
  botonNuevo: { backgroundColor: '#1e293b', borderRadius: 16, padding: 18, flexDirection: 'row', alignItems: 'center', gap: 14, borderWidth: 2, borderColor: '#334155', marginTop: 4 },
  plusCircle: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#f59e0b22', alignItems: 'center', justifyContent: 'center' },
  botonNuevoTitulo: { fontSize: 17, fontWeight: '700', color: '#f1f5f9' },
  botonNuevoDesc: { fontSize: 13, color: '#64748b', marginTop: 2 },
  botonPrimario: { backgroundColor: '#f59e0b', borderRadius: 14, paddingVertical: 20, alignItems: 'center', marginTop: 20 },
  botonDesactivado: { opacity: 0.4 },
  botonPrimarioTexto: { fontSize: 18, fontWeight: '800', color: '#0f172a' },
  botonVolver: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 14 },
  botonVolverTexto: { fontSize: 15, color: '#64748b', fontWeight: '600' },
})
