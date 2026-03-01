function diasHastaFecha(fecha) {
  const objetivo = new Date(fecha);
  const hoy = /* @__PURE__ */ new Date();
  const diferencia = objetivo.getTime() - hoy.getTime();
  return Math.ceil(diferencia / (1e3 * 60 * 60 * 24));
}
function estaPorCaducar(fechaVencimiento, diasAntelacion = 30) {
  return diasHastaFecha(fechaVencimiento) <= diasAntelacion;
}
function estaCaducado(fechaVencimiento) {
  return diasHastaFecha(fechaVencimiento) < 0;
}
function formatearFecha(fecha) {
  return new Date(fecha).toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  });
}
export {
  estaPorCaducar as a,
  estaCaducado as e,
  formatearFecha as f
};
