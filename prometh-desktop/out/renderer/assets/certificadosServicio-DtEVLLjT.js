import { d as apiClient, J as BASE_URL, g as ErrorApiCliente } from "./index-DMbE3NR1.js";
async function listarCertificadosApi(params) {
  const query = new URLSearchParams();
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.etiquetaId) query.set("etiquetaId", params.etiquetaId);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  if (params?.limite) query.set("limite", String(params.limite));
  if (params?.ordenarPor) query.set("ordenarPor", params.ordenarPor);
  if (params?.orden) query.set("orden", params.orden);
  const queryStr = query.toString();
  const ruta = queryStr ? `/certificados?${queryStr}` : "/certificados";
  const respuesta = await apiClient.get(ruta);
  return {
    certificados: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function listarResumenCertificadosApi() {
  const respuesta = await apiClient.get("/certificados/resumen");
  return respuesta.datos ?? [];
}
async function crearCertificadoApi(datos) {
  const respuesta = await apiClient.post("/certificados", datos);
  return respuesta.datos;
}
async function actualizarCertificadoApi(id, datos) {
  const respuesta = await apiClient.put(`/certificados/${id}`, datos);
  return respuesta.datos;
}
async function eliminarCertificadoApi(id) {
  await apiClient.del(`/certificados/${id}`);
}
async function importarCertificadoP12Api(archivo, password) {
  const token = localStorage.getItem("accessToken");
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("password", password);
  const respuesta = await fetch(`${BASE_URL}/certificados/importar`, {
    method: "POST",
    headers: {
      // El browser setea Content-Type con el boundary automáticamente al usar FormData
      ...token ? { Authorization: `Bearer ${token}` } : {}
    },
    body: formData
  });
  const datos = await respuesta.json();
  if (!respuesta.ok) {
    throw new ErrorApiCliente(respuesta.status, datos.error ?? "Error al importar certificado");
  }
  return datos.datos;
}
export {
  actualizarCertificadoApi as a,
  listarResumenCertificadosApi as b,
  crearCertificadoApi as c,
  eliminarCertificadoApi as e,
  importarCertificadoP12Api as i,
  listarCertificadosApi as l
};
