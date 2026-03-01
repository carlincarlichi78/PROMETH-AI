import { c as createLucideIcon, d as apiClient, r as reactExports, j as jsxRuntimeExports, $ as FileDown, X, I as CircleX, T as TriangleAlert } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { C as CircleCheck } from "./circle-check-BxiPcB-x.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Hash = createLucideIcon("Hash", [
  ["line", { x1: "4", x2: "20", y1: "9", y2: "9", key: "4lhtct" }],
  ["line", { x1: "4", x2: "20", y1: "15", y2: "15", key: "vyu0kd" }],
  ["line", { x1: "10", x2: "8", y1: "3", y2: "21", key: "1ggp8o" }],
  ["line", { x1: "16", x2: "14", y1: "3", y2: "21", key: "weycgp" }]
]);
const BASE = "/documentos-descargados";
async function listarDocumentosDescargadosApi(params) {
  const query = new URLSearchParams();
  if (params?.certificadoId) query.set("certificadoId", params.certificadoId);
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.exito !== void 0) query.set("exito", String(params.exito));
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  const qs = query.toString();
  const respuesta = await apiClient.get(`${BASE}${qs ? `?${qs}` : ""}`);
  return {
    datos: respuesta.datos ?? [],
    meta: respuesta.meta ?? {
      total: 0,
      pagina: 1,
      limite: 20,
      totalPaginas: 0
    }
  };
}
async function obtenerEstadisticasDocsApi() {
  const respuesta = await apiClient.get(`${BASE}/estadisticas`);
  return respuesta.datos;
}
const NOMBRES_TIPO = {
  DEUDAS_AEAT: "Deudas AEAT",
  DATOS_FISCALES: "Datos Fiscales",
  CERTIFICADOS_IRPF: "Certificados IRPF",
  CNAE_AUTONOMO: "CNAE Autonomo",
  IAE_ACTIVIDADES: "IAE Actividades",
  DEUDAS_SS: "Deudas Seg. Social",
  VIDA_LABORAL: "Vida Laboral",
  CERTIFICADO_INSS: "Certificado INSS",
  CONSULTA_VEHICULOS: "Consulta Vehiculos",
  CONSULTA_INMUEBLES: "Consulta Inmuebles",
  EMPADRONAMIENTO: "Empadronamiento",
  CERTIFICADO_PENALES: "Cert. Penales",
  CERTIFICADO_NACIMIENTO: "Cert. Nacimiento",
  APUD_ACTA: "Apud Acta",
  CERTIFICADO_SEPE: "Certificado SEPE",
  SOLICITUD_CIRBE: "Solicitud CIRBE",
  OBTENCION_CIRBE: "Obtencion CIRBE",
  DEUDAS_HACIENDA: "Deudas Hacienda",
  CERTIFICADO_MATRIMONIO: "Cert. Matrimonio",
  PROC_ABIERTOS_GENERAL: "Licitaciones General",
  PROC_ABIERTOS_MADRID: "Licitaciones Madrid",
  PROC_ABIERTOS_ANDALUCIA: "Licitaciones Andalucia",
  PROC_ABIERTOS_VALENCIA: "Licitaciones Valencia",
  PROC_ABIERTOS_CATALUNYA: "Licitaciones Catalunya"
};
const COLORES_PORTAL = {
  AEAT: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
  SEGURIDAD_SOCIAL: "bg-orange-500/10 text-orange-400 border border-orange-500/20",
  CARPETA_CIUDADANA: "bg-purple-500/10 text-purple-400 border border-purple-500/20",
  JUSTICIA: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
  SEPE: "bg-teal-500/10 text-teal-400 border border-teal-500/20",
  BANCO_ESPANA: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
  LICITACIONES: "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
};
const TIPOS_DISPONIBLES = Object.keys(NOMBRES_TIPO);
function fechaRelativa(fecha) {
  const ahora = Date.now();
  const diff = ahora - new Date(fecha).getTime();
  const mins = Math.floor(diff / 6e4);
  if (mins < 1) return "Hace un momento";
  if (mins < 60) return `Hace ${mins} min`;
  const horas = Math.floor(mins / 60);
  if (horas < 24) return `Hace ${horas}h`;
  const dias = Math.floor(horas / 24);
  if (dias < 7) return `Hace ${dias}d`;
  return formatearFecha(fecha);
}
function PaginaDocumentosDescargados() {
  const [documentos, setDocumentos] = reactExports.useState([]);
  const [estadisticas, setEstadisticas] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(0);
  const [filtroTipo, setFiltroTipo] = reactExports.useState("");
  const [filtroEstado, setFiltroEstado] = reactExports.useState("");
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [docsRes, statsRes] = await Promise.all([
        listarDocumentosDescargadosApi({
          pagina,
          limite: 20,
          tipo: filtroTipo || void 0,
          exito: filtroEstado === "" ? void 0 : filtroEstado === "exitoso"
        }),
        obtenerEstadisticasDocsApi()
      ]);
      setDocumentos(docsRes.datos);
      setTotalPaginas(docsRes.meta.totalPaginas);
      setEstadisticas(statsRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar documentos");
    } finally {
      setCargando(false);
    }
  }, [pagina, filtroTipo, filtroEstado]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  reactExports.useEffect(() => {
    setPagina(1);
  }, [filtroTipo, filtroEstado]);
  if (cargando && documentos.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin" }) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(FileDown, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Documentos Descargados" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Documentos descargados automaticamente desde el desktop" })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    estadisticas && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 lg:grid-cols-5 gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: Hash,
          valor: estadisticas.total,
          subtitulo: "Total descargas",
          color: "blue"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: CircleCheck,
          valor: estadisticas.exitos,
          subtitulo: "Exitosas",
          color: "green"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: CircleX,
          valor: estadisticas.erroresCount,
          subtitulo: "Errores",
          color: "red"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: TriangleAlert,
          valor: estadisticas.capturas,
          subtitulo: "Capturas (no originales)",
          color: "amber"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: Clock,
          valor: estadisticas.ultimaDescarga ? fechaRelativa(estadisticas.ultimaDescarga) : "N/A",
          subtitulo: "Ultima descarga",
          color: "purple"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtroTipo,
          onChange: (e) => setFiltroTipo(e.target.value),
          className: "px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg\n            bg-superficie-800/60 outline-none focus:ring-2 focus:ring-acento-500/40",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todos los tipos" }),
            TIPOS_DISPONIBLES.map((t) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: t, children: NOMBRES_TIPO[t] }, t))
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtroEstado,
          onChange: (e) => setFiltroEstado(e.target.value),
          className: "px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg\n            bg-superficie-800/60 outline-none focus:ring-2 focus:ring-acento-500/40",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todos los estados" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "exitoso", children: "Exitoso" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "error", children: "Error" })
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: documentos.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(FileDown, { className: "w-10 h-10 text-superficie-500 mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-superficie-400 text-sm text-center", children: [
        "No hay documentos descargados.",
        /* @__PURE__ */ jsxRuntimeExports.jsx("br", {}),
        "Usa la aplicacion de escritorio para descargar documentos."
      ] })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tipo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Archivo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Portal" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Titular" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Calidad" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: documentos.map((doc) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 font-medium text-superficie-100", children: NOMBRES_TIPO[doc.tipo] ?? doc.tipo }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 max-w-[200px] truncate", title: doc.nombreArchivo, children: doc.nombreArchivo }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_PORTAL[doc.portal] ?? "bg-superficie-800 text-superficie-400 border border-white/[0.06]"}`, children: doc.portal.replace(/_/g, " ") }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300", children: doc.nombreTitular ?? doc.dniCifTitular ?? "-" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: doc.exito ? /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheck, { className: "w-3 h-3" }),
            "Exitoso"
          ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20", title: doc.error ?? void 0, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-3 h-3" }),
            "Error"
          ] }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: doc.esDocumentoReal === false ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "span",
            {
              className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20",
              title: `Metodo: ${doc.metodoDescarga ?? "desconocido"}`,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(TriangleAlert, { className: "w-3 h-3" }),
                "Captura"
              ]
            }
          ) : /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheck, { className: "w-3 h-3" }),
            "Original"
          ] }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap", children: formatearFecha(doc.fechaDescarga) })
        ] }, doc.id)) })
      ] }) }),
      totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-3 border-t border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setPagina((p) => Math.max(1, p - 1)),
            disabled: pagina <= 1,
            className: "flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-superficie-400\n                    hover:text-white hover:bg-white/[0.05] disabled:opacity-40 disabled:cursor-not-allowed\n                    rounded-lg transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-3.5 h-3.5" }),
              "Anterior"
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
          "Pagina ",
          pagina,
          " de ",
          totalPaginas
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
            disabled: pagina >= totalPaginas,
            className: "flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-superficie-400\n                    hover:text-white hover:bg-white/[0.05] disabled:opacity-40 disabled:cursor-not-allowed\n                    rounded-lg transition-colors",
            children: [
              "Siguiente",
              /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-3.5 h-3.5" })
            ]
          }
        )
      ] })
    ] }) })
  ] });
}
const COLORES_KPI = {
  blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  green: "bg-green-500/10 text-green-400 border-green-500/20",
  red: "bg-red-500/10 text-red-400 border-red-500/20",
  amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  purple: "bg-purple-500/10 text-purple-400 border-purple-500/20"
};
function CardKpi({
  icono: Icono,
  valor,
  subtitulo,
  color
}) {
  const claseColor = COLORES_KPI[color] ?? COLORES_KPI.blue;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl p-5", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-3 mb-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-9 h-9 rounded-lg border flex items-center justify-center ${claseColor}`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4.5 h-4.5" }) }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-2xl font-bold text-white", children: valor }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-1", children: subtitulo })
  ] });
}
export {
  PaginaDocumentosDescargados
};
