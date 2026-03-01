// mobile/components/upload/ProveedorSelector.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, TextInput, ActivityIndicator, StyleSheet } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { Plus, Check, ArrowLeft } from 'lucide-react-native'

interface Proveedor { cif: string; nombre: string; base_imponible?: string; total?: string }
interface Props {
  empresaId: number
  onSeleccionar: (p: Proveedor) => void
  seleccionado: Proveedor | null
  obligatorio?: boolean   // true = foto (campos requeridos), false = PDF (optativo)
}

export function ProveedorSelector({ empresaId, onSeleccionar, seleccionado, obligatorio = false }: Props) {
  const [modoNuevo, setModoNuevo] = useState(false)
  const [cif, setCif] = useState('')
  const [nombre, setNombre] = useState('')
  const [baseImponible, setBaseImponible] = useState('')
  const [total, setTotal] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['proveedores', empresaId],
    queryFn: () => apiFetch<{ proveedores: Proveedor[] }>(`/api/portal/${empresaId}/proveedores-frecuentes`),
  })

  if (isLoading) return <ActivityIndicator color="#f59e0b" size="large" style={{ marginVertical: 28 }} />

  const proveedores = data?.proveedores ?? []
  const puedeConfirmar = obligatorio ? nombre.trim().length > 0 && total.trim().length > 0 : true

  if (modoNuevo || (obligatorio && proveedores.length === 0)) {
    return (
      <View style={s.container}>
        {obligatorio && (
          <View style={s.alertaObligatorio}>
            <Text style={s.alertaTexto}>📸 Foto detectada — introduce los datos del documento para asegurar un OCR correcto</Text>
          </View>
        )}

        <Text style={s.label}>Nombre / Razón social {obligatorio ? '*' : ''}</Text>
        <TextInput style={s.input} placeholder="Ej: Repsol Butano S.A." placeholderTextColor="#475569" value={nombre} onChangeText={setNombre} />

        <Text style={[s.label, { marginTop: 14 }]}>CIF / NIF {!obligatorio ? '(opcional)' : ''}</Text>
        <TextInput style={s.input} placeholder="Ej: B12345678" placeholderTextColor="#475569" value={cif} onChangeText={setCif} autoCapitalize="characters" />

        <View style={s.fila}>
          <View style={{ flex: 1 }}>
            <Text style={s.label}>Base imponible {!obligatorio ? '(opt.)' : ''}</Text>
            <TextInput style={s.input} placeholder="0.00 €" placeholderTextColor="#475569" value={baseImponible} onChangeText={setBaseImponible} keyboardType="decimal-pad" />
          </View>
          <View style={{ width: 12 }} />
          <View style={{ flex: 1 }}>
            <Text style={s.label}>Total {obligatorio ? '*' : '(opt.)'}</Text>
            <TextInput style={s.input} placeholder="0.00 €" placeholderTextColor="#475569" value={total} onChangeText={setTotal} keyboardType="decimal-pad" />
          </View>
        </View>

        <TouchableOpacity
          style={[s.botonPrimario, !puedeConfirmar && s.botonDesactivado]}
          onPress={() => {
            if (puedeConfirmar) {
              onSeleccionar({ cif: cif.trim(), nombre: nombre.trim() || 'Sin nombre', base_imponible: baseImponible.trim(), total: total.trim() })
              setModoNuevo(false)
            }
          }}
          disabled={!puedeConfirmar}
          activeOpacity={0.8}
        >
          <Text style={s.botonPrimarioTexto}>Confirmar datos</Text>
        </TouchableOpacity>

        {!obligatorio && proveedores.length > 0 && (
          <TouchableOpacity style={s.botonVolver} onPress={() => setModoNuevo(false)} activeOpacity={0.7}>
            <ArrowLeft size={16} color="#64748b" />
            <Text style={s.botonVolverTexto}>Volver a la lista</Text>
          </TouchableOpacity>
        )}
      </View>
    )
  }

  return (
    <View style={s.container}>
      <Text style={s.desc}>Proveedores frecuentes</Text>
      {proveedores.map((p) => (
        <TouchableOpacity key={p.cif ?? p.nombre} style={[s.card, seleccionado?.nombre === p.nombre && s.cardSeleccionada]} onPress={() => onSeleccionar(p)} activeOpacity={0.7}>
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
  fila: { flexDirection: 'row', marginTop: 4 },
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
