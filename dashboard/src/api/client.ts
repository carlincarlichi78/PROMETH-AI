import type {
  Empresa,
  PyG,
  Balance,
  Asiento,
  Factura,
  Documento,
  Cuarentena,
  ActivoFijo,
  ProveedorCliente,
  Trabajador,
} from '../types'

/**
 * Cliente API tipado para el backend SFCE.
 * Usa fetch con Authorization Bearer JWT.
 */
export class ApiClient {
  private baseUrl = '/api'

  constructor(private getToken: () => string | null) {}

  /** GET generico con tipos */
  async get<T>(ruta: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    const url = new URL(`${this.baseUrl}${ruta}`, window.location.origin)

    // Anadir query params si existen
    if (params) {
      Object.entries(params).forEach(([clave, valor]) => {
        if (valor !== undefined && valor !== null) {
          url.searchParams.set(clave, String(valor))
        }
      })
    }

    const respuesta = await fetch(url.toString(), {
      headers: this._headers(),
    })
    return this._procesarRespuesta<T>(respuesta)
  }

  /** POST generico con tipos */
  async post<T>(ruta: string, body?: unknown): Promise<T> {
    const respuesta = await fetch(`${this.baseUrl}${ruta}`, {
      method: 'POST',
      headers: this._headers(),
      body: body ? JSON.stringify(body) : undefined,
    })
    return this._procesarRespuesta<T>(respuesta)
  }

  // --- Metodos tipados ---

  /** Listar todas las empresas del usuario */
  async listarEmpresas(): Promise<Empresa[]> {
    return this.get<Empresa[]>('/empresas')
  }

  /** Obtener detalle de una empresa */
  async obtenerEmpresa(id: number): Promise<Empresa> {
    return this.get<Empresa>(`/empresas/${id}`)
  }

  /** Cuenta de Perdidas y Ganancias */
  async obtenerPyG(
    empresaId: number,
    params?: { ejercicio?: string; hasta_fecha?: string }
  ): Promise<PyG> {
    return this.get<PyG>(`/empresas/${empresaId}/pyg`, params)
  }

  /** Balance de situacion */
  async obtenerBalance(
    empresaId: number,
    params?: { hasta_fecha?: string }
  ): Promise<Balance> {
    return this.get<Balance>(`/empresas/${empresaId}/balance`, params)
  }

  /** Libro diario (asientos) */
  async obtenerDiario(
    empresaId: number,
    params?: { desde?: string; hasta?: string; limit?: number; offset?: number }
  ): Promise<Asiento[]> {
    return this.get<Asiento[]>(`/empresas/${empresaId}/diario`, params)
  }

  /** Listado de facturas */
  async obtenerFacturas(
    empresaId: number,
    params?: { tipo?: string; pagada?: boolean }
  ): Promise<Factura[]> {
    return this.get<Factura[]>(`/empresas/${empresaId}/facturas`, params)
  }

  /** Documentos en pipeline */
  async obtenerDocumentos(
    empresaId: number,
    params?: { estado?: string; tipo_doc?: string }
  ): Promise<Documento[]> {
    return this.get<Documento[]>(`/empresas/${empresaId}/documentos`, params)
  }

  /** Documentos en cuarentena */
  async obtenerCuarentena(empresaId: number): Promise<Cuarentena[]> {
    return this.get<Cuarentena[]>(`/empresas/${empresaId}/cuarentena`)
  }

  /** Resolver un documento en cuarentena */
  async resolverCuarentena(
    empresaId: number,
    cuarentenaId: number,
    respuesta: string
  ): Promise<Cuarentena> {
    return this.post<Cuarentena>(
      `/empresas/${empresaId}/cuarentena/${cuarentenaId}/resolver`,
      { respuesta }
    )
  }

  /** Activos fijos */
  async obtenerActivos(empresaId: number): Promise<ActivoFijo[]> {
    return this.get<ActivoFijo[]>(`/empresas/${empresaId}/activos`)
  }

  /** Proveedores y clientes */
  async obtenerProveedores(empresaId: number): Promise<ProveedorCliente[]> {
    return this.get<ProveedorCliente[]>(`/empresas/${empresaId}/proveedores`)
  }

  /** Trabajadores */
  async obtenerTrabajadores(empresaId: number): Promise<Trabajador[]> {
    return this.get<Trabajador[]>(`/empresas/${empresaId}/trabajadores`)
  }

  // --- Helpers privados ---

  private _headers(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return headers
  }

  private async _procesarRespuesta<T>(respuesta: Response): Promise<T> {
    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => ({ detail: 'Error del servidor' }))
      throw new Error(error.detail ?? `Error HTTP ${respuesta.status}`)
    }
    return respuesta.json() as Promise<T>
  }
}
