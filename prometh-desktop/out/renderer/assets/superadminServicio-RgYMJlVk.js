import { d as apiClient } from "./index-DMbE3NR1.js";
async function listarOrganizacionesApi(params) {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([clave, valor]) => {
      if (valor) query.set(clave, valor);
    });
  }
  const queryStr = query.toString();
  const ruta = queryStr ? `/superadmin/organizaciones?${queryStr}` : "/superadmin/organizaciones";
  const respuesta = await apiClient.get(ruta);
  return {
    organizaciones: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function actualizarOrganizacionApi(id, datos) {
  const respuesta = await apiClient.patch(`/superadmin/organizaciones/${id}`, datos);
  return respuesta.datos;
}
async function crearOrganizacionApi(datos) {
  const respuesta = await apiClient.post("/superadmin/organizaciones", datos);
  return respuesta.datos;
}
async function listarUsuariosGlobalApi(params) {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([clave, valor]) => {
      if (valor) query.set(clave, valor);
    });
  }
  const queryStr = query.toString();
  const ruta = queryStr ? `/superadmin/usuarios?${queryStr}` : "/superadmin/usuarios";
  const respuesta = await apiClient.get(ruta);
  return {
    usuarios: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function impersonarOrgApi(orgId) {
  return apiClient.post(`/superadmin/impersonar/${orgId}`, {});
}
async function obtenerMetricasGlobalesApi() {
  const respuesta = await apiClient.get("/superadmin/metricas");
  return respuesta.datos;
}
async function obtenerAuditoriaGlobalApi(params) {
  const query = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([clave, valor]) => {
      if (valor) query.set(clave, valor);
    });
  }
  const queryStr = query.toString();
  const ruta = queryStr ? `/superadmin/auditoria?${queryStr}` : "/superadmin/auditoria";
  const respuesta = await apiClient.get(ruta);
  return {
    registros: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
export {
  actualizarOrganizacionApi as a,
  listarUsuariosGlobalApi as b,
  crearOrganizacionApi as c,
  obtenerAuditoriaGlobalApi as d,
  impersonarOrgApi as i,
  listarOrganizacionesApi as l,
  obtenerMetricasGlobalesApi as o
};
