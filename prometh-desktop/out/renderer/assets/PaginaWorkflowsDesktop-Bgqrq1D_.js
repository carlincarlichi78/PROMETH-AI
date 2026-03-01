import { r as reactExports, j as jsxRuntimeExports, m as Search, n as ChevronDown, W as Workflow, f as CircleCheckBig, I as CircleX } from "./index-DMbE3NR1.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { F as Filter } from "./filter-CPgLVKV9.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { P as Play } from "./play-B9P3AzSW.js";
import { C as Copy } from "./copy-BxtWXfxP.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
const ETIQUETAS_ACCION = {
  split_pdf: "Separar PDF",
  send_mail: "Enviar email",
  protect_pdf: "Proteger PDF",
  send_to_repository: "Organizar en carpeta"
};
function PaginaWorkflowsDesktop() {
  const [workflows, setWorkflows] = reactExports.useState([]);
  const [historial, setHistorial] = reactExports.useState([]);
  const [categorias, setCategorias] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [tabActiva, setTabActiva] = reactExports.useState("workflows");
  const [categoriaFiltro, setCategoriaFiltro] = reactExports.useState("");
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [expandidos, setExpandidos] = reactExports.useState(/* @__PURE__ */ new Set());
  const [ejecutandoId, setEjecutandoId] = reactExports.useState(null);
  const [progreso, setProgreso] = reactExports.useState(null);
  const api = window.electronAPI;
  const cargar = reactExports.useCallback(async () => {
    if (!api) return;
    try {
      setCargando(true);
      setError(null);
      const [wfs, hist, cats] = await Promise.all([
        api.workflows.listar(),
        api.workflows.historial(30),
        api.workflows.categorias()
      ]);
      setWorkflows(wfs);
      setHistorial(hist);
      setCategorias(cats);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando workflows");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  reactExports.useEffect(() => {
    if (!api) return;
    api.workflows.onProgreso((datos) => {
      const p = datos;
      setProgreso(p);
      if (p.estado === "completado" || p.estado === "error") {
        setTimeout(() => {
          setProgreso(null);
          setEjecutandoId(null);
          cargar();
        }, 1500);
      }
    });
  }, [api, cargar]);
  const ejecutarWorkflow = async (id) => {
    if (!api) return;
    try {
      setEjecutandoId(id);
      setError(null);
      await api.workflows.ejecutar(id, {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error ejecutando workflow");
      setEjecutandoId(null);
    }
  };
  const duplicarWorkflow = async (id) => {
    if (!api) return;
    try {
      await api.workflows.duplicar(id);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error duplicando workflow");
    }
  };
  const eliminarWorkflow = async (id) => {
    if (!api) return;
    try {
      await api.workflows.eliminar(id);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error eliminando workflow");
    }
  };
  const toggleExpandido = (id) => {
    const nuevos = new Set(expandidos);
    if (nuevos.has(id)) nuevos.delete(id);
    else nuevos.add(id);
    setExpandidos(nuevos);
  };
  const workflowsFiltrados = workflows.filter((wf) => {
    if (categoriaFiltro && wf.categoria !== categoriaFiltro) return false;
    if (busqueda && !wf.nombre.toLowerCase().includes(busqueda.toLowerCase())) return false;
    return true;
  });
  const agrupados = workflowsFiltrados.reduce((acc, wf) => {
    return { ...acc, [wf.categoria]: [...acc[wf.categoria] ?? [], wf] };
  }, {});
  if (!api) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Workflows Desktop" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Automatiza procesamiento de documentos: separar, proteger, enviar, organizar" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
        workflows.length,
        " workflows disponibles"
      ] })
    ] }),
    progreso && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 cristal rounded-xl p-4 border border-acento-500/30 bg-acento-500/5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-400 animate-spin" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-white", children: progreso.workflowNombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-400 ml-auto", children: [
          progreso.porcentaje,
          "%"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-full bg-superficie-800 rounded-full h-1.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-acento-500 h-1.5 rounded-full transition-all duration-300", style: { width: `${progreso.porcentaje}%` } }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-400 mt-2", children: [
        "Accion ",
        progreso.accionActual,
        "/",
        progreso.totalAcciones,
        ": ",
        ETIQUETAS_ACCION[progreso.accionNombre] ?? progreso.accionNombre
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5 mb-4", children: [
      { id: "workflows", etiqueta: "Workflows" },
      { id: "historial", etiqueta: `Historial (${historial.length})` }
    ].map(({ id, etiqueta }) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => setTabActiva(id),
        className: `px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${tabActiva === id ? "bg-acento-500/10 text-acento-400 border border-acento-500/20" : "text-superficie-400 hover:bg-white/[0.05] border border-transparent"}`,
        children: etiqueta
      },
      id
    )) }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-500 animate-spin" }) }),
    !cargando && tabActiva === "workflows" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3 mb-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              value: busqueda,
              onChange: (e) => setBusqueda(e.target.value),
              placeholder: "Buscar workflow...",
              className: "w-full pl-9 pr-3 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white placeholder:text-superficie-500 focus:outline-none focus:border-acento-500/40"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Filter, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: categoriaFiltro,
              onChange: (e) => setCategoriaFiltro(e.target.value),
              className: "pl-9 pr-8 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white appearance-none focus:outline-none focus:border-acento-500/40",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todas las categorias" }),
                categorias.map((cat) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: cat, children: cat }, cat))
              ]
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-6", children: Object.entries(agrupados).map(([cat, wfs]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-xs font-semibold text-superficie-500 uppercase tracking-wide mb-2", children: [
          cat,
          " (",
          wfs.length,
          ")"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1.5", children: wfs.map((wf) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl border border-white/[0.06] overflow-hidden", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 px-4 py-3 hover:bg-white/[0.02] transition-colors", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => toggleExpandido(wf.id), className: "text-superficie-500 hover:text-white", children: expandidos.has(wf.id) ? /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(Workflow, { className: "w-4 h-4 text-superficie-400 shrink-0" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1 min-w-0", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white truncate", children: wf.nombre }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-1", children: wf.acciones.map((a, i) => /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-1.5 py-0.5 text-[10px] bg-superficie-800 text-superficie-400 rounded", children: ETIQUETAS_ACCION[a.tipo] ?? a.tipo }, i)) }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1 ml-2 shrink-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => ejecutarWorkflow(wf.id),
                  disabled: ejecutandoId !== null,
                  className: "p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-50",
                  title: "Ejecutar",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Play, { className: "w-4 h-4" })
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => duplicarWorkflow(wf.id),
                  className: "p-1.5 rounded-lg text-superficie-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors",
                  title: "Duplicar como personalizado",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "w-4 h-4" })
                }
              ),
              !wf.predefinido && /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => eliminarWorkflow(wf.id),
                  className: "p-1.5 rounded-lg text-superficie-400 hover:text-red-400 hover:bg-red-500/10 transition-colors",
                  title: "Eliminar",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" })
                }
              )
            ] })
          ] }),
          expandidos.has(wf.id) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-4 pb-3 pt-0 border-t border-white/[0.04]", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 py-2", children: wf.descripcion }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4 text-xs text-superficie-500", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: wf.predefinido ? "Predefinido" : "Personalizado" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
                wf.acciones.length,
                " accion(es)"
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: wf.activo ? "Activo" : "Inactivo" })
            ] })
          ] })
        ] }, wf.id)) })
      ] }, cat)) })
    ] }),
    !cargando && tabActiva === "historial" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "No hay ejecuciones registradas" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: historial.map((ej) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-4 border border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
      ej.resultado === "exito" ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-5 h-5 text-emerald-400 shrink-0" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white", children: ej.workflowNombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
          new Date(ej.ejecutadoEn).toLocaleString("es-ES"),
          " — ",
          ej.detalles.tiempoTotalMs,
          "ms"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-medium px-2 py-0.5 rounded-full ${ej.resultado === "exito" ? "bg-emerald-500/20 text-emerald-400" : "bg-red-500/20 text-red-400"}`, children: ej.resultado === "exito" ? "Exito" : "Error" })
    ] }) }, ej.id)) }) })
  ] });
}
export {
  PaginaWorkflowsDesktop
};
