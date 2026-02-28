const TOKEN_KEY = 'sfce_token'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem(TOKEN_KEY)
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((opciones.headers as Record<string, string>) ?? {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const respuesta = await fetch(ruta, { ...opciones, headers })

  if (respuesta.status === 401) {
    sessionStorage.removeItem(TOKEN_KEY)
    window.location.href = '/login'
    throw new ApiError(401, 'Sesion expirada')
  }

  if (!respuesta.ok) {
    const error = await respuesta.json().catch(() => ({ detail: `Error HTTP ${respuesta.status}` }))
    throw new ApiError(respuesta.status, (error as { detail?: string }).detail ?? `Error ${respuesta.status}`)
  }

  return respuesta.json() as Promise<T>
}

export const api = {
  get: <T>(ruta: string) => fetchApi<T>(ruta),
  post: <T>(ruta: string, body: unknown) =>
    fetchApi<T>(ruta, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(ruta: string, body: unknown) =>
    fetchApi<T>(ruta, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(ruta: string) => fetchApi<T>(ruta, { method: 'DELETE' }),
}
