import { useAuth } from '@/context/AuthContext'

// Constantes de tier — mismo orden que sfce/core/tiers.py
export const TIER_BASICO   = 'basico'   as const
export const TIER_PRO      = 'pro'      as const
export const TIER_PREMIUM  = 'premium'  as const

export type TierValue = typeof TIER_BASICO | typeof TIER_PRO | typeof TIER_PREMIUM

const TIER_RANK: Record<TierValue, number> = {
  [TIER_BASICO]:  1,
  [TIER_PRO]:     2,
  [TIER_PREMIUM]: 3,
}

// Mismo mapa que sfce/core/tiers.py — mantener sincronizados
const FEATURES_EMPRESARIO: Record<string, TierValue> = {
  consultar:                TIER_BASICO,
  subir_docs:               TIER_PRO,
  app_movil:                TIER_PRO,
  firmar:                   TIER_PREMIUM,
  chat_gestor:              TIER_PREMIUM,
  advisor_premium:          TIER_PREMIUM,
  advisor_sector_brain:     TIER_PREMIUM,
  advisor_temporal_machine: TIER_PREMIUM,
  advisor_autopilot:        TIER_PREMIUM,
  advisor_simulador:        TIER_PREMIUM,
  advisor_informes:         TIER_PRO,
}

export function useTiene(feature: string): boolean {
  const { usuario } = useAuth()
  const requerido = FEATURES_EMPRESARIO[feature] ?? TIER_PREMIUM
  const actual = (usuario?.plan_tier ?? TIER_BASICO) as TierValue
  return (TIER_RANK[actual] ?? 1) >= (TIER_RANK[requerido] ?? 3)
}
