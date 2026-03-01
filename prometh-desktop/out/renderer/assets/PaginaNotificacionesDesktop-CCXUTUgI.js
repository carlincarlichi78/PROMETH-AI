const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["./integracionesServicio-C-79KoQl.js","./index-DMbE3NR1.js","./index-UY9qchYi.css"])))=>i.map(i=>d[i]);
import { c as createLucideIcon, j as jsxRuntimeExports, r as reactExports, z as useAuthStore, B as Bell, T as TriangleAlert, C as CalendarDays, m as Search, p as Brain, f as CircleCheckBig, I as CircleX, D as Download, E as Eye, an as __vitePreload, d as apiClient, X, F as FolderOpen, q as FileText, al as UserCheck, _ as Inbox, ao as BellRing, ag as Settings, $ as FileDown, ap as Cloud, W as Workflow, A as Activity, a as Shield, v as Check } from "./index-DMbE3NR1.js";
import { l as listarNotificacionesApi, a as obtenerDashboardPlazosApi, c as eliminarNotificacionesBatchApi, o as obtenerHistorialApi, b as actualizarNotificacionApi } from "./notificacionesServicio-B3Srptx0.js";
import { S as SelectorCertificados, C as CalendarCheck } from "./SelectorCertificados-Dv92DoP7.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { F as FileCheck } from "./file-check-CGZ00Z_g.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { l as listarHistorialAegisApi } from "./aegisServicio-6JqSkwLW.js";
import { L as ListTodo } from "./list-todo-WH_1tbpH.js";
import { C as CalendarPlus } from "./calendar-plus-DByXh6wM.js";
import { T as Tag } from "./tag-wvcc-Qrp.js";
import { M as Mail } from "./mail-BDEpMyrm.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import "./certificadosServicio-DtEVLLjT.js";
import "./award-CLV5ctGj.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CheckCheck = createLucideIcon("CheckCheck", [
  ["path", { d: "M18 6 7 17l-5-5", key: "116fxf" }],
  ["path", { d: "m22 10-7.5 7.5L13 16", key: "ke71qq" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CloudDownload = createLucideIcon("CloudDownload", [
  ["path", { d: "M12 13v8l-4-4", key: "1f5nwf" }],
  ["path", { d: "m12 21 4-4", key: "1lfcce" }],
  ["path", { d: "M4.393 15.269A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.436 8.284", key: "ui1hmy" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const FilePen = createLucideIcon("FilePen", [
  ["path", { d: "M12.5 22H18a2 2 0 0 0 2-2V7l-5-5H6a2 2 0 0 0-2 2v9.5", key: "1couwa" }],
  ["path", { d: "M14 2v4a2 2 0 0 0 2 2h4", key: "tnqrlb" }],
  [
    "path",
    {
      d: "M13.378 15.626a1 1 0 1 0-3.004-3.004l-5.01 5.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z",
      key: "1y4qbx"
    }
  ]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const ScanText = createLucideIcon("ScanText", [
  ["path", { d: "M3 7V5a2 2 0 0 1 2-2h2", key: "aa7l1z" }],
  ["path", { d: "M17 3h2a2 2 0 0 1 2 2v2", key: "4qcy5o" }],
  ["path", { d: "M21 17v2a2 2 0 0 1-2 2h-2", key: "6vwrx8" }],
  ["path", { d: "M7 21H5a2 2 0 0 1-2-2v-2", key: "ioqczr" }],
  ["path", { d: "M7 8h8", key: "1jbsf9" }],
  ["path", { d: "M7 12h10", key: "b7w52i" }],
  ["path", { d: "M7 16h6", key: "1vyc9m" }]
]);
function SemaforoUrgencia({ diasRestantes, vencida }) {
  const obtenerEstilo = () => {
    if (vencida || diasRestantes != null && diasRestantes <= 0) {
      return { color: "bg-gray-400", pulso: false, titulo: "Caducada" };
    }
    if (diasRestantes == null) {
      return { color: "bg-gray-600", pulso: false, titulo: "Sin plazo" };
    }
    if (diasRestantes <= 2) {
      return { color: "bg-red-500", pulso: true, titulo: `${diasRestantes} dias` };
    }
    if (diasRestantes <= 5) {
      return { color: "bg-red-500", pulso: false, titulo: `${diasRestantes} dias` };
    }
    if (diasRestantes <= 8) {
      return { color: "bg-amber-400", pulso: false, titulo: `${diasRestantes} dias` };
    }
    return { color: "bg-green-500", pulso: false, titulo: `${diasRestantes} dias` };
  };
  const { color, pulso, titulo } = obtenerEstilo();
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "span",
    {
      className: `inline-block w-3 h-3 rounded-full ${color} ${pulso ? "animate-pulse" : ""}`,
      title: titulo
    }
  );
}
const COLORES_ESTADO = {
  pendiente: "bg-blue-500/20 text-blue-400",
  leida: "bg-amber-500/20 text-amber-400",
  gestionada: "bg-green-500/20 text-green-400",
  descartada: "bg-gray-500/20 text-gray-400"
};
function obtenerEstadoVisual(notif) {
  if (notif.estado === "pendiente" && notif.vencida) {
    return { texto: "Caducada", color: "bg-gray-600/20 text-gray-500" };
  }
  return {
    texto: notif.estado.charAt(0).toUpperCase() + notif.estado.slice(1),
    color: COLORES_ESTADO[notif.estado] ?? ""
  };
}
function formatearFecha$1(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  const anio = d.getFullYear();
  return `${dia}/${mes}/${anio}`;
}
function formatearFechaCorta(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}`;
}
const ABREVIATURAS_ADMIN = {
  "tesoreria general de la seguridad social": "TGSS",
  "agencia estatal de administracion tributaria": "AEAT",
  "agencia tributaria": "AEAT",
  "direccion general de trafico": "DGT",
  "servicio publico de empleo estatal": "SEPE",
  "instituto nacional de la seguridad social": "INSS",
  "direccion general del catastro": "Catastro",
  "ministerio de justicia": "M. Justicia",
  "registro civil": "Reg. Civil",
  "seguridad social": "Seg. Social",
  "junta de andalucia": "J. Andalucia",
  "generalitat de catalunya": "Generalitat",
  "comunidad de madrid": "C. Madrid",
  "gobierno vasco": "Gob. Vasco",
  "xunta de galicia": "Xunta",
  "generalitat valenciana": "G. Valenciana"
};
function abreviarAdmin(nombre) {
  if (!nombre) return "";
  const lower = nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  for (const [patron, abreviatura] of Object.entries(ABREVIATURAS_ADMIN)) {
    if (lower.includes(patron)) return abreviatura;
  }
  return nombre.length > 20 ? nombre.substring(0, 18) + "..." : nombre;
}
function colorDiasPlazo(dias) {
  if (dias == null) return "bg-gray-500";
  if (dias <= 0) return "bg-gray-500";
  if (dias <= 3) return "bg-red-500";
  if (dias <= 7) return "bg-amber-500";
  return "bg-green-500";
}
function colorTextoPlazo(dias) {
  if (dias == null) return "text-gray-500";
  if (dias <= 0) return "text-gray-500 line-through";
  if (dias <= 3) return "text-red-400";
  if (dias <= 7) return "text-amber-400";
  return "text-green-400";
}
function colorImporte(importeStr) {
  if (!importeStr) return "text-gray-500";
  const limpio = importeStr.replace(/[€\s]/g, "").replace(/\./g, "").replace(",", ".");
  const valor = parseFloat(limpio);
  if (isNaN(valor)) return "text-gray-300";
  if (valor >= 5e3) return "text-red-400 font-semibold";
  if (valor >= 1e3) return "text-amber-400 font-medium";
  return "text-gray-200";
}
function BadgeEstado({ notif }) {
  const { texto, color } = obtenerEstadoVisual(notif);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-2 py-0.5 rounded-full text-xs font-medium ${color}`, children: texto });
}
const COLORES_PRIORIDAD_IA = {
  alta: "bg-red-500/20 text-red-400",
  media: "bg-amber-500/20 text-amber-400",
  baja: "bg-green-500/20 text-green-400"
};
function BadgePrioridadIA({ prioridad }) {
  const color = COLORES_PRIORIDAD_IA[prioridad] ?? "bg-gray-500/20 text-gray-400";
  const texto = prioridad.charAt(0).toUpperCase() + prioridad.slice(1);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-1.5 py-0.5 rounded text-[10px] font-semibold ${color}`, children: texto });
}
function CeldaPlazos({ notif }) {
  const tieneAcceso = notif.fechaLimiteAcceso != null;
  const tieneRespuesta = notif.fechaLimiteRespuesta != null;
  const tienePlazoIA = notif.plazoRecursoIA != null;
  if (!tieneAcceso && !tieneRespuesta && !tienePlazoIA) {
    if (notif.fechaPublicacion) {
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-[11px] leading-tight", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-500", children: "Pub: " }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-400", children: formatearFechaCorta(notif.fechaPublicacion) })
      ] });
    }
    return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-600", children: "—" });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-0.5 text-[11px] leading-tight", children: [
    tieneAcceso && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", title: `Acceso: ${formatearFecha$1(notif.fechaLimiteAcceso)} (${notif.diasRestantesAcceso ?? "?"} dias)`, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full shrink-0 ${colorDiasPlazo(notif.diasRestantesAcceso)}` }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-500", children: "Acceso" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: colorTextoPlazo(notif.diasRestantesAcceso), children: formatearFecha$1(notif.fechaLimiteAcceso) }),
      notif.diasRestantesAcceso != null && notif.diasRestantesAcceso > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-gray-600", children: [
        "(",
        notif.diasRestantesAcceso,
        "d)"
      ] })
    ] }),
    tieneRespuesta && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", title: `Respuesta: ${formatearFecha$1(notif.fechaLimiteRespuesta)} (${notif.diasRestantesRespuesta ?? "?"} dias)`, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full shrink-0 ${colorDiasPlazo(notif.diasRestantesRespuesta)}` }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-500", children: "Resp." }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: colorTextoPlazo(notif.diasRestantesRespuesta), children: formatearFecha$1(notif.fechaLimiteRespuesta) }),
      notif.diasRestantesRespuesta != null && notif.diasRestantesRespuesta > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-gray-600", children: [
        "(",
        notif.diasRestantesRespuesta,
        "d)"
      ] })
    ] }),
    tienePlazoIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", title: `Recurso IA: ${notif.plazoRecursoIA}`, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-1.5 h-1.5 rounded-full shrink-0 bg-blue-500" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-500", children: "Recurso" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue-400 truncate max-w-[100px]", children: notif.plazoRecursoIA })
    ] })
  ] });
}
function CeldaImporte({ notif }) {
  if (!notif.importeIA) return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-600", children: "—" });
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs whitespace-nowrap ${colorImporte(notif.importeIA)}`, title: notif.importeIA, children: notif.importeIA });
}
function CardKpi({
  icono: Icono,
  valor,
  etiqueta,
  colorIcono
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#1a1a2e]/60 border border-white/10 rounded-xl p-4 flex items-center gap-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `p-2 rounded-lg ${colorIcono}`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-5 h-5" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-2xl font-bold text-white", children: valor }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-gray-400", children: etiqueta })
    ] })
  ] });
}
function EsqueletoFila() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { className: "border-b border-white/5", children: Array.from({ length: 7 }).map((_, i) => /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-4 bg-white/5 rounded animate-pulse" }) }, i)) });
}
function TabBandejaPortales({ onSeleccionarNotificacion, onDescargarPdf, onAbrirPdf, onDescargarBatch, onAnalizarIA }) {
  const [notificaciones, setNotificaciones] = reactExports.useState([]);
  const [plazos, setPlazos] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [descargandoId, setDescargandoId] = reactExports.useState(null);
  const [resultadoDescarga, setResultadoDescarga] = reactExports.useState({});
  const [filtros, setFiltros] = reactExports.useState({ busqueda: "", estado: "", urgencia: "", certificadoIds: "" });
  const [paginaActual, setPaginaActual] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [pdfsDescargados, setPdfsDescargados] = reactExports.useState({});
  const [analizandoId, setAnalizandoId] = reactExports.useState(null);
  const [analizandoBatch, setAnalizandoBatch] = reactExports.useState(null);
  const [sincPlazos, setSincPlazos] = reactExports.useState({ pendientes: 0, sincronizando: false });
  const [seleccionados, setSeleccionados] = reactExports.useState(/* @__PURE__ */ new Set());
  const [eliminando, setEliminando] = reactExports.useState(false);
  const [confirmarEliminar, setConfirmarEliminar] = reactExports.useState(false);
  const rolUsuario = useAuthStore((s) => s.usuario?.rol);
  const esAdmin = rolUsuario === "admin" || rolUsuario === "superadmin";
  const [version, setVersion] = reactExports.useState(0);
  const notificacionesRef = reactExports.useRef([]);
  notificacionesRef.current = notificaciones;
  reactExports.useEffect(() => {
    const manejarFoco = () => {
      if (notificacionesRef.current.length > 0) {
        verificarPdfsDescargados(notificacionesRef.current);
      }
    };
    window.addEventListener("focus", manejarFoco);
    return () => window.removeEventListener("focus", manejarFoco);
  }, []);
  const [busquedaInput, setBusquedaInput] = reactExports.useState("");
  const timerRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    let cancelado = false;
    const cargar = async () => {
      setCargando(true);
      try {
        const params = {
          pagina: paginaActual,
          limite: 20
        };
        if (filtros.busqueda) params.busqueda = filtros.busqueda;
        if (filtros.estado) params.estado = filtros.estado;
        if (filtros.urgencia) params.urgencia = filtros.urgencia;
        if (filtros.certificadoIds) params.certificadoIds = filtros.certificadoIds;
        const [listado, dashPlazos] = await Promise.all([
          listarNotificacionesApi(params),
          obtenerDashboardPlazosApi()
        ]);
        if (!cancelado) {
          setNotificaciones(listado.notificaciones);
          setTotalPaginas(listado.meta.totalPaginas);
          setPlazos(dashPlazos);
          verificarPdfsDescargados(listado.notificaciones);
          __vitePreload(async () => {
            const { obtenerEstadoSyncPlazosApi } = await import("./integracionesServicio-C-79KoQl.js");
            return { obtenerEstadoSyncPlazosApi };
          }, true ? __vite__mapDeps([0,1,2]) : void 0, import.meta.url).then(({ obtenerEstadoSyncPlazosApi }) => obtenerEstadoSyncPlazosApi()).then((estado) => {
            if (!cancelado) setSincPlazos((prev) => ({ ...prev, pendientes: estado.totalPendientes }));
          }).catch(() => {
          });
        }
      } catch {
      }
      if (!cancelado) setCargando(false);
    };
    cargar();
    return () => {
      cancelado = true;
    };
  }, [filtros, paginaActual, version]);
  const verificarPdfsDescargados = async (notifs) => {
    const api = window.electronAPI;
    if (!api?.dehu?.verificarPdfsBatch) return;
    const items = notifs.filter((n) => n.idExterno && n.certificadoSerial).map((n) => ({ idDehu: n.idExterno, certificadoSerial: n.certificadoSerial }));
    if (items.length === 0) return;
    try {
      const resultado = await api.dehu.verificarPdfsBatch(items);
      setPdfsDescargados((prev) => ({ ...prev, ...resultado }));
    } catch {
    }
  };
  const manejarCambioBusqueda = (valor) => {
    setBusquedaInput(valor);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setPaginaActual(1);
      setFiltros((prev) => ({ ...prev, busqueda: valor }));
    }, 300);
  };
  const manejarCambioEstado = (valor) => {
    setPaginaActual(1);
    setFiltros((prev) => ({ ...prev, estado: valor }));
  };
  const manejarCambioUrgencia = (valor) => {
    setPaginaActual(1);
    setFiltros((prev) => ({ ...prev, urgencia: valor }));
  };
  const manejarFiltroCertificados = (ids) => {
    setPaginaActual(1);
    setFiltros((prev) => ({ ...prev, certificadoIds: ids.join(",") }));
  };
  const refrescar = () => setVersion((v) => v + 1);
  const toggleSeleccion = (id) => {
    setSeleccionados((prev) => {
      const nuevo = new Set(prev);
      if (nuevo.has(id)) nuevo.delete(id);
      else nuevo.add(id);
      return nuevo;
    });
  };
  const toggleSeleccionTodos = () => {
    if (seleccionados.size === notificaciones.length) {
      setSeleccionados(/* @__PURE__ */ new Set());
    } else {
      setSeleccionados(new Set(notificaciones.map((n) => n.id)));
    }
  };
  const manejarEliminarBatch = async () => {
    if (seleccionados.size === 0) return;
    setEliminando(true);
    try {
      await eliminarNotificacionesBatchApi(Array.from(seleccionados));
      setSeleccionados(/* @__PURE__ */ new Set());
      setConfirmarEliminar(false);
      setVersion((v) => v + 1);
    } catch {
    } finally {
      setEliminando(false);
    }
  };
  const manejarAnalisis = async (e, notif) => {
    e.stopPropagation();
    if (!onAnalizarIA) return;
    setAnalizandoId(notif.id);
    try {
      await onAnalizarIA(notif);
    } catch {
    } finally {
      setAnalizandoId(null);
      setVersion((v) => v + 1);
    }
  };
  const manejarAnalisisBatch = async () => {
    if (!onAnalizarIA) return;
    const sinAnalizar2 = notificaciones.filter((n) => !n.prioridadIA);
    if (sinAnalizar2.length === 0) return;
    setAnalizandoBatch({ actual: 0, total: sinAnalizar2.length });
    for (let i = 0; i < sinAnalizar2.length; i++) {
      setAnalizandoBatch({ actual: i + 1, total: sinAnalizar2.length });
      try {
        await onAnalizarIA(sinAnalizar2[i]);
      } catch {
      }
    }
    setAnalizandoBatch(null);
    setVersion((v) => v + 1);
  };
  const manejarSyncPlazosBatch = async () => {
    setSincPlazos((prev) => ({ ...prev, sincronizando: true }));
    try {
      const { syncPlazosBatchApi } = await __vitePreload(async () => {
        const { syncPlazosBatchApi: syncPlazosBatchApi2 } = await import("./integracionesServicio-C-79KoQl.js");
        return { syncPlazosBatchApi: syncPlazosBatchApi2 };
      }, true ? __vite__mapDeps([0,1,2]) : void 0, import.meta.url);
      await syncPlazosBatchApi();
    } catch {
    } finally {
      setSincPlazos({ pendientes: 0, sincronizando: false });
      setVersion((v) => v + 1);
    }
  };
  const manejarDescarga = async (e, notif) => {
    e.stopPropagation();
    if (!onDescargarPdf) return;
    setDescargandoId(notif.id);
    try {
      const res = await onDescargarPdf(notif);
      if (res) {
        setResultadoDescarga((prev) => ({ ...prev, [notif.id]: res }));
        if (res.exito && notif.idExterno) {
          setPdfsDescargados((prev) => ({
            ...prev,
            [notif.idExterno]: { descargado: true, rutaLocal: res.rutaLocal }
          }));
        }
        setTimeout(() => {
          setResultadoDescarga((prev) => {
            const { [notif.id]: _, ...rest } = prev;
            return rest;
          });
        }, 15e3);
      }
    } catch {
      setResultadoDescarga((prev) => ({
        ...prev,
        [notif.id]: { exito: false, error: "Error de comunicacion" }
      }));
      setTimeout(() => {
        setResultadoDescarga((prev) => {
          const { [notif.id]: _, ...rest } = prev;
          return rest;
        });
      }, 15e3);
    }
    setDescargandoId(null);
  };
  const abrirPdfLocal = async (e, rutaLocal) => {
    e.stopPropagation();
    if (onAbrirPdf) {
      await onAbrirPdf(rutaLocal);
    }
  };
  const urgentes = plazos ? plazos.porUrgencia.critica + plazos.porUrgencia.alta : 0;
  const sinDescargar = notificaciones.filter(
    (n) => n.idExterno && !pdfsDescargados[n.idExterno]?.descargado
  );
  const sinAnalizar = notificaciones.filter((n) => !n.prioridadIA);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-4 gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: Bell,
          valor: plazos?.totalPendientes ?? 0,
          etiqueta: "Total pendientes",
          colorIcono: "bg-blue-500/20 text-blue-400"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: TriangleAlert,
          valor: urgentes,
          etiqueta: "Urgentes",
          colorIcono: "bg-red-500/20 text-red-400"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: Clock,
          valor: plazos?.vencidasHoy ?? 0,
          etiqueta: "Vencen hoy",
          colorIcono: "bg-amber-500/20 text-amber-400"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          icono: CalendarDays,
          valor: plazos?.vencenEstaSemana ?? 0,
          etiqueta: "Esta semana",
          colorIcono: "bg-green-500/20 text-green-400"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: busquedaInput,
            onChange: (e) => manejarCambioBusqueda(e.target.value),
            placeholder: "Buscar notificaciones...",
            className: "w-full pl-10 pr-3 py-2 bg-[#0f0f23] border border-white/10 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500/50"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtros.estado,
          onChange: (e) => manejarCambioEstado(e.target.value),
          className: "px-3 py-2 bg-[#0f0f23] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500/50",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todos" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "pendiente", children: "Pendiente" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "leida", children: "Leida" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "gestionada", children: "Gestionada" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "descartada", children: "Descartada" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtros.urgencia,
          onChange: (e) => manejarCambioUrgencia(e.target.value),
          className: "px-3 py-2 bg-[#0f0f23] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500/50",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todas" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "critica", children: "Critica" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "alta", children: "Alta" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "media", children: "Media" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "baja", children: "Baja" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        SelectorCertificados,
        {
          seleccionados: filtros.certificadoIds ? filtros.certificadoIds.split(",") : [],
          onChange: manejarFiltroCertificados
        }
      ),
      onDescargarBatch && sinDescargar.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => onDescargarBatch(sinDescargar),
          title: `Descargar ${sinDescargar.length} PDFs pendientes`,
          className: "flex items-center gap-1.5 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg text-sm text-blue-400 hover:bg-blue-500/20 transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CloudDownload, { className: "w-4 h-4" }),
            sinDescargar.length
          ]
        }
      ),
      onAnalizarIA && sinAnalizar.length > 0 && !analizandoBatch && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarAnalisisBatch,
          title: `Analizar ${sinAnalizar.length} notificaciones con IA`,
          className: "flex items-center gap-1.5 px-3 py-2 bg-purple-500/10 border border-purple-500/20 rounded-lg text-sm text-purple-400 hover:bg-purple-500/20 transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-4 h-4" }),
            sinAnalizar.length
          ]
        }
      ),
      analizandoBatch && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1.5 px-3 py-2 text-sm text-purple-400 whitespace-nowrap", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
        analizandoBatch.actual,
        "/",
        analizandoBatch.total
      ] }),
      sincPlazos.pendientes > 0 && !sincPlazos.sincronizando && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarSyncPlazosBatch,
          title: `Sincronizar ${sincPlazos.pendientes} notificaciones a Google Calendar`,
          className: "flex items-center gap-1.5 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-sm text-emerald-400 hover:bg-emerald-500/20 transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarCheck, { className: "w-4 h-4" }),
            sincPlazos.pendientes
          ]
        }
      ),
      sincPlazos.sincronizando && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1.5 px-3 py-2 text-sm text-emerald-400 whitespace-nowrap", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
        "Sincronizando..."
      ] }),
      esAdmin && seleccionados.size > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setConfirmarEliminar(true),
          title: `Eliminar ${seleccionados.size} notificaciones`,
          className: "flex items-center gap-1.5 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400 hover:bg-red-500/20 transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" }),
            seleccionados.size
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: refrescar,
          title: "Refrescar datos",
          className: "p-2 rounded-lg border border-white/10 text-gray-400 hover:text-white hover:bg-white/5 transition-colors",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: `w-4 h-4 ${cargando ? "animate-spin" : ""}` })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-[#1a1a2e]/40 border border-white/10 rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm table-fixed", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "bg-white/5 text-xs text-gray-400 uppercase", children: [
        esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-10 px-2 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "checkbox",
            checked: notificaciones.length > 0 && seleccionados.size === notificaciones.length,
            onChange: toggleSeleccionTodos,
            className: "w-4 h-4 rounded border-2 border-gray-400 bg-gray-700 cursor-pointer accent-blue-500"
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-14 px-2 py-2 text-left", children: "Urg." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-2 py-2 text-left", children: "Titular / Asunto" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-24 px-2 py-2 text-left", children: "Admin." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-52 px-2 py-2 text-left", children: "Plazos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-28 px-2 py-2 text-right", children: "Importe" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-24 px-2 py-2 text-left", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-28 px-2 py-2 text-center", children: "Acc." })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: cargando ? Array.from({ length: 6 }).map((_, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(EsqueletoFila, {}, i)) : notificaciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: esAdmin ? 8 : 7, className: "px-3 py-12 text-center text-gray-500", children: "No hay notificaciones" }) }) : notificaciones.map((notif) => {
        const contenidoCorto = notif.contenido ? notif.contenido.length > 60 ? notif.contenido.substring(0, 60) + "..." : notif.contenido : "";
        const pdfInfo = notif.idExterno ? pdfsDescargados[notif.idExterno] : void 0;
        const tieneDescarga = pdfInfo?.descargado === true;
        const infoIA = [];
        if (notif.procedimientoIA) infoIA.push(notif.procedimientoIA);
        if (notif.deudorIA && notif.deudorIA !== notif.certificadoNombre) {
          infoIA.push(notif.deudorIA);
        }
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "tr",
          {
            onClick: () => onSeleccionarNotificacion(notif),
            className: `border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer ${seleccionados.has(notif.id) ? "bg-blue-500/[0.04]" : ""}`,
            children: [
              esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-10 px-2 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  type: "checkbox",
                  checked: seleccionados.has(notif.id),
                  onChange: () => toggleSeleccion(notif.id),
                  onClick: (e) => e.stopPropagation(),
                  className: "w-4 h-4 rounded border-2 border-gray-400 bg-gray-700 cursor-pointer accent-blue-500"
                }
              ) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-14 px-2 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-1", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  SemaforoUrgencia,
                  {
                    diasRestantes: notif.diasRestantesAcceso,
                    vencida: notif.vencida
                  }
                ),
                notif.prioridadIA && /* @__PURE__ */ jsxRuntimeExports.jsx(BadgePrioridadIA, { prioridad: notif.prioridadIA })
              ] }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-2 py-2 overflow-hidden", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "truncate", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-white font-medium text-sm", children: notif.certificadoNombre ?? "Sin titular" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-600 mx-1.5", children: "·" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium px-1.5 py-0.5 rounded bg-white/5 text-gray-400", children: abreviarAdmin(notif.administracion) })
                ] }),
                contenidoCorto && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[11px] text-gray-500 truncate mt-0.5", title: notif.contenido ?? "", children: contenidoCorto }),
                infoIA.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[11px] text-gray-400 truncate mt-0.5", children: infoIA.join(" · ") })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-24 px-2 py-2 text-gray-400 text-xs whitespace-nowrap", children: formatearFechaCorta(notif.fechaPublicacion || notif.fechaDeteccion) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-52 px-2 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CeldaPlazos, { notif }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-28 px-2 py-2 text-right", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CeldaImporte, { notif }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-24 px-2 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeEstado, { notif }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-28 px-2 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center gap-1", children: [
                onAnalizarIA && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    title: notif.prioridadIA ? `IA: ${notif.prioridadIA}${notif.procedimientoIA ? ` — ${notif.procedimientoIA}` : ""} (click re-analizar)` : "Analizar con IA",
                    disabled: analizandoId === notif.id || analizandoBatch !== null,
                    onClick: (e) => manejarAnalisis(e, notif),
                    className: `p-1.5 rounded-lg transition-colors disabled:opacity-40 ${analizandoId === notif.id ? "text-purple-400" : notif.prioridadIA ? `hover:bg-white/10 ${notif.prioridadIA === "alta" ? "text-red-400" : notif.prioridadIA === "media" ? "text-amber-400" : notif.prioridadIA === "baja" ? "text-green-400" : "text-purple-400"}` : "text-gray-600 hover:bg-white/10 hover:text-purple-400"}`,
                    children: analizandoId === notif.id ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-4 h-4" })
                  }
                ),
                !onAnalizarIA && notif.prioridadIA && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "span",
                  {
                    title: `IA: ${notif.prioridadIA}${notif.procedimientoIA ? ` — ${notif.procedimientoIA}` : ""}`,
                    className: `p-1 ${notif.prioridadIA === "alta" ? "text-red-400" : notif.prioridadIA === "media" ? "text-amber-400" : notif.prioridadIA === "baja" ? "text-green-400" : "text-purple-400"}`,
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-4 h-4" })
                  }
                ),
                notif.sincronizadoCalendario && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { title: "Plazos sincronizados a Google Calendar", className: "p-1 text-emerald-400", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarCheck, { className: "w-4 h-4" }) }),
                tieneDescarga && pdfInfo?.rutaLocal && onAbrirPdf && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    title: "Abrir PDF descargado",
                    onClick: (e) => abrirPdfLocal(e, pdfInfo.rutaLocal),
                    className: "p-1.5 rounded-lg hover:bg-green-500/10 text-green-400 transition-colors",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(FileCheck, { className: "w-4 h-4" })
                  }
                ),
                tieneDescarga && !onAbrirPdf && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { title: "PDF descargado", className: "p-1.5 text-green-400", children: /* @__PURE__ */ jsxRuntimeExports.jsx(FileCheck, { className: "w-4 h-4" }) }),
                onDescargarPdf && notif.idExterno && !tieneDescarga && (resultadoDescarga[notif.id] ? resultadoDescarga[notif.id].exito ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { title: "Descargado", className: "p-1.5 text-green-400", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-4 h-4" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { title: resultadoDescarga[notif.id].error ?? "Error", className: "p-1.5 text-red-400 cursor-help", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-4 h-4" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    title: "Descargar PDF",
                    disabled: descargandoId === notif.id,
                    onClick: (e) => manejarDescarga(e, notif),
                    className: "p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-blue-400 transition-colors disabled:opacity-40",
                    children: descargandoId === notif.id ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-4 h-4" })
                  }
                )),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    title: "Ver detalle",
                    onClick: (e) => {
                      e.stopPropagation();
                      onSeleccionarNotificacion(notif);
                    },
                    className: "p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-4 h-4" })
                  }
                )
              ] }) })
            ]
          },
          notif.id
        );
      }) })
    ] }) }),
    Object.entries(resultadoDescarga).filter(([, r]) => !r.exito).map(([id, r]) => {
      const notif = notificaciones.find((n) => n.id === id);
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-4 h-4 shrink-0" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "truncate", children: [
          "Error descargando ",
          notif?.certificadoNombre ?? notif?.idExterno ?? id,
          ": ",
          r.error || "Error desconocido"
        ] })
      ] }, id);
    }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setPaginaActual((p) => Math.max(1, p - 1)),
          disabled: paginaActual <= 1,
          className: "flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" }),
            "Anterior"
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-gray-400", children: [
        paginaActual,
        " / ",
        totalPaginas
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setPaginaActual((p) => Math.min(totalPaginas, p + 1)),
          disabled: paginaActual >= totalPaginas,
          className: "flex items-center gap-1 px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
          children: [
            "Siguiente",
            /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
          ]
        }
      )
    ] }),
    cargando && notificaciones.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-gray-500 animate-spin" }) }),
    confirmarEliminar && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#1a1a2e] border border-white/10 rounded-2xl w-full max-w-md", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 px-6 py-4 border-b border-white/10", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-5 h-5 text-red-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Eliminar notificaciones" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-gray-300", children: [
          "¿Eliminar permanentemente ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-bold text-white", children: seleccionados.size }),
          " notificaciones? Esta acción no se puede deshacer."
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3 justify-end", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setConfirmarEliminar(false),
              disabled: eliminando,
              className: "px-4 py-2 text-sm font-medium rounded-lg text-gray-400 border border-white/10\n                    hover:bg-white/5 transition-colors disabled:opacity-50",
              children: "Cancelar"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: manejarEliminarBatch,
              disabled: eliminando,
              className: "flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg\n                    bg-red-500 text-white hover:bg-red-400 disabled:opacity-50 transition-colors",
              children: [
                eliminando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" }),
                eliminando ? "Eliminando..." : "Eliminar"
              ]
            }
          )
        ] })
      ] })
    ] }) })
  ] });
}
const FORMATO_FECHA = { day: "2-digit", month: "2-digit", year: "numeric" };
function formatearFecha(fecha) {
  if (!fecha) return "—";
  return new Date(fecha).toLocaleDateString("es-ES", FORMATO_FECHA);
}
function formatearCountdown(dias) {
  if (dias == null) return "";
  if (dias <= 0) return " (vencida)";
  return ` (${dias} dias restantes)`;
}
function colorCountdown(dias) {
  if (dias == null) return "";
  if (dias <= 3) return "text-red-400";
  if (dias <= 7) return "text-amber-400";
  return "text-green-400";
}
const BADGE_ESTADO = {
  pendiente: { texto: "Pendiente", clase: "bg-yellow-500/20 text-yellow-300" },
  leida: { texto: "Leida", clase: "bg-blue-500/20 text-blue-300" },
  gestionada: { texto: "Gestionada", clase: "bg-green-500/20 text-green-300" },
  descartada: { texto: "Descartada", clase: "bg-gray-500/20 text-gray-400" }
};
const ICONO_ACCION = {
  cambio_estado: RefreshCw,
  cambio_asignacion: UserCheck,
  analisis_ia: Brain,
  cambio_notas: FilePen,
  envio_email: Mail,
  cambio_urgencia: TriangleAlert,
  cambio_categoria: Tag,
  asignada_gestion: FolderOpen
};
const ESTADOS_NOTIFICACION = ["pendiente", "leida", "gestionada", "descartada"];
function CampoInfo({
  etiqueta,
  valor,
  extra,
  extraClase
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400 uppercase", children: etiqueta }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-white", children: [
      valor,
      extra && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs ml-1 ${extraClase ?? ""}`, children: extra })
    ] })
  ] });
}
function ItemHistorial({ registro }) {
  const Icono = ICONO_ACCION[registro.accion] ?? RefreshCw;
  const descripcionCambio = registro.valorAnterior || registro.valorNuevo ? `${registro.accion}: ${registro.valorAnterior ?? "—"} → ${registro.valorNuevo ?? "—"}` : registro.accion;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3 py-2", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4 h-4 text-gray-400 mt-0.5 shrink-0" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0 flex-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white", children: descripcionCambio }),
      registro.descripcion && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-gray-500 mt-0.5", children: registro.descripcion }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-gray-600 mt-0.5", children: [
        formatearFecha(registro.creadoEn),
        registro.nombreUsuario ? ` — ${registro.nombreUsuario}` : ""
      ] })
    ] })
  ] });
}
function ModalDetalleNotificacionDesktop({
  notificacion,
  onCerrar,
  onActualizar,
  onCrearTarea,
  onAgregarCalendario,
  onAsignarGestion,
  onDescargarPdf,
  onAbrirPdf,
  rutaPdfLocal
}) {
  const [historial, setHistorial] = reactExports.useState([]);
  const [cargandoHistorial, setCargandoHistorial] = reactExports.useState(true);
  const [analisisIA, setAnalisisIA] = reactExports.useState(null);
  const [cargandoIA, setCargandoIA] = reactExports.useState(false);
  const [respuestaIA, setRespuestaIA] = reactExports.useState(null);
  const [cargandoRespuesta, setCargandoRespuesta] = reactExports.useState(false);
  const [estadoSelect, setEstadoSelect] = reactExports.useState(notificacion.estado);
  const [actualizando, setActualizando] = reactExports.useState(false);
  const [descargando, setDescargando] = reactExports.useState(false);
  const [resultadoDescarga, setResultadoDescarga] = reactExports.useState(null);
  const [syncPlazos, setSyncPlazos] = reactExports.useState("idle");
  reactExports.useEffect(() => {
    obtenerHistorialApi(notificacion.id).then((r) => {
      setHistorial(r.registros);
      setCargandoHistorial(false);
    }).catch(() => setCargandoHistorial(false));
    listarHistorialAegisApi({ notificacionId: notificacion.id, limite: 1 }).then((r) => {
      if (r.analisis.length > 0) setAnalisisIA(r.analisis[0]);
    }).catch(() => {
    });
  }, [notificacion.id]);
  reactExports.useEffect(() => {
    const manejarKeydown = (e) => {
      if (e.key === "Escape") onCerrar();
    };
    document.addEventListener("keydown", manejarKeydown);
    return () => document.removeEventListener("keydown", manejarKeydown);
  }, [onCerrar]);
  const marcarLeida = reactExports.useCallback(async () => {
    setActualizando(true);
    try {
      await actualizarNotificacionApi(notificacion.id, { estado: "leida" });
      onActualizar();
    } catch {
    } finally {
      setActualizando(false);
    }
  }, [notificacion.id, onActualizar]);
  const cambiarEstado = reactExports.useCallback(
    async (nuevoEstado) => {
      setEstadoSelect(nuevoEstado);
      setActualizando(true);
      try {
        await actualizarNotificacionApi(notificacion.id, {
          estado: nuevoEstado
        });
        onActualizar();
      } catch {
        setEstadoSelect(notificacion.estado);
      } finally {
        setActualizando(false);
      }
    },
    [notificacion.id, notificacion.estado, onActualizar]
  );
  const analizarIA = reactExports.useCallback(async () => {
    setCargandoIA(true);
    try {
      let contenidoPdf;
      const api = window.electronAPI;
      if (api?.ocr?.extraerTexto) {
        let ruta = rutaPdfLocal;
        if (!ruta && notificacion.idExterno && notificacion.certificadoSerial && api?.dehu?.verificarPdfDescargado) {
          try {
            const res = await api.dehu.verificarPdfDescargado(notificacion.idExterno, notificacion.certificadoSerial);
            if (res?.descargado && res.rutaLocal) ruta = res.rutaLocal;
          } catch {
          }
        }
        if (ruta) {
          try {
            const texto = await api.ocr.extraerTexto(ruta);
            if (texto && texto.length > 50) contenidoPdf = texto;
          } catch {
          }
        }
      }
      const resp = await apiClient.post("/aegis/analizar", {
        notificacionId: notificacion.id,
        contenidoPdf
      });
      setAnalisisIA(resp.datos ?? null);
    } catch {
      setAnalisisIA(null);
    } finally {
      setCargandoIA(false);
    }
  }, [notificacion.id, rutaPdfLocal, notificacion.idExterno, notificacion.certificadoSerial]);
  const generarRespuesta = reactExports.useCallback(async () => {
    setCargandoRespuesta(true);
    try {
      const resp = await apiClient.post("/aegis/generar-respuesta", {
        notificacionId: notificacion.id,
        tipoRespuesta: "respuesta_generica"
      });
      setRespuestaIA(resp.datos ?? null);
    } catch {
      setRespuestaIA(null);
    } finally {
      setCargandoRespuesta(false);
    }
  }, [notificacion.id]);
  const badge = BADGE_ESTADO[notificacion.estado] ?? BADGE_ESTADO.pendiente;
  const asunto = notificacion.contenido?.substring(0, 100) || "Sin asunto";
  const estiloBoton = "bg-[#1a1a2e] border border-white/10 hover:bg-white/10 rounded-lg px-3 py-2 text-sm flex items-center gap-2 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors";
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60",
      onClick: (e) => {
        if (e.target === e.currentTarget) onCerrar();
      },
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#0f0f23] border border-white/10 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3 p-5 border-b border-white/10", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            SemaforoUrgencia,
            {
              diasRestantes: notificacion.diasRestantesAcceso,
              vencida: notificacion.vencida
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white truncate", children: asunto }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mt-1 flex-wrap", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs px-2 py-0.5 rounded-full ${badge.clase}`, children: badge.texto }),
              notificacion.urgenciaTemporalAcceso && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs px-2 py-0.5 rounded-full bg-white/5 text-gray-300", children: [
                "Urgencia: ",
                notificacion.urgenciaTemporalAcceso
              ] })
            ] }),
            (notificacion.administracion || notificacion.tipo) && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-gray-400 mt-1", children: [
              notificacion.administracion,
              notificacion.tipo ? ` — ${notificacion.tipo}` : ""
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-gray-400 hover:text-white transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4 p-5 border-b border-white/10", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            CampoInfo,
            {
              etiqueta: "Titular",
              valor: notificacion.certificadoNombre ?? "Sin titular"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(CampoInfo, { etiqueta: "Fecha publicacion", valor: formatearFecha(notificacion.fechaPublicacion) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            CampoInfo,
            {
              etiqueta: "Fecha limite acceso",
              valor: formatearFecha(notificacion.fechaLimiteAcceso),
              extra: formatearCountdown(notificacion.diasRestantesAcceso),
              extraClase: colorCountdown(notificacion.diasRestantesAcceso)
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            CampoInfo,
            {
              etiqueta: "Fecha lectura",
              valor: notificacion.fechaLectura ? formatearFecha(notificacion.fechaLectura) : "No leida"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            CampoInfo,
            {
              etiqueta: "Fecha limite respuesta",
              valor: formatearFecha(notificacion.fechaLimiteRespuesta),
              extra: formatearCountdown(notificacion.diasRestantesRespuesta),
              extraClase: colorCountdown(notificacion.diasRestantesRespuesta)
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(CampoInfo, { etiqueta: "Origen", valor: notificacion.origen ?? "Manual" })
        ] }),
        notificacion.contenido && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-5 border-b border-white/10", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400 uppercase", children: "Contenido" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-200 mt-1 whitespace-pre-wrap", children: notificacion.contenido })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-5 border-b border-white/10", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400 uppercase mb-3 block", children: "Acciones" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 sm:grid-cols-3 gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                className: estiloBoton,
                disabled: notificacion.estado === "leida" || actualizando,
                onClick: marcarLeida,
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-4 h-4" }),
                  " Marcar leida"
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-4 h-4 text-gray-400 shrink-0" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "select",
                {
                  value: estadoSelect,
                  onChange: (e) => cambiarEstado(e.target.value),
                  disabled: actualizando,
                  className: "bg-[#1a1a2e] border border-white/10 rounded-lg px-2 py-2 text-sm text-white w-full focus:outline-none focus:ring-1 focus:ring-white/20 disabled:opacity-40",
                  children: ESTADOS_NOTIFICACION.map((est) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: est, children: est.charAt(0).toUpperCase() + est.slice(1) }, est))
                }
              )
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { className: estiloBoton, onClick: () => onCrearTarea(notificacion), children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(ListTodo, { className: "w-4 h-4" }),
              " Crear tarea"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { className: estiloBoton, onClick: () => onAgregarCalendario(notificacion), children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarPlus, { className: "w-4 h-4" }),
              " Calendario"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                className: `${estiloBoton} ${notificacion.sincronizadoCalendario ? "text-emerald-400" : ""}`,
                disabled: syncPlazos === "sincronizando",
                onClick: async () => {
                  setSyncPlazos("sincronizando");
                  try {
                    const { syncPlazosApi } = await __vitePreload(async () => {
                      const { syncPlazosApi: syncPlazosApi2 } = await import("./integracionesServicio-C-79KoQl.js");
                      return { syncPlazosApi: syncPlazosApi2 };
                    }, true ? __vite__mapDeps([0,1,2]) : void 0, import.meta.url);
                    await syncPlazosApi(notificacion.id);
                    setSyncPlazos("exito");
                  } catch {
                    setSyncPlazos("error");
                  }
                },
                children: syncPlazos === "sincronizando" ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
                  " Sincronizando..."
                ] }) : syncPlazos === "exito" || notificacion.sincronizadoCalendario ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarCheck, { className: "w-4 h-4 text-emerald-400" }),
                  " Plazos sincronizados"
                ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarCheck, { className: "w-4 h-4" }),
                  " Sync plazos"
                ] })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { className: estiloBoton, onClick: () => onAsignarGestion(notificacion), children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(FolderOpen, { className: "w-4 h-4" }),
              " Asignar gestion"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { className: estiloBoton, disabled: cargandoIA, onClick: analizarIA, children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-4 h-4" }),
              " ",
              cargandoIA ? "Analizando..." : analisisIA ? "Re-analizar IA" : "Analizar IA"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { className: estiloBoton, disabled: cargandoRespuesta, onClick: generarRespuesta, children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4" }),
              " ",
              cargandoRespuesta ? "Generando..." : "Generar respuesta"
            ] }),
            rutaPdfLocal && onAbrirPdf && /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                className: estiloBoton,
                onClick: () => onAbrirPdf(rutaPdfLocal),
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(FileCheck, { className: "w-4 h-4 text-green-400" }),
                  " Abrir PDF"
                ]
              }
            ),
            onDescargarPdf && /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                className: estiloBoton,
                disabled: descargando,
                onClick: async () => {
                  setDescargando(true);
                  setResultadoDescarga(null);
                  try {
                    const resultado = await onDescargarPdf(notificacion);
                    if (resultado) {
                      setResultadoDescarga({ exito: resultado.exito, error: resultado.error });
                    }
                  } catch {
                    setResultadoDescarga({ exito: false, error: "Error inesperado" });
                  } finally {
                    setDescargando(false);
                  }
                },
                children: [
                  descargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-4 h-4" }),
                  descargando ? "Descargando..." : "Descargar PDF"
                ]
              }
            )
          ] }),
          resultadoDescarga && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `mt-3 p-3 border rounded-lg ${resultadoDescarga.exito ? "bg-green-500/10 border-green-500/30" : "bg-red-500/10 border-red-500/30"}`, children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm ${resultadoDescarga.exito ? "text-green-300" : "text-red-300"}`, children: resultadoDescarga.exito ? "PDF descargado correctamente" : `Error: ${resultadoDescarga.error ?? "No se pudo descargar"}` }) }),
          analisisIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 p-3 bg-white/5 border border-white/10 rounded-lg space-y-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400 uppercase", children: "Analisis IA" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `text-xs px-2 py-0.5 rounded-full ${analisisIA.prioridad === "alta" ? "bg-red-500/20 text-red-300" : analisisIA.prioridad === "media" ? "bg-amber-500/20 text-amber-300" : "bg-green-500/20 text-green-300"}`, children: [
                "Prioridad: ",
                analisisIA.prioridad
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-gray-500", children: [
                analisisIA.tokens,
                " tokens — ",
                analisisIA.modelo
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-200 whitespace-pre-wrap", children: analisisIA.resumen }),
            analisisIA.fechasClaves.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400", children: "Fechas clave:" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "text-sm text-gray-300 mt-1 space-y-0.5", children: analisisIA.fechasClaves.map((f, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber-400 shrink-0", children: f.fecha }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: f.descripcion })
              ] }, i)) })
            ] }),
            analisisIA.accionesRequeridas.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400", children: "Acciones requeridas:" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "text-sm text-gray-300 mt-1 space-y-0.5", children: analisisIA.accionesRequeridas.map((a, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue-400 shrink-0", children: a.plazo ?? "—" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: a.accion })
              ] }, i)) })
            ] }),
            Object.keys(analisisIA.datosExtraidos).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400", children: "Datos extraidos:" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 grid grid-cols-2 gap-x-4 gap-y-1", children: Object.entries(analisisIA.datosExtraidos).map(([clave, valor]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-1.5 text-sm", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-gray-500 capitalize shrink-0", children: [
                  clave.replace(/([A-Z])/g, " $1").trim(),
                  ":"
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-200 break-words", children: String(valor) })
              ] }, clave)) })
            ] })
          ] }),
          respuestaIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 p-3 bg-white/5 border border-white/10 rounded-lg space-y-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-gray-400 uppercase", children: [
                "Borrador respuesta — ",
                respuestaIA.tipoRespuesta.replace(/_/g, " ")
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-gray-500", children: [
                respuestaIA.tokens,
                " tokens"
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-300 font-medium", children: respuestaIA.asunto }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "textarea",
              {
                className: "w-full bg-transparent text-sm text-gray-200 resize-y min-h-[120px] focus:outline-none border border-white/5 rounded p-2",
                defaultValue: respuestaIA.cuerpo
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-gray-400 uppercase mb-2 block", children: "Historial" }),
          cargandoHistorial ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-500", children: "Cargando historial..." }) : historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-500", children: "Sin registros de historial." }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "divide-y divide-white/5", children: historial.map((reg) => /* @__PURE__ */ jsxRuntimeExports.jsx(ItemHistorial, { registro: reg }, reg.id)) })
        ] })
      ] })
    }
  );
}
function ModalCrearTareaDesdeNotif({ notificacion, onCerrar, onCreada }) {
  const [titulo, setTitulo] = reactExports.useState(
    `Gestionar: ${notificacion.contenido?.substring(0, 60) ?? "notificacion"}`
  );
  const [prioridad, setPrioridad] = reactExports.useState("media");
  const [descripcion, setDescripcion] = reactExports.useState(
    `Referencia: ${notificacion.administracion}
Notificacion ID: ${notificacion.id}`
  );
  const [enviando, setEnviando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  useEscapeKey(true, onCerrar);
  const manejarSubmit = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await apiClient.post("/tareas", { titulo, prioridad, descripcion });
      onCreada();
      onCerrar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear la tarea");
    } finally {
      setEnviando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: "fixed inset-0 bg-black/60 z-50 flex items-center justify-center",
      onClick: onCerrar,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#0f0f23] border border-white/10 rounded-xl p-6 w-full max-w-md shadow-2xl", onClick: (e) => e.stopPropagation(), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-white font-medium", children: "Crear tarea" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-gray-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "flex flex-col gap-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm text-gray-400 block mb-1", children: "Titulo" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "text",
                value: titulo,
                onChange: (e) => setTitulo(e.target.value),
                className: "w-full bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none",
                required: true
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm text-gray-400 block mb-1", children: "Prioridad" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "select",
              {
                value: prioridad,
                onChange: (e) => setPrioridad(e.target.value),
                className: "w-full bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "alta", children: "Alta" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "media", children: "Media" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "baja", children: "Baja" })
                ]
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm text-gray-400 block mb-1", children: "Descripcion" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "textarea",
              {
                value: descripcion,
                onChange: (e) => setDescripcion(e.target.value),
                className: "w-full bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none min-h-[80px]"
              }
            )
          ] }),
          error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red-400 text-sm", children: error }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-3", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("button", { type: "button", onClick: onCerrar, className: "text-gray-400 hover:text-white text-sm", children: "Cancelar" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                type: "submit",
                disabled: enviando,
                className: "bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50",
                children: enviando ? "Creando..." : "Crear tarea"
              }
            )
          ] })
        ] })
      ] })
    }
  );
}
function calcularFechaInicial(notificacion) {
  const fuente = notificacion.fechaLimiteAcceso ?? notificacion.fechaLimiteRespuesta;
  if (fuente) {
    const fecha = new Date(fuente);
    if (!isNaN(fecha.getTime())) {
      return fecha.toISOString().split("T")[0];
    }
  }
  const manana = /* @__PURE__ */ new Date();
  manana.setDate(manana.getDate() + 1);
  return manana.toISOString().split("T")[0];
}
function ModalAgregarCalendarioDesdeNotif({ notificacion, onCerrar, onCreado }) {
  const [titulo, setTitulo] = reactExports.useState(
    `Plazo: ${notificacion.contenido?.substring(0, 50) ?? "notificacion"}`
  );
  const [fecha, setFecha] = reactExports.useState(calcularFechaInicial(notificacion));
  const [enviando, setEnviando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  useEscapeKey(true, onCerrar);
  const manejarSubmit = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      await apiClient.post("/agenda", {
        titulo,
        fecha: new Date(fecha).toISOString(),
        tipo: "recordatorio",
        ...notificacion.certificadoId ? { certificadoId: notificacion.certificadoId } : {}
      });
      onCreado();
      onCerrar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear el recordatorio");
    } finally {
      setEnviando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: "fixed inset-0 bg-black/60 z-50 flex items-center justify-center",
      onClick: onCerrar,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#0f0f23] border border-white/10 rounded-xl p-6 w-full max-w-md shadow-2xl", onClick: (e) => e.stopPropagation(), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-white font-medium", children: "Agregar a calendario" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-gray-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "flex flex-col gap-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm text-gray-400 block mb-1", children: "Titulo" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "text",
                value: titulo,
                onChange: (e) => setTitulo(e.target.value),
                className: "w-full bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none",
                required: true
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm text-gray-400 block mb-1", children: "Fecha" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "date",
                value: fecha,
                onChange: (e) => setFecha(e.target.value),
                className: "w-full bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none",
                required: true
              }
            )
          ] }),
          error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red-400 text-sm", children: error }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-3", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("button", { type: "button", onClick: onCerrar, className: "text-gray-400 hover:text-white text-sm", children: "Cancelar" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                type: "submit",
                disabled: enviando,
                className: "bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50",
                children: enviando ? "Guardando..." : "Agregar"
              }
            )
          ] })
        ] })
      ] })
    }
  );
}
function ModalAsignarGestion({ notificacion, onCerrar, onAsignada }) {
  const [gestiones, setGestiones] = reactExports.useState([]);
  const [gestionId, setGestionId] = reactExports.useState("");
  const [cargando, setCargando] = reactExports.useState(true);
  const [enviando, setEnviando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  useEscapeKey(true, onCerrar);
  reactExports.useEffect(() => {
    const cargarGestiones = async () => {
      try {
        const respuesta = await apiClient.get("/gestiones");
        const lista = respuesta.datos ?? [];
        setGestiones(lista);
        if (lista.length > 0) setGestionId(lista[0].id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar gestiones");
      } finally {
        setCargando(false);
      }
    };
    cargarGestiones();
  }, []);
  const manejarSubmit = async (e) => {
    e.preventDefault();
    if (!gestionId) return;
    setEnviando(true);
    setError(null);
    try {
      await apiClient.post(`/gestiones/${gestionId}/notificaciones`, {
        notificacionIds: [notificacion.id]
      });
      onAsignada();
      onCerrar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al asignar la gestion");
    } finally {
      setEnviando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "div",
    {
      className: "fixed inset-0 bg-black/60 z-50 flex items-center justify-center",
      onClick: onCerrar,
      children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-[#0f0f23] border border-white/10 rounded-xl p-6 w-full max-w-md shadow-2xl", onClick: (e) => e.stopPropagation(), children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-white font-medium", children: "Asignar a gestion" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-gray-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
        ] }),
        cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400", children: "Cargando gestiones..." }) : gestiones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400", children: "No hay gestiones disponibles." }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-gray-400 hover:text-white text-sm self-end", children: "Cerrar" })
        ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "flex flex-col gap-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm text-gray-400 block mb-1", children: "Gestion" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "select",
              {
                value: gestionId,
                onChange: (e) => setGestionId(e.target.value),
                className: "w-full bg-[#1a1a2e] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none",
                required: true,
                children: gestiones.map((g) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: g.id, children: g.nombre }, g.id))
              }
            )
          ] }),
          error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-red-400 text-sm", children: error }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-3", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("button", { type: "button", onClick: onCerrar, className: "text-gray-400 hover:text-white text-sm", children: "Cancelar" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                type: "submit",
                disabled: enviando,
                className: "bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50",
                children: enviando ? "Asignando..." : "Asignar"
              }
            )
          ] })
        ] })
      ] })
    }
  );
}
const ICONOS_TIPO = {
  certificado_caduca: Shield,
  scraping_completado: Activity,
  scraping_error: Activity,
  workflow_completado: Workflow,
  workflow_error: Workflow,
  sync_completada: Cloud,
  descarga_completada: FileDown,
  tarea_scheduler: Clock
};
const COLORES_PRIORIDAD = {
  alta: "border-l-red-500 bg-red-500/5",
  media: "border-l-amber-500 bg-amber-500/5",
  baja: "border-l-emerald-500 bg-emerald-500/5"
};
function PaginaNotificacionesDesktop() {
  const [notificaciones, setNotificaciones] = reactExports.useState([]);
  const [config, setConfig] = reactExports.useState(null);
  const [estado, setEstado] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [tabActiva, setTabActiva] = reactExports.useState("bandeja");
  const [chequeando, setChequeando] = reactExports.useState(false);
  const [notifSeleccionada, setNotifSeleccionada] = reactExports.useState(null);
  const [notifParaTarea, setNotifParaTarea] = reactExports.useState(null);
  const [notifParaCalendario, setNotifParaCalendario] = reactExports.useState(null);
  const [notifParaGestion, setNotifParaGestion] = reactExports.useState(null);
  const [refetchBandeja, setRefetchBandeja] = reactExports.useState(0);
  const [ocrEstado, setOcrEstado] = reactExports.useState(null);
  const [extrayendoOcr, setExtrayendoOcr] = reactExports.useState(null);
  const [batchProgreso, setBatchProgreso] = reactExports.useState(null);
  const [rutaPdfModal, setRutaPdfModal] = reactExports.useState(void 0);
  const api = window.electronAPI;
  const cargar = reactExports.useCallback(async () => {
    if (!api?.tray) return;
    try {
      setCargando(true);
      setError(null);
      const [ns, cfg, est, ocrEst] = await Promise.all([
        api.tray.listarNotificaciones(100),
        api.tray.obtenerConfig(),
        api.tray.obtenerEstado(),
        api.ocr?.estado() ?? Promise.resolve(null)
      ]);
      setNotificaciones(ns);
      setConfig(cfg);
      setEstado(est);
      if (ocrEst) setOcrEstado(ocrEst);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando notificaciones");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  reactExports.useEffect(() => {
    if (!api?.dehu?.onProgresoBatch) return;
    api.dehu.onProgresoBatch((progreso) => {
      setBatchProgreso({ actual: progreso.actual, total: progreso.total });
      if (progreso.actual >= progreso.total) {
        setTimeout(() => {
          setBatchProgreso(null);
          setRefetchBandeja((p) => p + 1);
        }, 1e3);
      }
    });
  }, [api]);
  reactExports.useEffect(() => {
    if (!notifSeleccionada?.idExterno || !notifSeleccionada?.certificadoSerial) {
      setRutaPdfModal(void 0);
      return;
    }
    const verificar = async () => {
      try {
        const res = await api?.dehu?.verificarPdfDescargado(
          notifSeleccionada.idExterno,
          notifSeleccionada.certificadoSerial
        );
        setRutaPdfModal(res?.descargado ? res.rutaLocal : void 0);
      } catch {
        setRutaPdfModal(void 0);
      }
    };
    verificar();
  }, [notifSeleccionada, api]);
  const abrirPdfLocal = async (rutaLocal) => {
    if (!api?.dehu?.abrirPdf) return;
    await api.dehu.abrirPdf(rutaLocal);
  };
  const iniciarBatchDownload = async (notifs) => {
    if (!api?.dehu?.descargarPdfBatch) return;
    const porSerial = /* @__PURE__ */ new Map();
    for (const n of notifs) {
      const serial = n.certificadoSerial ?? "desconocido";
      const grupo = porSerial.get(serial) ?? [];
      grupo.push(n);
      porSerial.set(serial, grupo);
    }
    const totalGlobal = notifs.length;
    let procesados = 0;
    setBatchProgreso({ actual: 0, total: totalGlobal });
    try {
      for (const [serial, grupo] of porSerial) {
        const config2 = { certificadoSerial: serial };
        const notifsDehu = grupo.map((n) => ({
          idDehu: n.idExterno ?? n.id,
          tipo: "Notificacion",
          titulo: n.contenido ?? "",
          titular: n.certificadoNombre ?? "",
          ambito: n.administracion ?? "",
          organismo: n.administracion ?? "",
          fechaDisposicion: n.fechaDeteccion,
          fechaCaducidad: null,
          estado: n.estado === "pendiente" ? "Pendiente de abrir" : "Aceptada",
          rutaPdfLocal: null
        }));
        await api.dehu.descargarPdfBatch(config2, notifsDehu);
        procesados += grupo.length;
        setBatchProgreso({ actual: procesados, total: totalGlobal });
      }
    } catch {
    }
    setBatchProgreso(null);
    setRefetchBandeja((p) => p + 1);
  };
  const marcarLeida = async (id) => {
    if (!api?.tray) return;
    await api.tray.marcarLeida(id);
    await cargar();
  };
  const marcarTodasLeidas = async () => {
    if (!api?.tray) return;
    await api.tray.marcarTodasLeidas();
    await cargar();
  };
  const ejecutarChequeo = async () => {
    if (!api?.tray) return;
    try {
      setChequeando(true);
      const resultado = await api.tray.ejecutarChequeo();
      if (resultado.nuevas > 0) {
        await cargar();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error ejecutando chequeo");
    } finally {
      setChequeando(false);
    }
  };
  const extraerTextoOcr = async (rutaPdf, notifId) => {
    if (!api?.ocr) return;
    try {
      setExtrayendoOcr(notifId);
      const texto = await api.ocr.extraerTexto(rutaPdf);
      if (texto) {
        const ocrEst = await api.ocr.estado();
        setOcrEstado(ocrEst);
      }
      return texto;
    } catch {
    } finally {
      setExtrayendoOcr(null);
    }
  };
  const analizarNotificacionIA = reactExports.useCallback(async (notif) => {
    let contenidoPdf;
    if (api?.ocr?.extraerTexto) {
      let ruta;
      if (notif.idExterno && notif.certificadoSerial && api?.dehu?.verificarPdfDescargado) {
        try {
          const res = await api.dehu.verificarPdfDescargado(notif.idExterno, notif.certificadoSerial);
          if (res?.descargado && res.rutaLocal) ruta = res.rutaLocal;
        } catch {
        }
      }
      if (ruta) {
        try {
          const texto = await api.ocr.extraerTexto(ruta);
          if (texto && texto.length > 50) contenidoPdf = texto;
        } catch {
        }
      }
    }
    await apiClient.post("/aegis/analizar", { notificacionId: notif.id, contenidoPdf });
  }, [api]);
  const guardarConfig = async (campo, valor) => {
    if (!api?.tray || !config) return;
    const nuevaConfig = { ...config, [campo]: valor };
    setConfig(nuevaConfig);
    await api.tray.guardarConfig(nuevaConfig);
  };
  const noLeidas = notificaciones.filter((n) => !n.leida).length;
  if (!api?.tray) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Notificaciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Notificaciones de certificados, scraping, workflows y sincronizacion" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        estado && estado.pendientes > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400", children: [
          estado.pendientes,
          " sin leer"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: ejecutarChequeo,
            disabled: chequeando,
            className: "flex items-center gap-2 px-3 py-2 text-sm text-superficie-400 hover:text-white border border-white/[0.06] rounded-lg hover:bg-white/[0.05] transition-colors disabled:opacity-50",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: `w-4 h-4 ${chequeando ? "animate-spin" : ""}` }),
              "Chequear ahora"
            ]
          }
        ),
        noLeidas > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: marcarTodasLeidas,
            className: "flex items-center gap-2 px-3 py-2 text-sm font-medium bg-acento-500/10 text-acento-400 border border-acento-500/20 rounded-lg hover:bg-acento-500/20 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(CheckCheck, { className: "w-4 h-4" }),
              "Marcar todas"
            ]
          }
        )
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5 mb-4", children: [
      { id: "bandeja", etiqueta: "Bandeja", icono: Inbox },
      { id: "alertas", etiqueta: `Alertas (${notificaciones.length})`, icono: BellRing },
      { id: "ocr", etiqueta: "OCR", icono: ScanText },
      { id: "config", etiqueta: "Configuracion", icono: Settings }
    ].map(({ id, etiqueta, icono: Icono }) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => setTabActiva(id),
        className: `flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${tabActiva === id ? "bg-acento-500/10 text-acento-400 border border-acento-500/20" : "text-superficie-400 hover:bg-white/[0.05] border border-transparent"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-3.5 h-3.5" }),
          etiqueta
        ]
      },
      id
    )) }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-500 animate-spin" }) }),
    tabActiva === "bandeja" && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        TabBandejaPortales,
        {
          onSeleccionarNotificacion: setNotifSeleccionada,
          onAnalizarIA: analizarNotificacionIA,
          onDescargarPdf: api?.notificaciones?.descargarPdf ? async (n) => {
            try {
              return await api.notificaciones.descargarPdf(
                n.idExterno ?? n.id,
                n.idExterno ? "DEHU" : n.origen ?? "DEHU",
                void 0,
                n.estado,
                n.certificadoNombre ?? void 0
              );
            } catch {
              return { exito: false, error: "Error de comunicacion con el proceso principal" };
            }
          } : void 0,
          onAbrirPdf: api?.dehu ? abrirPdfLocal : void 0,
          onDescargarBatch: api?.dehu ? iniciarBatchDownload : void 0
        },
        refetchBandeja
      ),
      batchProgreso && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 px-4 py-3 bg-blue-500/10 border border-blue-500/20 rounded-lg", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-blue-400 animate-spin shrink-0" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-blue-300", children: [
            "Descargando PDFs: ",
            batchProgreso.actual,
            " / ",
            batchProgreso.total
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1 h-1.5 bg-blue-500/20 rounded-full overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: "h-full bg-blue-500 rounded-full transition-all duration-300",
              style: { width: `${batchProgreso.actual / batchProgreso.total * 100}%` }
            }
          ) })
        ] })
      ] }),
      notifSeleccionada && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ModalDetalleNotificacionDesktop,
        {
          notificacion: notifSeleccionada,
          onCerrar: () => setNotifSeleccionada(null),
          onActualizar: () => setRefetchBandeja((p) => p + 1),
          onCrearTarea: (n) => setNotifParaTarea(n),
          onAgregarCalendario: (n) => setNotifParaCalendario(n),
          onAsignarGestion: (n) => setNotifParaGestion(n),
          onDescargarPdf: api?.notificaciones?.descargarPdf ? async (n) => {
            try {
              return await api.notificaciones.descargarPdf(
                n.idExterno ?? n.id,
                n.idExterno ? "DEHU" : n.origen ?? "DEHU",
                void 0,
                n.estado,
                n.certificadoNombre ?? void 0
              );
            } catch {
              return { exito: false, error: "Error de comunicacion con el proceso principal" };
            }
          } : void 0,
          onAbrirPdf: api?.dehu ? abrirPdfLocal : void 0,
          rutaPdfLocal: rutaPdfModal
        }
      ),
      notifParaTarea && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ModalCrearTareaDesdeNotif,
        {
          notificacion: notifParaTarea,
          onCerrar: () => setNotifParaTarea(null),
          onCreada: () => {
            setNotifParaTarea(null);
            setRefetchBandeja((p) => p + 1);
          }
        }
      ),
      notifParaCalendario && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ModalAgregarCalendarioDesdeNotif,
        {
          notificacion: notifParaCalendario,
          onCerrar: () => setNotifParaCalendario(null),
          onCreado: () => {
            setNotifParaCalendario(null);
            setRefetchBandeja((p) => p + 1);
          }
        }
      ),
      notifParaGestion && /* @__PURE__ */ jsxRuntimeExports.jsx(
        ModalAsignarGestion,
        {
          notificacion: notifParaGestion,
          onCerrar: () => setNotifParaGestion(null),
          onAsignada: () => {
            setNotifParaGestion(null);
            setRefetchBandeja((p) => p + 1);
          }
        }
      )
    ] }),
    !cargando && tabActiva === "alertas" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: notificaciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 flex items-center justify-center mx-auto mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(BellRing, { className: "w-7 h-7 text-superficie-500" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "No hay alertas" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Las alertas apareceran cuando se detecten eventos" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1.5", children: notificaciones.map((notif) => {
      const Icono = ICONOS_TIPO[notif.tipo] ?? BellRing;
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: `cristal rounded-xl border border-white/[0.06] border-l-2 px-4 py-3 transition-colors ${COLORES_PRIORIDAD[notif.prioridad] ?? ""} ${notif.leida ? "opacity-60" : ""}`,
          children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4 h-4 text-superficie-400 shrink-0" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm ${notif.leida ? "text-superficie-400" : "font-medium text-white"}`, children: notif.titulo }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: notif.mensaje }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-superficie-600 mt-0.5", children: new Date(notif.fechaCreacion).toLocaleString("es-ES") })
            ] }),
            !notif.leida && /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => marcarLeida(notif.id),
                className: "p-1.5 rounded-lg text-superficie-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors",
                title: "Marcar como leida",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4" })
              }
            )
          ] })
        },
        notif.id
      );
    }) }) }),
    !cargando && tabActiva === "ocr" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl border border-white/[0.06] p-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(ScanText, { className: "w-4 h-4 text-superficie-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Extraccion de texto (OCR)" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mb-4", children: "Extrae texto de PDFs de notificaciones para alimentar el analisis AEGIS IA. Usa texto nativo del PDF cuando existe, y OCR (tesseract.js) como fallback para documentos escaneados." }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-2 h-2 rounded-full ${ocrEstado?.activo ? "bg-emerald-400" : "bg-superficie-600"}` }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-400", children: [
              "Worker OCR: ",
              ocrEstado?.activo ? "Activo" : "Inactivo (se activa al primer uso)"
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
            "Idioma: ",
            ocrEstado?.idioma ?? "spa"
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl border border-white/[0.06] p-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4 text-superficie-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Extraer texto de PDF" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mb-4", children: "La extraccion de texto se ejecuta automaticamente al sincronizar notificaciones con el servidor. Si una notificacion tiene un PDF descargado, el texto se extrae y se envia como contenido para que AEGIS IA pueda analizar el documento completo." }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 rounded-lg bg-superficie-800/50 border border-white/[0.04]", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-medium text-acento-400 mb-1", children: "Capa 1: Texto nativo" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-superficie-500", children: "pdf-parse extrae texto embebido (~100ms). Funciona con PDFs digitales." })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 rounded-lg bg-superficie-800/50 border border-white/[0.04]", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-medium text-amber-400 mb-1", children: "Capa 2: OCR (fallback)" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-superficie-500", children: "tesseract.js reconoce texto en imagenes (~5-15s). Para PDFs escaneados." })
          ] })
        ] })
      ] }),
      api?.ocr && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl border border-white/[0.06] p-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(ScanText, { className: "w-4 h-4 text-superficie-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Test de extraccion" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mb-3", children: "Selecciona un PDF local para probar la extraccion de texto." }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: async () => {
              const ruta = window.prompt("Ruta del PDF a procesar:");
              if (!ruta) return;
              await extraerTextoOcr(ruta, "test");
            },
            disabled: extrayendoOcr !== null,
            className: "flex items-center gap-2 px-3 py-2 text-sm font-medium bg-acento-500/10 text-acento-400 border border-acento-500/20 rounded-lg hover:bg-acento-500/20 transition-colors disabled:opacity-50",
            children: [
              extrayendoOcr ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4" }),
              extrayendoOcr ? "Extrayendo..." : "Probar OCR"
            ]
          }
        )
      ] })
    ] }),
    !cargando && tabActiva === "config" && config && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl border border-white/[0.06] p-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Settings, { className: "w-4 h-4 text-superficie-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Preferencias de notificaciones" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        [
          { campo: "nativasActivas", label: "Notificaciones nativas Windows", desc: "Mostrar popups del sistema operativo" },
          { campo: "notificarScraping", label: "Scraping", desc: "Alertar al completar o fallar scraping" },
          { campo: "notificarWorkflows", label: "Workflows", desc: "Alertar al completar o fallar workflows" },
          { campo: "notificarSync", label: "Sincronizacion cloud", desc: "Alertar al completar sync con servidor" },
          { campo: "sonido", label: "Sonido", desc: "Reproducir sonido con las notificaciones" }
        ].map(({ campo, label, desc }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white", children: label }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: desc })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => guardarConfig(campo, !config[campo]),
              className: `relative w-10 h-5 rounded-full transition-colors ${config[campo] ? "bg-acento-500" : "bg-superficie-700"}`,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${config[campo] ? "translate-x-5" : "translate-x-0.5"}` })
            }
          )
        ] }, campo)),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between pt-2 border-t border-white/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white", children: "Dias de aviso caducidad" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Alertar N dias antes de que caduque un certificado" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              min: 1,
              max: 365,
              value: config.diasAvisoCaducidad,
              onChange: (e) => guardarConfig("diasAvisoCaducidad", Number(e.target.value) || 30),
              className: "w-20 px-3 py-1.5 text-sm text-center bg-superficie-800 border border-white/[0.06] rounded-lg text-white focus:outline-none focus:border-acento-500/40"
            }
          )
        ] })
      ] })
    ] })
  ] });
}
export {
  PaginaNotificacionesDesktop
};
