import { d as apiClient, r as reactExports, g as ErrorApiCliente, j as jsxRuntimeExports, A as Activity, N as FileSearch, m as Search } from "./index-DMbE3NR1.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { F as Filter } from "./filter-CPgLVKV9.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
async function listarAuditoriaApi(params) {
  const query = new URLSearchParams();
  if (params?.fechaDesde) query.set("fechaDesde", params.fechaDesde);
  if (params?.fechaHasta) query.set("fechaHasta", params.fechaHasta);
  if (params?.usuarioId) query.set("usuarioId", params.usuarioId);
  if (params?.certificadoId) query.set("certificadoId", params.certificadoId);
  if (params?.accion) query.set("accion", params.accion);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  const queryStr = query.toString();
  const ruta = queryStr ? `/auditoria?${queryStr}` : "/auditoria";
  const respuesta = await apiClient.get(ruta);
  return {
    registros: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function obtenerEstadisticasApi() {
  const respuesta = await apiClient.get("/auditoria/estadisticas");
  return respuesta.datos;
}
const COLORES_ACCION = {
  consultar: { fondo: "bg-blue-500/10 border-blue-500/20", texto: "text-blue-400" },
  activar: { fondo: "bg-green-500/10 border-green-500/20", texto: "text-green-400" },
  desactivar: { fondo: "bg-red-500/10 border-red-500/20", texto: "text-red-400" },
  firmar: { fondo: "bg-violet-500/10 border-violet-500/20", texto: "text-violet-400" }
};
const COLOR_ACCION_DEFECTO = { fondo: "bg-superficie-700/50 border-white/[0.06]", texto: "text-superficie-300" };
function badgeAccion(accion) {
  const { fondo, texto } = COLORES_ACCION[accion] ?? COLOR_ACCION_DEFECTO;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${fondo} ${texto} border capitalize`, children: accion });
}
function truncarUrl(url, max = 40) {
  return url.length > max ? url.slice(0, max) + "..." : url;
}
function PaginaAuditoria() {
  const [registros, setRegistros] = reactExports.useState([]);
  const [total, setTotal] = reactExports.useState(0);
  const [estadisticas, setEstadisticas] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [pagina, setPagina] = reactExports.useState(1);
  const [busquedaAccion, setBusquedaAccion] = reactExports.useState("");
  const [fechaDesde, setFechaDesde] = reactExports.useState("");
  const [fechaHasta, setFechaHasta] = reactExports.useState("");
  const [busquedaDebounced, setBusquedaDebounced] = reactExports.useState("");
  const LIMITE = 20;
  reactExports.useEffect(() => {
    const temporizador = setTimeout(() => {
      setBusquedaDebounced(busquedaAccion);
      setPagina(1);
    }, 300);
    return () => clearTimeout(temporizador);
  }, [busquedaAccion]);
  const cargarDatos = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [listado, stats] = await Promise.all([
        listarAuditoriaApi({
          accion: busquedaDebounced || void 0,
          fechaDesde: fechaDesde || void 0,
          fechaHasta: fechaHasta || void 0,
          pagina,
          limite: LIMITE
        }),
        obtenerEstadisticasApi()
      ]);
      setRegistros(listado.registros);
      setTotal(listado.meta.total);
      setEstadisticas(stats);
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al cargar datos de auditoría");
      }
    } finally {
      setCargando(false);
    }
  }, [busquedaDebounced, fechaDesde, fechaHasta, pagina]);
  reactExports.useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);
  const limpiarFiltros = () => {
    setBusquedaAccion("");
    setFechaDesde("");
    setFechaHasta("");
    setPagina(1);
  };
  const tieneFiltros = busquedaAccion || fechaDesde || fechaHasta;
  const totalPaginas = Math.ceil(total / LIMITE);
  const accionFrecuente = estadisticas?.accionesPorTipo.reduce(
    (max, item) => item.total > max.total ? item : max,
    { accion: "—", total: 0 }
  );
  const ultimoAcceso = registros.length > 0 ? new Date(registros[0].fecha).toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }) : "—";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Auditoría de accesos" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-500 mt-1", children: "Registro de actividad sobre certificados" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 flex items-center gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-acento-500/10 border border-acento-500/20 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Activity, { className: "w-5 h-5 text-acento-400" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 font-medium uppercase tracking-wide", children: "Total accesos (mes)" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg font-semibold text-white", children: estadisticas?.totalMes ?? "—" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 flex items-center gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(FileSearch, { className: "w-5 h-5 text-blue-400" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 font-medium uppercase tracking-wide", children: "Acción más frecuente" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg font-semibold text-white capitalize", children: accionFrecuente?.accion ?? "—" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 flex items-center gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-5 h-5 text-amber-400" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 font-medium uppercase tracking-wide", children: "Último acceso" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-semibold text-white", children: ultimoAcceso })
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-xs w-full", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: busquedaAccion,
            onChange: (e) => setBusquedaAccion(e.target.value),
            placeholder: "Buscar por acción...",
            className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n              focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-500", children: "Desde" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "date",
            value: fechaDesde,
            onChange: (e) => {
              setFechaDesde(e.target.value);
              setPagina(1);
            },
            className: "px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n              focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-500", children: "Hasta" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "date",
            value: fechaHasta,
            onChange: (e) => {
              setFechaHasta(e.target.value);
              setPagina(1);
            },
            className: "px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n              focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60"
          }
        )
      ] }),
      tieneFiltros && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: limpiarFiltros,
          className: "flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-superficie-400\n              border border-white/[0.06] rounded-lg hover:bg-white/[0.05] transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Filter, { className: "w-3.5 h-3.5" }),
            "Limpiar filtros"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400 flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: cargarDatos, className: "ml-auto text-xs underline hover:text-red-300", children: "Reintentar" })
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando registros..." })
    ] }),
    !cargando && !error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Usuario" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Certificado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Acción" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "URL" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "IP" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: registros.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 6, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No hay registros de auditoría" }) }) : registros.map((reg) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 whitespace-nowrap", children: new Date(reg.fecha).toLocaleString("es-ES", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
          }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-200 font-medium", children: reg.nombreUsuario ?? "Desconocido" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300", children: reg.nombreCertificado ?? "N/A" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: badgeAccion(reg.accion) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-500 font-mono text-xs", title: reg.urlAcceso, children: truncarUrl(reg.urlAcceso) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-500 font-mono text-xs", children: reg.ip ?? "—" })
        ] }, reg.id)) })
      ] }) }),
      total > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-3 border-t border-white/[0.06] bg-superficie-800/20", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
          "Mostrando ",
          Math.min((pagina - 1) * LIMITE + 1, total),
          "-",
          Math.min(pagina * LIMITE, total),
          " de ",
          total,
          " registros"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.max(1, p - 1)),
              disabled: pagina <= 1,
              className: "px-3 py-1.5 text-xs font-medium text-superficie-300 border border-white/[0.06] rounded-lg\n                    hover:bg-white/[0.05] disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
              children: "Anterior"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-400", children: [
            pagina,
            " / ",
            totalPaginas
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
              disabled: pagina >= totalPaginas,
              className: "px-3 py-1.5 text-xs font-medium text-superficie-300 border border-white/[0.06] rounded-lg\n                    hover:bg-white/[0.05] disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
              children: "Siguiente"
            }
          )
        ] })
      ] })
    ] })
  ] });
}
export {
  PaginaAuditoria
};
