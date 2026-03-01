import { d as apiClient } from "./index-DMbE3NR1.js";
async function listarGestionesApi(params) {
  const query = new URLSearchParams();
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.estado) query.set("estado", params.estado);
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite ?? 20));
  const ruta = `/gestiones?${query}`;
  const respuesta = await apiClient.get(ruta);
  return {
    gestiones: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function obtenerGestionApi(id) {
  const respuesta = await apiClient.get(`/gestiones/${id}`);
  return respuesta.datos;
}
async function crearGestionApi(datos) {
  const respuesta = await apiClient.post("/gestiones", datos);
  return respuesta.datos;
}
async function actualizarGestionApi(id, datos) {
  const respuesta = await apiClient.put(`/gestiones/${id}`, datos);
  return respuesta.datos;
}
async function eliminarGestionApi(id) {
  await apiClient.del(`/gestiones/${id}`);
}
async function asignarNotificacionesGestionApi(gestionId, notificacionIds) {
  const respuesta = await apiClient.post(
    `/gestiones/${gestionId}/notificaciones`,
    { notificacionIds }
  );
  return respuesta.datos ?? [];
}
export {
  actualizarGestionApi as a,
  asignarNotificacionesGestionApi as b,
  crearGestionApi as c,
  eliminarGestionApi as e,
  listarGestionesApi as l,
  obtenerGestionApi as o
};
