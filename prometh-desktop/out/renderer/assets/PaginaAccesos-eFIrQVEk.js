import { d as apiClient, r as reactExports, j as jsxRuntimeExports, m as Search } from "./index-DMbE3NR1.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { E as ExternalLink } from "./external-link-Bh_6IHXn.js";
async function listarAccesosApi(params) {
  const query = new URLSearchParams();
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.categoria) query.set("categoria", params.categoria);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  if (params?.orden) query.set("orden", params.orden);
  const queryStr = query.toString();
  const ruta = queryStr ? `/accesos?${queryStr}` : "/accesos";
  const respuesta = await apiClient.get(ruta);
  return {
    accesos: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 50, totalPaginas: 0 }
  };
}
const COLORES_POR_CATEGORIA = {
  tributaria: { fondo: "bg-blue-500/10 border-blue-500/20", texto: "text-blue-400" },
  laboral: { fondo: "bg-acento-500/10 border-acento-500/20", texto: "text-acento-400" },
  electronica: { fondo: "bg-violet-500/10 border-violet-500/20", texto: "text-violet-400" },
  mercantil: { fondo: "bg-orange-500/10 border-orange-500/20", texto: "text-orange-400" },
  propiedad: { fondo: "bg-amber-500/10 border-amber-500/20", texto: "text-amber-400" },
  trafico: { fondo: "bg-red-500/10 border-red-500/20", texto: "text-red-400" },
  legislacion: { fondo: "bg-indigo-500/10 border-indigo-500/20", texto: "text-indigo-400" },
  certificados: { fondo: "bg-superficie-700/50 border-white/[0.06]", texto: "text-superficie-300" },
  justicia: { fondo: "bg-pink-500/10 border-pink-500/20", texto: "text-pink-400" }
};
const COLORES_DEFECTO = { fondo: "bg-cyan-500/10 border-cyan-500/20", texto: "text-cyan-400" };
function obtenerIniciales(nombre) {
  const palabras = nombre.trim().split(/\s+/);
  return palabras.length === 1 ? palabras[0].slice(0, 2).toUpperCase() : (palabras[0][0] + palabras[1][0]).toUpperCase();
}
function obtenerColores(categoria) {
  return COLORES_POR_CATEGORIA[categoria ?? ""] ?? COLORES_DEFECTO;
}
function PaginaAccesos() {
  const [accesos, setAccesos] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [busquedaDebounced, setBusquedaDebounced] = reactExports.useState("");
  reactExports.useEffect(() => {
    const temporizador = setTimeout(() => {
      setBusquedaDebounced(busqueda);
    }, 300);
    return () => clearTimeout(temporizador);
  }, [busqueda]);
  const cargarAccesos = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarAccesosApi({
        busqueda: busquedaDebounced || void 0,
        limite: 100
      });
      setAccesos(resultado.accesos);
    } catch {
      setError("No se pudieron cargar los accesos directos");
    } finally {
      setCargando(false);
    }
  }, [busquedaDebounced]);
  reactExports.useEffect(() => {
    cargarAccesos();
  }, [cargarAccesos]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Accesos directos" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative max-w-xs w-full", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: busqueda,
            onChange: (e) => setBusqueda(e.target.value),
            placeholder: "Buscar administración...",
            className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n              focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
          }
        )
      ] })
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm", children: "Cargando accesos..." })
    ] }),
    !cargando && error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-6 h-6 text-red-400" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm", children: error })
    ] }),
    !cargando && !error && accesos.length === 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col items-center justify-center py-16", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm", children: "No se encontraron administraciones" }) }),
    !cargando && !error && accesos.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3", children: accesos.map((acceso) => /* @__PURE__ */ jsxRuntimeExports.jsx(CardAcceso, { acceso }, acceso.id)) })
  ] });
}
function CardAcceso({ acceso }) {
  const iniciales = obtenerIniciales(acceso.nombre);
  const { fondo, texto } = obtenerColores(acceso.categoria);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "button",
    {
      type: "button",
      onClick: () => window.open(acceso.url, "_blank"),
      className: "group flex flex-col items-center gap-3 p-5 cristal-sutil rounded-xl\n        hover:bg-superficie-900/60 transition-all text-center cursor-pointer",
      "aria-label": `Acceder a ${acceso.nombre}`,
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: `w-12 h-12 rounded-xl ${fondo} border flex items-center justify-center
        group-hover:scale-105 transition-transform`,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm font-bold ${texto}`, children: iniciales })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0 w-full", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "font-semibold text-sm text-superficie-100 truncate", children: acceso.nombre }),
          acceso.categoria && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-superficie-500 mt-0.5 line-clamp-2 leading-tight", children: acceso.categoria })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(ExternalLink, { className: "w-3.5 h-3.5 text-superficie-600 group-hover:text-acento-400 transition-colors" })
      ]
    }
  );
}
export {
  PaginaAccesos
};
