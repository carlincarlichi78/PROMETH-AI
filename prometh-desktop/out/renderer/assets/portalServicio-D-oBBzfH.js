function resolverBaseUrl() {
  if (window.electronAPI?.isDesktop) return "https://www.carloscanetegomez.dev/certigestor/api";
  return "http://localhost:3000/api";
}
const PORTAL_BASE_URL = resolverBaseUrl();
function obtenerTokenPortal() {
  try {
    const raw = sessionStorage.getItem("portal_datos");
    if (!raw) return null;
    const datos = JSON.parse(raw);
    return datos.token ?? null;
  } catch {
    return null;
  }
}
function redirigirExpirado() {
  sessionStorage.removeItem("portal_datos");
  const base = "./".replace(/\/$/, "");
  window.location.href = `${base}/portal/expirado`;
}
async function peticionPortal(ruta) {
  const token = obtenerTokenPortal();
  if (!token) {
    redirigirExpirado();
    throw new Error("Sin token de portal");
  }
  const respuesta = await fetch(`${PORTAL_BASE_URL}/portal${ruta}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    }
  });
  if (respuesta.status === 401) {
    redirigirExpirado();
    throw new Error("Acceso expirado");
  }
  const datos = await respuesta.json();
  if (!respuesta.ok) {
    throw new Error(datos.error ?? "Error desconocido");
  }
  return datos;
}
const portalApiClient = {
  get: (ruta) => peticionPortal(ruta)
};
async function obtenerResumenPortalApi() {
  const respuesta = await portalApiClient.get("/resumen");
  return respuesta.datos;
}
async function listarCertificadosPortalApi(params) {
  const query = new URLSearchParams();
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const respuesta = await portalApiClient.get(`/certificados?${query}`);
  return {
    items: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function listarNotificacionesPortalApi(params) {
  const query = new URLSearchParams();
  if (params?.estado) query.set("estado", params.estado);
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const respuesta = await portalApiClient.get(`/notificaciones?${query}`);
  return {
    items: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function listarFirmasPortalApi(params) {
  const query = new URLSearchParams();
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const respuesta = await portalApiClient.get(`/firmas?${query}`);
  return {
    items: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function listarGestionesPortalApi(params) {
  const query = new URLSearchParams();
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const respuesta = await portalApiClient.get(`/gestiones?${query}`);
  return {
    items: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
export {
  listarNotificacionesPortalApi as a,
  listarFirmasPortalApi as b,
  listarGestionesPortalApi as c,
  listarCertificadosPortalApi as l,
  obtenerResumenPortalApi as o
};
