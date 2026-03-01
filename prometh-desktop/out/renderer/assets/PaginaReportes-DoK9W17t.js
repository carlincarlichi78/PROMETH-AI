import { J as BASE_URL, r as reactExports, z as useAuthStore, j as jsxRuntimeExports, ab as FileSpreadsheet, q as FileText, D as Download } from "./index-DMbE3NR1.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
const EXTENSIONES = {
  csv: "csv",
  pdf: "pdf",
  excel: "xlsx"
};
async function descargarReporteApi(opciones) {
  const token = localStorage.getItem("accessToken");
  const query = new URLSearchParams();
  query.set("formato", opciones.formato);
  if (opciones.fechaDesde) query.set("fechaDesde", opciones.fechaDesde);
  if (opciones.fechaHasta) query.set("fechaHasta", opciones.fechaHasta);
  const respuesta = await fetch(`${BASE_URL}/reportes/${opciones.tipo}?${query.toString()}`, {
    headers: {
      ...token ? { Authorization: `Bearer ${token}` } : {}
    }
  });
  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => ({}));
    throw new Error(datos.error ?? `Error al generar reporte (${respuesta.status})`);
  }
  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = `${opciones.tipo}.${EXTENSIONES[opciones.formato]}`;
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
}
const TIPOS_REPORTE = [
  { id: "certificados", nombre: "Certificados", descripcion: "Listado completo de certificados digitales" },
  { id: "notificaciones", nombre: "Notificaciones", descripcion: "Historial de notificaciones de administraciones" },
  { id: "auditoria", nombre: "Auditoría", descripcion: "Registro de accesos y acciones de usuarios" }
];
const FORMATOS = [
  { id: "csv", nombre: "CSV", icono: FileSpreadsheet, planMinimo: "basico" },
  { id: "pdf", nombre: "PDF", icono: FileText, planMinimo: "profesional" },
  { id: "excel", nombre: "Excel", icono: FileSpreadsheet, planMinimo: "plus" }
];
const ORDEN_PLANES = ["basico", "profesional", "plus"];
function planPermitido(planActual, planMinimo) {
  return ORDEN_PLANES.indexOf(planActual) >= ORDEN_PLANES.indexOf(planMinimo);
}
function PaginaReportes() {
  const [tipoSeleccionado, setTipoSeleccionado] = reactExports.useState("certificados");
  const [fechaDesde, setFechaDesde] = reactExports.useState("");
  const [fechaHasta, setFechaHasta] = reactExports.useState("");
  const [descargando, setDescargando] = reactExports.useState(null);
  const [error, setError] = reactExports.useState("");
  const { usuario } = useAuthStore();
  const planActual = usuario?.organizacion?.plan ?? "basico";
  const manejarDescarga = async (formato) => {
    setError("");
    setDescargando(formato);
    try {
      await descargarReporteApi({
        tipo: tipoSeleccionado,
        formato,
        fechaDesde: fechaDesde || void 0,
        fechaHasta: fechaHasta || void 0
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al generar reporte");
    } finally {
      setDescargando(null);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Reportes" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 mt-1", children: "Exporta datos de tu organización en diferentes formatos" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid gap-4 md:grid-cols-3", children: TIPOS_REPORTE.map((tipo) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => setTipoSeleccionado(tipo.id),
        className: `p-4 rounded-xl border text-left transition-all ${tipoSeleccionado === tipo.id ? "border-acento-500/40 bg-acento-500/10" : "border-white/[0.06] bg-superficie-900 hover:border-white/[0.12]"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: `font-semibold ${tipoSeleccionado === tipo.id ? "text-acento-400" : "text-white"}`, children: tipo.nombre }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: tipo.descripcion })
        ]
      },
      tipo.id
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl p-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-300 mb-3", children: "Filtrar por fecha (opcional)" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Desde" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "date",
              value: fechaDesde,
              onChange: (e) => setFechaDesde(e.target.value),
              className: "px-3 py-2 rounded-lg bg-superficie-800 border border-white/[0.06] text-white text-sm focus:outline-none focus:border-acento-500/40"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Hasta" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "date",
              value: fechaHasta,
              onChange: (e) => setFechaHasta(e.target.value),
              className: "px-3 py-2 rounded-lg bg-superficie-800 border border-white/[0.06] text-white text-sm focus:outline-none focus:border-acento-500/40"
            }
          )
        ] }),
        (fechaDesde || fechaHasta) && /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => {
              setFechaDesde("");
              setFechaHasta("");
            },
            className: "self-end px-3 py-2 text-sm text-superficie-400 hover:text-white transition-colors",
            children: "Limpiar filtros"
          }
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl p-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-300 mb-4", children: "Descargar reporte" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-3", children: FORMATOS.map((formato) => {
        const disponible = planPermitido(planActual, formato.planMinimo);
        const Icono = formato.icono;
        const cargando = descargando === formato.id;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => manejarDescarga(formato.id),
            disabled: !disponible || cargando,
            className: `flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${disponible ? "bg-acento-500/10 text-acento-400 border border-acento-500/20 hover:bg-acento-500/20" : "bg-superficie-800 text-superficie-500 border border-white/[0.04] cursor-not-allowed"}`,
            title: !disponible ? `Requiere plan ${formato.planMinimo}` : void 0,
            children: [
              cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4 h-4" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-3.5 h-3.5" }),
              formato.nombre,
              !disponible && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs bg-superficie-700 px-1.5 py-0.5 rounded ml-1", children: formato.planMinimo })
            ]
          },
          formato.id
        );
      }) }),
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-3 text-sm text-red-400", children: error })
    ] })
  ] });
}
export {
  PaginaReportes
};
