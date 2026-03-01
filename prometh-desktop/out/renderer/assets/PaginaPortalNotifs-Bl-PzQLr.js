import { r as reactExports, j as jsxRuntimeExports, B as Bell, m as Search, n as ChevronDown } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { a as listarNotificacionesPortalApi } from "./portalServicio-D-oBBzfH.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
const COLORES_URGENCIA = {
  critica: "bg-red-500/10 text-red-400 border-red-500/20",
  alta: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  media: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  baja: "bg-green-500/10 text-green-400 border-green-500/20"
};
const ETIQUETAS_URGENCIA = {
  critica: "Critica",
  alta: "Alta",
  media: "Media",
  baja: "Baja"
};
const COLORES_ESTADO = {
  pendiente: "bg-amber-500/10 text-amber-400",
  leida: "bg-blue-500/10 text-blue-400",
  gestionada: "bg-green-500/10 text-green-400",
  descartada: "bg-superficie-700/50 text-superficie-500"
};
const ETIQUETAS_ESTADO = {
  pendiente: "Pendiente",
  leida: "Leida",
  gestionada: "Gestionada",
  descartada: "Descartada"
};
const FILTROS_ESTADO = [
  { valor: "", etiqueta: "Todos los estados" },
  { valor: "pendiente", etiqueta: "Pendiente" },
  { valor: "leida", etiqueta: "Leida" },
  { valor: "gestionada", etiqueta: "Gestionada" },
  { valor: "descartada", etiqueta: "Descartada" }
];
function PaginaPortalNotifs() {
  const [notificaciones, setNotificaciones] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [filtroEstado, setFiltroEstado] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarNotificacionesPortalApi({
        estado: filtroEstado || void 0,
        busqueda: busqueda || void 0,
        pagina,
        limite: 20
      });
      setNotificaciones(resultado.items);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar notificaciones");
    } finally {
      setCargando(false);
    }
  }, [busqueda, filtroEstado, pagina]);
  reactExports.useEffect(() => {
    const timer = setTimeout(cargar, 300);
    return () => clearTimeout(timer);
  }, [cargar]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Notificaciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-superficie-500", children: [
          "(",
          total,
          ")"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-1 items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: busqueda,
              onChange: (e) => {
                setBusqueda(e.target.value);
                setPagina(1);
              },
              placeholder: "Buscar notificaciones...",
              className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: filtroEstado,
              onChange: (e) => {
                setFiltroEstado(e.target.value);
                setPagina(1);
              },
              className: "appearance-none pl-3 pr-8 py-2 text-sm text-superficie-200 border border-white/[0.06] rounded-lg\n                outline-none focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 cursor-pointer",
              children: FILTROS_ESTADO.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: f.valor, className: "bg-superficie-800", children: f.etiqueta }, f.valor))
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500 pointer-events-none" })
        ] })
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando notificaciones..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Administracion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tipo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Urgencia" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Contenido" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: notificaciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 6, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No se encontraron notificaciones" }) }) : notificaciones.map((notif) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 font-medium text-superficie-100", children: notif.administracion }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: notif.tipo ?? "---" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_ESTADO[notif.estado] ?? ""}`, children: ETIQUETAS_ESTADO[notif.estado] ?? notif.estado }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: notif.urgencia ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_URGENCIA[notif.urgencia] ?? ""}`, children: ETIQUETAS_URGENCIA[notif.urgencia] ?? notif.urgencia }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-600 text-xs", children: "---" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 whitespace-nowrap", children: formatearFecha(notif.fechaDeteccion) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 max-w-xs truncate", children: notif.contenido ?? "---" })
      ] }, notif.id)) })
    ] }) }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mt-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Pagina ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " notificaciones)"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setPagina((p) => Math.max(1, p - 1)),
            disabled: pagina <= 1,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
            disabled: pagina >= totalPaginas,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
          }
        )
      ] })
    ] })
  ] });
}
export {
  PaginaPortalNotifs
};
