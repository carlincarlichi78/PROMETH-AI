import { r as reactExports, j as jsxRuntimeExports, F as FolderOpen } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { c as listarGestionesPortalApi } from "./portalServicio-D-oBBzfH.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
const COLORES_TIPO = {
  fiscal: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  laboral: "bg-green-500/10 text-green-400 border-green-500/20",
  mercantil: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  administrativo: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  otro: "bg-superficie-700/50 text-superficie-400 border-white/[0.06]"
};
const ETIQUETAS_TIPO = {
  fiscal: "Fiscal",
  laboral: "Laboral",
  mercantil: "Mercantil",
  administrativo: "Administrativo",
  otro: "Otro"
};
const COLORES_ESTADO = {
  activa: "bg-green-500/10 text-green-400",
  completada: "bg-blue-500/10 text-blue-400",
  archivada: "bg-superficie-700/50 text-superficie-500"
};
const ETIQUETAS_ESTADO = {
  activa: "Activa",
  completada: "Completada",
  archivada: "Archivada"
};
function PaginaPortalGestiones() {
  const [gestiones, setGestiones] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarGestionesPortalApi({
        pagina,
        limite: 20
      });
      setGestiones(resultado.items);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar gestiones");
    } finally {
      setCargando(false);
    }
  }, [pagina]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(FolderOpen, { className: "w-5 h-5 text-acento-400" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Gestiones" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-superficie-500", children: [
        "(",
        total,
        ")"
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando gestiones..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Nombre" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tipo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Descripcion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: gestiones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 5, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No se encontraron gestiones" }) }) : gestiones.map((gestion) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 font-medium text-superficie-100", children: gestion.nombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_TIPO[gestion.tipo] ?? COLORES_TIPO.otro}`, children: ETIQUETAS_TIPO[gestion.tipo] ?? gestion.tipo }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_ESTADO[gestion.estado] ?? ""}`, children: ETIQUETAS_ESTADO[gestion.estado] ?? gestion.estado }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 max-w-xs truncate", children: gestion.descripcion ?? "---" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 whitespace-nowrap", children: formatearFecha(gestion.creadoEn) })
      ] }, gestion.id)) })
    ] }) }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mt-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Pagina ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " gestiones)"
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
  PaginaPortalGestiones
};
