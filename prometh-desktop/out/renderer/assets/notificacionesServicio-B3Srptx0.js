import { d as apiClient } from "./index-DMbE3NR1.js";
async function listarNotificacionesApi(params) {
  const query = new URLSearchParams();
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.estado) query.set("estado", params.estado);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  if (params?.limite) query.set("limite", String(params.limite));
  if (params?.orden) query.set("orden", params.orden);
  if (params?.urgencia) query.set("urgencia", params.urgencia);
  if (params?.categoria) query.set("categoria", params.categoria);
  if (params?.certificadoIds) query.set("certificadoIds", params.certificadoIds);
  const queryStr = query.toString();
  const ruta = queryStr ? `/notificaciones?${queryStr}` : "/notificaciones";
  const respuesta = await apiClient.get(ruta);
  return {
    notificaciones: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function actualizarNotificacionApi(id, datos) {
  const respuesta = await apiClient.patch(`/notificaciones/${id}`, datos);
  return respuesta.datos;
}
async function enviarNotificacionApi(id, datos) {
  const respuesta = await apiClient.post(`/notificaciones/${id}/enviar`, datos);
  return respuesta.datos;
}
async function descartarAutomaticasApi() {
  const respuesta = await apiClient.post("/notificaciones/descartar-automaticas", {});
  return respuesta.datos;
}
async function obtenerDashboardPlazosApi() {
  const respuesta = await apiClient.get(
    "/notificaciones/dashboard-plazos"
  );
  return respuesta.datos;
}
async function eliminarNotificacionesBatchApi(ids) {
  const respuesta = await apiClient.post("/notificaciones/eliminar-batch", { ids });
  return respuesta.datos;
}
async function obtenerHistorialApi(notificacionId) {
  const respuesta = await apiClient.get(
    `/notificaciones/${notificacionId}/historial`
  );
  return {
    registros: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 50, totalPaginas: 0 }
  };
}
export {
  obtenerDashboardPlazosApi as a,
  actualizarNotificacionApi as b,
  eliminarNotificacionesBatchApi as c,
  descartarAutomaticasApi as d,
  enviarNotificacionApi as e,
  listarNotificacionesApi as l,
  obtenerHistorialApi as o
};
