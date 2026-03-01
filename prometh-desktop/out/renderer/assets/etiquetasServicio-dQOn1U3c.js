import { d as apiClient } from "./index-DMbE3NR1.js";
async function listarEtiquetasApi(params) {
  const query = new URLSearchParams();
  query.set("limite", "50");
  const ruta = `/etiquetas?${query}`;
  const respuesta = await apiClient.get(ruta);
  return {
    etiquetas: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 50, totalPaginas: 0 }
  };
}
async function crearEtiquetaApi(datos) {
  const respuesta = await apiClient.post("/etiquetas", datos);
  return respuesta.datos;
}
async function actualizarEtiquetaApi(id, datos) {
  const respuesta = await apiClient.put(`/etiquetas/${id}`, datos);
  return respuesta.datos;
}
async function eliminarEtiquetaApi(id) {
  await apiClient.del(`/etiquetas/${id}`);
}
async function asignarEtiquetasApi(certificadoId, etiquetaIds) {
  const respuesta = await apiClient.post(
    `/certificados/${certificadoId}/etiquetas`,
    { etiquetaIds }
  );
  return respuesta.datos ?? [];
}
export {
  actualizarEtiquetaApi as a,
  asignarEtiquetasApi as b,
  crearEtiquetaApi as c,
  eliminarEtiquetaApi as e,
  listarEtiquetasApi as l
};
