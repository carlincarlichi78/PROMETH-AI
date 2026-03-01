import { r as reactExports, j as jsxRuntimeExports, N as FileSearch } from "./index-DMbE3NR1.js";
import { d as obtenerAuditoriaGlobalApi } from "./superadminServicio-RgYMJlVk.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
function PaginaSuperadminAuditoria() {
  const [registros, setRegistros] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [fechaDesde, setFechaDesde] = reactExports.useState("");
  const [fechaHasta, setFechaHasta] = reactExports.useState("");
  const [accion, setAccion] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const cargar = reactExports.useCallback(async () => {
    try {
      setCargando(true);
      setError(null);
      const params = {
        pagina: String(pagina),
        limite: "20"
      };
      if (fechaDesde) params.fechaDesde = fechaDesde;
      if (fechaHasta) params.fechaHasta = fechaHasta;
      if (accion.trim()) params.accion = accion.trim();
      const resp = await obtenerAuditoriaGlobalApi(params);
      setRegistros(resp.registros);
      setTotalPaginas(resp.meta.totalPaginas || 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando auditoria");
    } finally {
      setCargando(false);
    }
  }, [pagina, fechaDesde, fechaHasta, accion]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-gray-100", children: "Auditoria global" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400 mt-1", children: "Registro de actividad de todas las organizaciones" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-gray-500 mb-1", children: "Desde" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "date",
            value: fechaDesde,
            onChange: (e) => {
              setFechaDesde(e.target.value);
              setPagina(1);
            },
            className: "px-3 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-gray-500 mb-1", children: "Hasta" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "date",
            value: fechaHasta,
            onChange: (e) => {
              setFechaHasta(e.target.value);
              setPagina(1);
            },
            className: "px-3 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-gray-500 mb-1", children: "Accion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            placeholder: "Filtrar por accion...",
            value: accion,
            onChange: (e) => {
              setAccion(e.target.value);
              setPagina(1);
            },
            className: "w-full px-3 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-acento-500"
          }
        )
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400", children: error }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center h-48", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-8 h-8 text-acento-400 animate-spin" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-gray-800 border border-gray-700 overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-gray-700", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Fecha" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Usuario" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Organizacion" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Accion" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Certificado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "IP" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-gray-700/50", children: registros.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { colSpan: 6, className: "px-4 py-12 text-center text-gray-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(FileSearch, { className: "w-10 h-10 mx-auto mb-2 opacity-50" }),
          "No se encontraron registros"
        ] }) }) : registros.map((r) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-gray-700/30 transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-400 whitespace-nowrap", children: new Date(r.fecha).toLocaleString("es-ES", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit"
          }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-100", children: r.nombreUsuario ?? r.usuarioId }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-300", children: r.nombreOrganizacion ?? r.organizacionId }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex px-2.5 py-0.5 rounded-md text-xs font-medium bg-gray-700 text-gray-300 border border-gray-600", children: r.accion }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-400 truncate max-w-[180px]", children: r.nombreCertificado ?? r.certificadoId ?? "-" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-500 font-mono", children: r.ip ?? "-" })
        ] }, r.id)) })
      ] }) }),
      totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-4 py-3 border-t border-gray-700", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-gray-400", children: [
          "Pagina ",
          pagina,
          " de ",
          totalPaginas
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.max(1, p - 1)),
              disabled: pagina <= 1,
              className: "p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
              disabled: pagina >= totalPaginas,
              className: "p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
            }
          )
        ] })
      ] })
    ] })
  ] });
}
export {
  PaginaSuperadminAuditoria
};
