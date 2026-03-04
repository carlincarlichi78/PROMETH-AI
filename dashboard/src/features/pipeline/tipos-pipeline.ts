// dashboard/src/features/pipeline/tipos-pipeline.ts

// ── Mapping empresas → gestorías ────────────────────────────────────────────
export interface EmpresaInfo {
  id: number
  nombre: string
  nombreCorto: string
}

export type GestoriaId = 'uralde' | 'gestoria_a' | 'javier'

export interface GestoriaConfig {
  id: GestoriaId
  nombre: string
  email: string
  color: string   // oklch
  colorRgb: string  // para CSS filter glow
}

export const GESTORIA_CONFIG: Record<GestoriaId, GestoriaConfig> = {
  uralde: {
    id: 'uralde',
    nombre: 'Uralde',
    email: 'sergio@prometh-ai.es',
    color: 'oklch(0.75 0.18 145)',
    colorRgb: '74, 222, 128',  // emerald-400
  },
  gestoria_a: {
    id: 'gestoria_a',
    nombre: 'Gestoria A',
    email: 'gestor1@prometh-ai.es',
    color: 'oklch(0.65 0.20 250)',
    colorRgb: '96, 165, 250',  // blue-400
  },
  javier: {
    id: 'javier',
    nombre: 'Javier',
    email: 'javier@prometh-ai.es',
    color: 'oklch(0.75 0.18 50)',
    colorRgb: '251, 146, 60',  // orange-400
  },
}

export const EMPRESAS_POR_GESTORIA: Record<GestoriaId, EmpresaInfo[]> = {
  uralde: [
    { id: 1,  nombre: 'PASTORINO COSTA DEL SOL S.L.',   nombreCorto: 'PASTORINO'    },
    { id: 2,  nombre: 'GERARDO GONZALEZ CALLEJON',       nombreCorto: 'GERARDO'      },
    { id: 3,  nombre: 'CHIRINGUITO SOL Y ARENA S.L.',    nombreCorto: 'CHIRINGUITO'  },
    { id: 4,  nombre: 'ELENA NAVARRO PRECIADOS',         nombreCorto: 'ELENA'        },
  ],
  gestoria_a: [
    { id: 5,  nombre: 'MARCOS RUIZ DELGADO',             nombreCorto: 'MARCOS'       },
    { id: 6,  nombre: 'RESTAURANTE LA MAREA S.L.',       nombreCorto: 'LA MAREA'     },
    { id: 7,  nombre: 'AURORA DIGITAL S.L.',             nombreCorto: 'AURORA'       },
    { id: 8,  nombre: 'CATERING COSTA S.L.',             nombreCorto: 'CATERING'     },
    { id: 9,  nombre: 'DISTRIBUCIONES LEVANTE S.L.',     nombreCorto: 'DISTRIB.'     },
  ],
  javier: [
    { id: 10, nombre: 'COMUNIDAD MIRADOR DEL MAR',       nombreCorto: 'COMUNIDAD'    },
    { id: 11, nombre: 'FRANCISCO MORA',                  nombreCorto: 'FRANMORA'     },
    { id: 12, nombre: 'GASTRO HOLDING S.L.',             nombreCorto: 'GASTRO'       },
    { id: 13, nombre: 'JOSE ANTONIO BERMUDEZ',           nombreCorto: 'BERMUDEZ'     },
  ],
}

// ── Colores por tipo de documento ────────────────────────────────────────────
export const COLOR_TIPO_DOC: Record<string, string> = {
  FC:      'oklch(0.75 0.18 145)',   // verde  — factura cliente
  FV:      'oklch(0.65 0.20 250)',   // azul   — factura proveedor
  NC:      'oklch(0.75 0.18 70)',    // ámbar  — nota crédito
  SUM:     'oklch(0.70 0.15 300)',   // morado — suministro
  IMP:     'oklch(0.75 0.18 200)',   // teal   — impuesto/modelo
  NOM:     'oklch(0.70 0.15 350)',   // rosa   — nómina
  BAN:     'oklch(0.75 0.10 210)',   // azul claro — banco
  default: 'oklch(0.78 0.15 70)',    // ámbar fallback
}

// ── Nodos del pipeline (en orden) ────────────────────────────────────────────
export const NODOS_PIPELINE = ['inbox', 'ocr', 'validacion', 'fs', 'asiento', 'done'] as const
export type NodoPipeline = typeof NODOS_PIPELINE[number]

export const NODO_LABEL: Record<NodoPipeline, string> = {
  inbox:     'INBOX',
  ocr:       'OCR',
  validacion:'VALID',
  fs:        'FS',
  asiento:   'ASIENTO',
  done:      'DONE',
}

export const FASES_A_NODO: Record<string, NodoPipeline> = {
  intake:             'ocr',
  pre_validacion:     'validacion',
  registro:           'fs',
  asientos:           'asiento',
  correccion:         'asiento',
  validacion_cruzada: 'asiento',
  salidas:            'asiento',
}

export function getNodoIndex(nodo: string): number {
  return NODOS_PIPELINE.indexOf(nodo as NodoPipeline)
}
