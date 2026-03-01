import { d as apiClient } from "./index-DMbE3NR1.js";
async function analizarNotificacionApi(notificacionId) {
  const respuesta = await apiClient.post("/aegis/analizar", { notificacionId });
  return respuesta.datos;
}
async function listarHistorialAegisApi(params) {
  const query = new URLSearchParams();
  if (params?.notificacionId) query.set("notificacionId", params.notificacionId);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  if (params?.limite) query.set("limite", String(params.limite));
  const qs = query.toString();
  const respuesta = await apiClient.get(`/aegis/historial${qs ? `?${qs}` : ""}`);
  return {
    analisis: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function obtenerUsoAegisApi() {
  const respuesta = await apiClient.get("/aegis/uso");
  return respuesta.datos;
}
async function generarRespuestaApi(notificacionId, tipoRespuesta) {
  const respuesta = await apiClient.post("/aegis/generar-respuesta", {
    notificacionId,
    tipoRespuesta
  });
  return respuesta.datos;
}
async function obtenerTiposRespuestaApi() {
  const respuesta = await apiClient.get("/aegis/tipos-respuesta");
  return respuesta.datos ?? [];
}
async function sugerirTiposRespuestaApi(notificacionId) {
  const respuesta = await apiClient.get(`/aegis/sugerir-tipos?notificacionId=${notificacionId}`);
  return respuesta.datos ?? [];
}
export {
  analizarNotificacionApi as a,
  obtenerUsoAegisApi as b,
  generarRespuestaApi as g,
  listarHistorialAegisApi as l,
  obtenerTiposRespuestaApi as o,
  sugerirTiposRespuestaApi as s
};
