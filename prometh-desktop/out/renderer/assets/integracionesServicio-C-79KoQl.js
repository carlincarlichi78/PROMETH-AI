import { d as apiClient } from "./index-DMbE3NR1.js";
async function obtenerEstadoIntegracionesApi() {
  const respuesta = await apiClient.get("/integraciones/estado");
  return respuesta.datos;
}
async function autorizarGoogleApi() {
  const respuesta = await apiClient.get("/integraciones/google/autorizar");
  return respuesta.datos;
}
async function autorizarMicrosoftApi() {
  const respuesta = await apiClient.get("/integraciones/microsoft/autorizar");
  return respuesta.datos;
}
async function sincronizarCalendarioApi(certificadoId) {
  const respuesta = await apiClient.post("/integraciones/sincronizar", {
    certificadoId
  });
  return respuesta.datos;
}
async function desconectarIntegracionApi(proveedor) {
  await apiClient.del(`/integraciones/desconectar/${proveedor}`);
}
async function agregarEventoCalendarioApi(tipo, itemId, proveedor) {
  await apiClient.post("/integraciones/agregar-evento", { tipo, itemId, proveedor });
}
async function syncPlazosApi(notificacionId) {
  const respuesta = await apiClient.post("/integraciones/sync-plazos", { notificacionId });
  return respuesta.datos;
}
async function syncPlazosBatchApi(limite) {
  const respuesta = await apiClient.post("/integraciones/sync-plazos-batch", { limite });
  return respuesta.datos;
}
async function obtenerEstadoSyncPlazosApi() {
  const respuesta = await apiClient.get("/integraciones/sync-plazos/estado");
  return respuesta.datos;
}
async function listarEventosCalendarioApi(params) {
  const query = new URLSearchParams();
  if (params?.desde) query.set("desde", params.desde);
  if (params?.hasta) query.set("hasta", params.hasta);
  const qs = query.toString();
  const respuesta = await apiClient.get(
    `/integraciones/eventos-calendario${qs ? `?${qs}` : ""}`
  );
  return respuesta.datos;
}
export {
  agregarEventoCalendarioApi,
  autorizarGoogleApi,
  autorizarMicrosoftApi,
  desconectarIntegracionApi,
  listarEventosCalendarioApi,
  obtenerEstadoIntegracionesApi,
  obtenerEstadoSyncPlazosApi,
  sincronizarCalendarioApi,
  syncPlazosApi,
  syncPlazosBatchApi
};
