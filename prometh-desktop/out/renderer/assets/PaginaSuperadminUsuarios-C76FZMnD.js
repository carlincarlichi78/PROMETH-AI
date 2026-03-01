import { r as reactExports, j as jsxRuntimeExports, m as Search, U as Users } from "./index-DMbE3NR1.js";
import { b as listarUsuariosGlobalApi } from "./superadminServicio-RgYMJlVk.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
function PaginaSuperadminUsuarios() {
  const [usuarios, setUsuarios] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
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
      if (busqueda.trim()) params.busqueda = busqueda.trim();
      const resp = await listarUsuariosGlobalApi(params);
      setUsuarios(resp.usuarios);
      setTotalPaginas(resp.meta.totalPaginas || 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando usuarios");
    } finally {
      setCargando(false);
    }
  }, [pagina, busqueda]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  const badgeRol = (rol) => {
    const colores = {
      superadmin: "bg-red-500/10 text-red-400 border-red-500/20",
      admin: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      asesor: "bg-blue-500/10 text-blue-400 border-blue-500/20"
    };
    return colores[rol] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20";
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-gray-100", children: "Usuarios global" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400 mt-1", children: "Todos los usuarios de todas las organizaciones" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col sm:flex-row gap-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "text",
          placeholder: "Buscar por nombre o email...",
          value: busqueda,
          onChange: (e) => {
            setBusqueda(e.target.value);
            setPagina(1);
          },
          className: "w-full pl-10 pr-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-acento-500"
        }
      )
    ] }) }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400", children: error }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center h-48", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-8 h-8 text-acento-400 animate-spin" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-gray-800 border border-gray-700 overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-gray-700", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Nombre" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Email" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Rol" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Organizacion" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Activo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Fecha" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-gray-700/50", children: usuarios.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { colSpan: 6, className: "px-4 py-12 text-center text-gray-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Users, { className: "w-10 h-10 mx-auto mb-2 opacity-50" }),
          "No se encontraron usuarios"
        ] }) }) : usuarios.map((u) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-gray-700/30 transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-100 font-medium", children: u.nombre }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-400", children: u.email }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex px-2.5 py-0.5 rounded-md text-xs font-medium border capitalize ${badgeRol(u.rol)}`, children: u.rol }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-300", children: u.nombreOrganizacion ?? u.organizacionId }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex w-2.5 h-2.5 rounded-full ${u.activo ? "bg-emerald-400" : "bg-red-400"}` }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-400", children: new Date(u.creadoEn).toLocaleDateString("es-ES") })
        ] }, u.id)) })
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
  PaginaSuperadminUsuarios
};
