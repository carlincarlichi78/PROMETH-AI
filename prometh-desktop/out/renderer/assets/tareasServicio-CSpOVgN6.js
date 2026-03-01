import { d as apiClient } from "./index-DMbE3NR1.js";
async function listarTareasApi(params) {
  const query = new URLSearchParams();
  if (params?.estado) query.set("estado", params.estado);
  if (params?.prioridad) query.set("prioridad", params.prioridad);
  if (params?.asignadoA) query.set("asignadoA", params.asignadoA);
  if (params?.referenciaTipo) query.set("referenciaTipo", params.referenciaTipo);
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite ?? 20));
  const ruta = `/tareas?${query}`;
  const respuesta = await apiClient.get(ruta);
  return {
    tareas: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function obtenerTareaApi(id) {
  const respuesta = await apiClient.get(`/tareas/${id}`);
  return respuesta.datos;
}
async function crearTareaApi(datos) {
  const respuesta = await apiClient.post("/tareas", datos);
  return respuesta.datos;
}
async function actualizarTareaApi(id, datos) {
  const respuesta = await apiClient.put(`/tareas/${id}`, datos);
  return respuesta.datos;
}
async function eliminarTareaApi(id) {
  await apiClient.del(`/tareas/${id}`);
}
async function agregarComentarioApi(tareaId, datos) {
  const respuesta = await apiClient.post(
    `/tareas/${tareaId}/comentarios`,
    datos
  );
  return respuesta.datos;
}
export {
  agregarComentarioApi as a,
  actualizarTareaApi as b,
  crearTareaApi as c,
  eliminarTareaApi as e,
  listarTareasApi as l,
  obtenerTareaApi as o
};
