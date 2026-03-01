export interface SesionSalud {
  id: number
  fecha: string
  rama_git: string | null
  commit_hash: string | null
  tests_total: number
  tests_pass: number
  tests_fail: number
  cobertura_pct: number
  duracion_seg: number
  estado: string
}

export interface FalloTest {
  id: number
  sesion_id: number
  test_id: string
  nombre: string
  modulo: string | null
  error_msg: string | null
}

export interface CoberturaMod {
  id: number
  sesion_id: number
  modulo: string
  pct_cobertura: number
  lineas_cubiertas: number
  lineas_totales: number
}

export interface SesionDetalle extends SesionSalud {
  fallos: FalloTest[]
  cobertura: CoberturaMod[]
}

export interface Tendencias {
  sesiones: Array<{
    fecha: string
    tests_total: number
    tests_fail: number
    cobertura_pct: number
  }>
}
