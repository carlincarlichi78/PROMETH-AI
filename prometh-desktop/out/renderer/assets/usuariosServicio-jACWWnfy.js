import { d as apiClient } from "./index-DMbE3NR1.js";
async function listarUsuariosApi(params) {
  const query = new URLSearchParams();
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.activo !== void 0) query.set("activo", String(params.activo));
  if (params?.pagina) query.set("pagina", String(params.pagina));
  if (params?.limite) query.set("limite", String(params.limite));
  const queryStr = query.toString();
  const ruta = queryStr ? `/usuarios?${queryStr}` : "/usuarios";
  const respuesta = await apiClient.get(ruta);
  return {
    usuarios: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function crearUsuarioApi(datos) {
  const respuesta = await apiClient.post("/usuarios", datos);
  return respuesta.datos;
}
async function actualizarUsuarioApi(id, datos) {
  const respuesta = await apiClient.put(`/usuarios/${id}`, datos);
  return respuesta.datos;
}
async function desactivarUsuarioApi(id) {
  await apiClient.del(`/usuarios/${id}`);
}
export {
  actualizarUsuarioApi as a,
  crearUsuarioApi as c,
  desactivarUsuarioApi as d,
  listarUsuariosApi as l
};
