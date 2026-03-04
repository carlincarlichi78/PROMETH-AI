const TOKEN_KEY = 'sfce_token'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(ruta: string, opciones: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem(TOKEN_KEY)
  const esFormData = opciones.body instanceof FormData
  const headers: Record<string, string> = {
    // No añadir Content-Type para FormData (el browser lo pone con el boundary)
    ...(esFormData ? {} : { 'Content-Type': 'application/json' }),
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
    const detail = (error as { detail?: unknown }).detail
    const mensaje = Array.isArray(detail)
      ? detail.map((e: { msg?: string }) => e.msg ?? String(e)).join(', ')
      : (typeof detail === 'string' ? detail : `Error ${respuesta.status}`)
    throw new ApiError(respuesta.status, mensaje)
  }

  return respuesta.json() as Promise<T>
}

export const api = {
  get: <T>(ruta: string) => fetchApi<T>(ruta),
  post: <T>(ruta: string, body: unknown) =>
    fetchApi<T>(ruta, { method: 'POST', body: JSON.stringify(body) }),
  postForm: <T>(ruta: string, formData: FormData) =>
    fetchApi<T>(ruta, { method: 'POST', body: formData }),
  put: <T>(ruta: string, body: unknown) =>
    fetchApi<T>(ruta, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(ruta: string, body: unknown) =>
    fetchApi<T>(ruta, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(ruta: string) => fetchApi<T>(ruta, { method: 'DELETE' }),
}
