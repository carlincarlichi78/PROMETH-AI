// mobile/components/upload/ProveedorSelector.tsx
import { useState } from 'react'
import { View, Text, TouchableOpacity, TextInput, ActivityIndicator } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/hooks/useApi'
import { Plus, Check } from 'lucide-react-native'

interface Proveedor { cif: string; nombre: string; tipo_doc_sugerido?: string }

interface Props {
  empresaId: number
  onSeleccionar: (p: Proveedor) => void
  seleccionado: Proveedor | null
}

export function ProveedorSelector({ empresaId, onSeleccionar, seleccionado }: Props) {
  const [modoNuevo, setModoNuevo] = useState(false)
  const [cifNuevo, setCifNuevo] = useState('')
  const [nombreNuevo, setNombreNuevo] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['proveedores', empresaId],
    queryFn: () => apiFetch<{ proveedores: Proveedor[] }>(`/api/portal/${empresaId}/proveedores-frecuentes`),
  })

  if (isLoading) return <ActivityIndicator color="#fbbf24" className="py-4" />

  const proveedores = data?.proveedores ?? []

  if (modoNuevo) {
    return (
      <View className="gap-3">
        <Text className="text-slate-300 text-sm font-medium">Nuevo proveedor</Text>
        <TextInput
          className="bg-slate-800 text-white rounded-xl px-4 py-3"
          placeholder="CIF / NIF (ej: B12345678)"
          placeholderTextColor="#64748b"
          value={cifNuevo}
          onChangeText={setCifNuevo}
          autoCapitalize="characters"
        />
        <TextInput
          className="bg-slate-800 text-white rounded-xl px-4 py-3"
          placeholder="Nombre o razón social"
          placeholderTextColor="#64748b"
          value={nombreNuevo}
          onChangeText={setNombreNuevo}
        />
        <TouchableOpacity
          className="bg-amber-400 rounded-xl py-3 items-center"
          onPress={() => {
            if (nombreNuevo.trim()) {
              onSeleccionar({ cif: cifNuevo.trim(), nombre: nombreNuevo.trim() })
              setModoNuevo(false)
            }
          }}
        >
          <Text className="text-slate-900 font-semibold">Usar este proveedor</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => setModoNuevo(false)}>
          <Text className="text-slate-400 text-center text-sm">← Volver a la lista</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <View className="gap-3">
      {proveedores.map((p) => (
        <TouchableOpacity
          key={p.cif ?? p.nombre}
          className={`flex-row items-center gap-3 bg-slate-900 rounded-xl px-4 py-3 ${seleccionado?.nombre === p.nombre ? 'border border-amber-400' : ''}`}
          onPress={() => onSeleccionar(p)}
        >
          {seleccionado?.nombre === p.nombre && <Check size={16} color="#fbbf24" />}
          <View className="flex-1">
            <Text className="text-white font-medium">{p.nombre}</Text>
            {p.cif && <Text className="text-slate-400 text-xs">{p.cif}</Text>}
          </View>
        </TouchableOpacity>
      ))}
      <TouchableOpacity
        className="flex-row items-center gap-2 border border-dashed border-slate-600 rounded-xl px-4 py-3"
        onPress={() => setModoNuevo(true)}
      >
        <Plus size={16} color="#94a3b8" />
        <Text className="text-slate-400">Añadir nuevo proveedor</Text>
      </TouchableOpacity>
    </View>
  )
}
