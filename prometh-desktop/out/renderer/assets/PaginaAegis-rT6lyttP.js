import { c as createLucideIcon, r as reactExports, j as jsxRuntimeExports, p as Brain, X, w as ClipboardList } from "./index-DMbE3NR1.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { b as obtenerUsoAegisApi, l as listarHistorialAegisApi } from "./aegisServicio-6JqSkwLW.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { C as Calendar } from "./calendar-KREuhz-X.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CircleArrowUp = createLucideIcon("CircleArrowUp", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["path", { d: "m16 12-4-4-4 4", key: "177agl" }],
  ["path", { d: "M12 16V8", key: "1sbj14" }]
]);
const COLORES_PRIORIDAD = {
  alta: "bg-red-500/10 text-red-400 border-red-500/20",
  media: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  baja: "bg-acento-500/10 text-acento-400 border-acento-500/20"
};
const ETIQUETAS_PRIORIDAD = {
  alta: "Alta",
  media: "Media",
  baja: "Baja"
};
function PaginaAegis() {
  const [uso, setUso] = reactExports.useState(null);
  const [historial, setHistorial] = reactExports.useState([]);
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [analisisSeleccionado, setAnalisisSeleccionado] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const cargarDatos = reactExports.useCallback(async (pag) => {
    try {
      setError(null);
      const [usoData, historialData] = await Promise.all([
        obtenerUsoAegisApi(),
        listarHistorialAegisApi({ pagina: pag, limite: 20 }).catch(() => ({
          analisis: [],
          meta: { total: 0, pagina: 1, limite: 20, totalPaginas: 1 }
        }))
      ]);
      setUso(usoData);
      setHistorial(historialData.analisis);
      setTotalPaginas(historialData.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar datos");
    }
  }, []);
  reactExports.useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      await cargarDatos(pagina);
      setCargando(false);
    };
    cargar();
  }, [cargarDatos, pagina]);
  const noDisponible = uso && uso.limite === 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-5 h-5 text-purple-400" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "AEGIS IA" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 mt-2", children: "Análisis inteligente de notificaciones con IA" })
    ] }),
    uso && /* @__PURE__ */ jsxRuntimeExports.jsx(BarraUso, { uso }),
    noDisponible && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl p-6 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleArrowUp, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-white font-semibold mb-1", children: "Funcionalidad no disponible" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Actualiza al plan Profesional o Plus para acceder al análisis con IA" })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error
    ] }),
    !noDisponible && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "px-5 py-4 border-b border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-300", children: "Historial de análisis" }) }),
      cargando ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin mb-3" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Cargando historial..." })
      ] }) : historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-7 h-7 text-superficie-500" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "No hay análisis realizados" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Analiza notificaciones desde la sección de Notificaciones" })
      ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Prioridad" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Resumen" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Acciones" })
          ] }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: historial.map((analisis) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "tr",
            {
              className: "hover:bg-white/[0.02] transition-colors cursor-pointer",
              onClick: () => setAnalisisSeleccionado(analisis),
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "span",
                  {
                    className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_PRIORIDAD[analisis.prioridad]}`,
                    children: ETIQUETAS_PRIORIDAD[analisis.prioridad]
                  }
                ) }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 max-w-md", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "line-clamp-2", children: analisis.resumen }) }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap text-xs", children: new Date(analisis.creadoEn).toLocaleDateString("es-ES", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit"
                }) }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("button", { className: "text-acento-400 hover:text-acento-300 transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" }) }) })
              ]
            },
            analisis.id
          )) })
        ] }) }),
        totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center gap-2 py-4 border-t border-white/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.max(1, p - 1)),
              disabled: pagina === 1,
              className: "px-3 py-1.5 text-xs text-superficie-400 hover:text-white disabled:opacity-40 transition-colors",
              children: "Anterior"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
            "Pagina ",
            pagina,
            " de ",
            totalPaginas
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
              disabled: pagina === totalPaginas,
              className: "px-3 py-1.5 text-xs text-superficie-400 hover:text-white disabled:opacity-40 transition-colors",
              children: "Siguiente"
            }
          )
        ] })
      ] })
    ] }),
    analisisSeleccionado && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalAnalisis,
      {
        analisis: analisisSeleccionado,
        onCerrar: () => setAnalisisSeleccionado(null)
      }
    )
  ] });
}
function BarraUso({ uso }) {
  const porcentaje = uso.limite > 0 ? Math.min(100, uso.usados / uso.limite * 100) : 0;
  const casiAlLimite = porcentaje >= 80;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl p-5", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-300", children: "Uso mensual" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-sm font-medium ${casiAlLimite ? "text-amber-400" : "text-superficie-400"}`, children: [
        uso.usados,
        " / ",
        uso.limite
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-2 bg-superficie-800 rounded-full overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: `h-full rounded-full transition-all duration-500 ${casiAlLimite ? "bg-amber-500" : "bg-acento-500"}`,
        style: { width: `${porcentaje}%` }
      }
    ) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-2", children: uso.restantes > 0 ? `${uso.restantes} analisis restantes este mes` : uso.limite === 0 ? "Analisis IA no disponible en tu plan" : "Has alcanzado el limite mensual" })
  ] });
}
function ModalAnalisis({
  analisis,
  onCerrar
}) {
  useEscapeKey(true, onCerrar);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-5 h-5 text-purple-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Resultado del analisis" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Prioridad" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: `inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${COLORES_PRIORIDAD[analisis.prioridad]}`,
            children: ETIQUETAS_PRIORIDAD[analisis.prioridad]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-xs text-superficie-500 uppercase tracking-wide mb-2", children: "Resumen" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 leading-relaxed", children: analisis.resumen })
      ] }),
      analisis.fechasClaves.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-xs text-superficie-500 uppercase tracking-wide mb-2 flex items-center gap-1.5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Calendar, { className: "w-3.5 h-3.5" }),
          "Fechas clave"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: analisis.fechasClaves.map((fc, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: "flex items-start gap-3 px-3 py-2 rounded-lg bg-superficie-800/60 border border-white/[0.04]",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-mono text-acento-400 whitespace-nowrap mt-0.5", children: fc.fecha }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-300", children: fc.descripcion })
            ]
          },
          i
        )) })
      ] }),
      analisis.accionesRequeridas.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-xs text-superficie-500 uppercase tracking-wide mb-2 flex items-center gap-1.5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(ClipboardList, { className: "w-3.5 h-3.5" }),
          "Acciones requeridas"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: analisis.accionesRequeridas.map((ar, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: "flex items-start gap-3 px-3 py-2 rounded-lg bg-superficie-800/60 border border-white/[0.04]",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-1.5 h-1.5 rounded-full bg-amber-400 mt-2 shrink-0" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-200", children: ar.accion }),
                ar.plazo && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500 ml-2", children: [
                  "Plazo: ",
                  ar.plazo
                ] })
              ] })
            ]
          },
          i
        )) })
      ] }),
      Object.keys(analisis.datosExtraidos).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-xs text-superficie-500 uppercase tracking-wide mb-2", children: "Datos extraidos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-lg bg-superficie-800/60 border border-white/[0.04] p-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("dl", { className: "space-y-1.5", children: Object.entries(analisis.datosExtraidos).map(([clave, valor]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2 text-sm", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("dt", { className: "text-superficie-500 capitalize", children: [
            clave,
            ":"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("dd", { className: "text-superficie-200", children: String(valor) })
        ] }, clave)) }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4 pt-3 border-t border-white/[0.06] text-xs text-superficie-500", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          "Modelo: ",
          analisis.modelo
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          "Tokens: ",
          analisis.tokens
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: new Date(analisis.creadoEn).toLocaleDateString("es-ES", {
          day: "2-digit",
          month: "2-digit",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit"
        }) })
      ] })
    ] })
  ] }) });
}
export {
  PaginaAegis
};
