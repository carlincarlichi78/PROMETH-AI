import { useAuth } from '@/context/AuthContext'

const TIER_RANK: Record<string, number> = { basico: 1, pro: 2, premium: 3 }

// Mismo mapa que sfce/core/tiers.py — mantener sincronizados
const FEATURES_EMPRESARIO: Record<string, string> = {
  consultar:   'basico',
  subir_docs:  'pro',
  app_movil:   'pro',
  firmar:      'premium',
  chat_gestor: 'premium',
}

export function useTiene(feature: string): boolean {
  const { usuario } = useAuth()
  const requerido = FEATURES_EMPRESARIO[feature] ?? 'premium'
  const actual = usuario?.plan_tier ?? 'basico'
  return (TIER_RANK[actual] ?? 1) >= (TIER_RANK[requerido] ?? 3)
}
