import { J as BASE_URL, r as reactExports, j as jsxRuntimeExports, N as FileSearch, o as Upload, s as ArrowRight, q as FileText } from "./index-DMbE3NR1.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
async function compararDocumentosApi(original, modificado) {
  const formData = new FormData();
  formData.append("original", original);
  formData.append("modificado", modificado);
  const token = localStorage.getItem("accessToken");
  const resp = await fetch(`${BASE_URL}/comparador`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData
  });
  const datos = await resp.json();
  if (!resp.ok) throw new Error(datos.error || "Error comparando documentos");
  return datos.datos;
}
function PaginaComparador() {
  const [archivoOriginal, setArchivoOriginal] = reactExports.useState(null);
  const [archivoModificado, setArchivoModificado] = reactExports.useState(null);
  const [resultado, setResultado] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  const [vistaUnificada, setVistaUnificada] = reactExports.useState(true);
  const refOriginal = reactExports.useRef(null);
  const refModificado = reactExports.useRef(null);
  const comparar = async () => {
    if (!archivoOriginal || !archivoModificado) return;
    try {
      setCargando(true);
      setError(null);
      const res = await compararDocumentosApi(archivoOriginal, archivoModificado);
      setResultado(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error comparando");
    } finally {
      setCargando(false);
    }
  };
  const limpiar = () => {
    setArchivoOriginal(null);
    setArchivoModificado(null);
    setResultado(null);
    setError(null);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-7xl mx-auto space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "text-2xl font-bold text-white flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(FileSearch, { className: "w-7 h-7 text-acento-400" }),
        "Comparador de documentos"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 mt-1", children: "Compara dos versiones de un documento PDF para ver las diferencias" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 md:grid-cols-2 gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          onClick: () => refOriginal.current?.click(),
          className: `rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${archivoOriginal ? "border-emerald-500/30 bg-emerald-500/5" : "border-white/[0.08] hover:border-white/[0.15] bg-superficie-900"}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                ref: refOriginal,
                type: "file",
                accept: ".pdf",
                className: "hidden",
                onChange: (e) => {
                  const f = e.target.files?.[0];
                  if (f) setArchivoOriginal(f);
                }
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: `w-8 h-8 mx-auto mb-3 ${archivoOriginal ? "text-emerald-400" : "text-superficie-600"}` }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white mb-1", children: archivoOriginal ? archivoOriginal.name : "Documento original" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: archivoOriginal ? `${(archivoOriginal.size / 1024).toFixed(1)} KB` : "Click para seleccionar PDF" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          onClick: () => refModificado.current?.click(),
          className: `rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${archivoModificado ? "border-acento-500/30 bg-acento-500/5" : "border-white/[0.08] hover:border-white/[0.15] bg-superficie-900"}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                ref: refModificado,
                type: "file",
                accept: ".pdf",
                className: "hidden",
                onChange: (e) => {
                  const f = e.target.files?.[0];
                  if (f) setArchivoModificado(f);
                }
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: `w-8 h-8 mx-auto mb-3 ${archivoModificado ? "text-acento-400" : "text-superficie-600"}` }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white mb-1", children: archivoModificado ? archivoModificado.name : "Documento modificado" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: archivoModificado ? `${(archivoModificado.size / 1024).toFixed(1)} KB` : "Click para seleccionar PDF" })
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: comparar,
          disabled: !archivoOriginal || !archivoModificado || cargando,
          className: "flex items-center gap-2 px-5 py-2.5 bg-acento-500 hover:bg-acento-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors",
          children: [
            cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowRight, { className: "w-4 h-4" }),
            cargando ? "Comparando..." : "Comparar"
          ]
        }
      ),
      resultado && /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: limpiar,
          className: "px-4 py-2.5 text-superficie-400 hover:text-white hover:bg-white/[0.05] rounded-lg text-sm transition-colors",
          children: "Limpiar"
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm", children: error }),
    resultado && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 md:grid-cols-5 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-superficie-900 border border-white/[0.06] p-4 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-2xl font-bold text-white", children: [
            resultado.diff.porcentajeCambio,
            "%"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: "Cambio total" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-emerald-500/5 border border-emerald-500/20 p-4 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-2xl font-bold text-emerald-400", children: [
            "+",
            resultado.diff.lineasAgregadas
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: "Agregadas" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-red-500/5 border border-red-500/20 p-4 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-2xl font-bold text-red-400", children: [
            "-",
            resultado.diff.lineasEliminadas
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: "Eliminadas" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-amber-500/5 border border-amber-500/20 p-4 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-2xl font-bold text-amber-400", children: [
            "~",
            resultado.diff.lineasModificadas
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: "Modificadas" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-superficie-900 border border-white/[0.06] p-4 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center gap-2 text-sm text-superficie-400", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
              resultado.metadatosOriginal.paginas,
              "p"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowRight, { className: "w-3 h-3" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
              resultado.metadatosModificado.paginas,
              "p"
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: "Paginas" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setVistaUnificada(true),
            className: `px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${vistaUnificada ? "bg-acento-500/10 text-acento-400 border border-acento-500/20" : "text-superficie-500 hover:text-white"}`,
            children: "Vista unificada"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setVistaUnificada(false),
            className: `px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${!vistaUnificada ? "bg-acento-500/10 text-acento-400 border border-acento-500/20" : "text-superficie-500 hover:text-white"}`,
            children: "Vista lado a lado"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-superficie-900 border border-white/[0.06] overflow-hidden", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-5 py-3 border-b border-white/[0.06] flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-superficie-400", children: [
            resultado.nombresArchivos.original,
            " vs ",
            resultado.nombresArchivos.modificado
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-600", children: [
            resultado.diff.lineas.length,
            " lineas"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-auto max-h-[600px] font-mono text-xs", children: vistaUnificada ? /* @__PURE__ */ jsxRuntimeExports.jsx("table", { className: "w-full", children: /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: resultado.diff.lineas.map((linea, idx) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "tr",
          {
            className: `relative ${linea.tipo === "agregada" ? "bg-emerald-500/5" : linea.tipo === "eliminada" ? "bg-red-500/5" : linea.tipo === "modificada" ? "bg-amber-500/5" : "hover:bg-white/[0.02]"}`,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-0.5 text-right text-superficie-700 select-none w-12 border-r border-white/[0.04]", children: linea.lineaOriginal ?? "" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-0.5 text-right text-superficie-700 select-none w-12 border-r border-white/[0.04]", children: linea.lineaModificada ?? "" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-2 py-0.5 w-6 text-center select-none", children: [
                linea.tipo === "agregada" && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-emerald-400", children: "+" }),
                linea.tipo === "eliminada" && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-red-400", children: "-" }),
                linea.tipo === "modificada" && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber-400", children: "~" })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-0.5", children: linea.tipo === "modificada" ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-red-400/70 line-through", children: linea.contenidoAnterior }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-emerald-400", children: linea.contenido })
              ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: linea.tipo === "agregada" ? "text-emerald-400" : linea.tipo === "eliminada" ? "text-red-400" : "text-superficie-300", children: linea.contenido || " " }) })
            ]
          },
          idx
        )) }) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 divide-x divide-white/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-3 py-2 bg-superficie-800/50 text-superficie-500 text-[10px] uppercase tracking-wider border-b border-white/[0.04]", children: [
              "Original — ",
              resultado.nombresArchivos.original
            ] }),
            resultado.diff.lineas.filter((l) => l.tipo !== "agregada").map((linea, idx) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "div",
              {
                className: `flex px-3 py-0.5 ${linea.tipo === "eliminada" ? "bg-red-500/5" : linea.tipo === "modificada" ? "bg-amber-500/5" : ""}`,
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-700 select-none w-10 text-right mr-3 shrink-0", children: linea.lineaOriginal ?? "" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: linea.tipo === "eliminada" ? "text-red-400" : linea.tipo === "modificada" ? "text-amber-400" : "text-superficie-300", children: linea.tipo === "modificada" ? linea.contenidoAnterior : linea.contenido || " " })
                ]
              },
              idx
            ))
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-3 py-2 bg-superficie-800/50 text-superficie-500 text-[10px] uppercase tracking-wider border-b border-white/[0.04]", children: [
              "Modificado — ",
              resultado.nombresArchivos.modificado
            ] }),
            resultado.diff.lineas.filter((l) => l.tipo !== "eliminada").map((linea, idx) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "div",
              {
                className: `flex px-3 py-0.5 ${linea.tipo === "agregada" ? "bg-emerald-500/5" : linea.tipo === "modificada" ? "bg-amber-500/5" : ""}`,
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-700 select-none w-10 text-right mr-3 shrink-0", children: linea.lineaModificada ?? "" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: linea.tipo === "agregada" ? "text-emerald-400" : linea.tipo === "modificada" ? "text-emerald-400" : "text-superficie-300", children: linea.contenido || " " })
                ]
              },
              idx
            ))
          ] })
        ] }) })
      ] })
    ] })
  ] });
}
export {
  PaginaComparador
};
