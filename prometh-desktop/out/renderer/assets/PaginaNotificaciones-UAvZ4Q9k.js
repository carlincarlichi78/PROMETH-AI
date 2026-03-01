import { j as jsxRuntimeExports, F as FolderOpen, p as Brain, q as FileText, s as ArrowRight, r as reactExports, E as Eye, X, t as Sparkles, v as Check, D as Download, f as CircleCheckBig, w as ClipboardList, x as ShieldAlert, T as TriangleAlert, y as Timer, z as useAuthStore, H as obtenerPerfilApi, B as Bell, m as Search } from "./index-DMbE3NR1.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { o as obtenerHistorialApi, e as enviarNotificacionApi, l as listarNotificacionesApi, a as obtenerDashboardPlazosApi, d as descartarAutomaticasApi, b as actualizarNotificacionApi, c as eliminarNotificacionesBatchApi } from "./notificacionesServicio-B3Srptx0.js";
import { l as listarHistorialAegisApi, o as obtenerTiposRespuestaApi, s as sugerirTiposRespuestaApi, g as generarRespuestaApi, a as analizarNotificacionApi } from "./aegisServicio-6JqSkwLW.js";
import { obtenerEstadoIntegracionesApi, syncPlazosApi } from "./integracionesServicio-C-79KoQl.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { T as Tag } from "./tag-wvcc-Qrp.js";
import { M as Mail } from "./mail-BDEpMyrm.js";
import { U as User } from "./user-Cs3upA-3.js";
import { C as CalendarCheck, S as SelectorCertificados } from "./SelectorCertificados-Dv92DoP7.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { S as Send } from "./send-mu2rTZak.js";
import { C as Copy } from "./copy-BxtWXfxP.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { C as Calendar } from "./calendar-KREuhz-X.js";
import { T as TrendingUp } from "./trending-up-zIPd8Al1.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { F as Filter } from "./filter-CPgLVKV9.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import "./certificadosServicio-DtEVLLjT.js";
import "./award-CLV5ctGj.js";
const ICONOS_ACCION = {
  cambio_estado: ArrowRight,
  cambio_asignacion: User,
  cambio_notas: FileText,
  envio_email: Mail,
  analisis_ia: Brain,
  cambio_urgencia: Tag,
  cambio_categoria: Tag,
  asignada_gestion: FolderOpen
};
function fechaRelativa(fechaStr) {
  const ahora = /* @__PURE__ */ new Date();
  const fecha = new Date(fechaStr);
  const diffMs = ahora.getTime() - fecha.getTime();
  const diffMin = Math.floor(diffMs / 6e4);
  const diffHoras = Math.floor(diffMin / 60);
  const diffDias = Math.floor(diffHoras / 24);
  if (diffMin < 1) return "ahora mismo";
  if (diffMin < 60) return `hace ${diffMin} min`;
  if (diffHoras < 24) return `hace ${diffHoras}h`;
  if (diffDias === 1) return "hace 1 día";
  if (diffDias < 30) return `hace ${diffDias} días`;
  return fecha.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}
function EsqueletoTimeline() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-4 animate-pulse", children: [1, 2, 3].map((i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-7 h-7 rounded-full bg-superficie-700 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-px flex-1 bg-superficie-700/40 mt-1" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "pb-4 flex-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-3.5 bg-superficie-700 rounded w-3/4 mb-1.5" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-3 bg-superficie-700/60 rounded w-1/3" })
    ] })
  ] }, i)) });
}
function TimelineHistorial({ registros, cargando }) {
  if (cargando) return /* @__PURE__ */ jsxRuntimeExports.jsx(EsqueletoTimeline, {});
  if (registros.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-8 h-8 text-superficie-600 mb-2" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm", children: "Sin historial registrado" })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-0", children: registros.map((registro, idx) => {
    const Icono = ICONOS_ACCION[registro.accion] ?? Clock;
    const esUltimo = idx === registros.length - 1;
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-7 h-7 rounded-full bg-superficie-700 border border-white/[0.06] flex items-center justify-center shrink-0", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-3.5 h-3.5 text-acento-400" }) }),
        !esUltimo && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-px flex-1 bg-white/[0.06] my-1" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex-1 ${esUltimo ? "pb-0" : "pb-4"}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-100 leading-snug", children: registro.descripcion }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mt-0.5", children: [
          registro.nombreUsuario && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: registro.nombreUsuario }),
          registro.nombreUsuario && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-600", children: "·" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: fechaRelativa(registro.creadoEn) })
        ] })
      ] })
    ] }, registro.id);
  }) });
}
const COLORES_ESTADO$1 = {
  pendiente: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  leida: "bg-superficie-700/50 text-superficie-400 border-white/[0.06]",
  gestionada: "bg-acento-500/10 text-acento-400 border-acento-500/20",
  descartada: "bg-red-500/10 text-red-400 border-red-500/20"
};
const ETIQUETAS_ESTADO$1 = {
  pendiente: "Pendiente",
  leida: "Leída",
  gestionada: "Gestionada",
  descartada: "Descartada"
};
const COLORES_URGENCIA = {
  critica: "bg-red-500/20 text-red-400 border-red-500/30",
  alta: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  media: "bg-green-500/20 text-green-400 border-green-500/30",
  baja: "bg-blue-500/20 text-blue-400 border-blue-500/30"
};
const ETIQUETAS_URGENCIA = {
  critica: "Crítica",
  alta: "Alta",
  media: "Media",
  baja: "Baja"
};
function ModalDetalleNotificacion({
  notificacion,
  abierto,
  onCerrar,
  onCambiarEstado,
  onEnviar,
  onAnalizar,
  onGenerarRespuesta,
  iaDisponible,
  analizandoId
}) {
  useEscapeKey(abierto, onCerrar);
  const [historial, setHistorial] = reactExports.useState([]);
  const [cargandoHistorial, setCargandoHistorial] = reactExports.useState(false);
  const [analisisIA, setAnalisisIA] = reactExports.useState(null);
  const ultimoIdCargado = reactExports.useRef(null);
  reactExports.useEffect(() => {
    if (!abierto || !notificacion) {
      ultimoIdCargado.current = null;
      return;
    }
    if (ultimoIdCargado.current === notificacion.id) return;
    ultimoIdCargado.current = notificacion.id;
    let cancelado = false;
    setCargandoHistorial(true);
    setHistorial([]);
    setAnalisisIA(null);
    obtenerHistorialApi(notificacion.id).then((resultado) => {
      if (!cancelado) setHistorial(resultado.registros);
    }).catch(() => {
      if (!cancelado) setHistorial([]);
    }).finally(() => {
      if (!cancelado) setCargandoHistorial(false);
    });
    listarHistorialAegisApi({ notificacionId: notificacion.id, limite: 1 }).then((r) => {
      if (!cancelado && r.analisis.length > 0) setAnalisisIA(r.analisis[0]);
    }).catch(() => {
    });
    return () => {
      cancelado = true;
    };
  }, [abierto, notificacion]);
  if (!abierto || !notificacion) return null;
  const analizando = analizandoId === notificacion.id;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Detalle de notificación" })
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
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Titular" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white font-medium mt-1", children: notificacion.certificadoNombre ?? "Sin titular" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Administración" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-superficie-200 mt-1", children: [
            notificacion.administracion,
            notificacion.tipo ? ` — ${notificacion.tipo}` : ""
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Fecha detección" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 mt-1", children: formatearFecha(notificacion.fechaDeteccion) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Estado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_ESTADO$1[notificacion.estado]}`, children: ETIQUETAS_ESTADO$1[notificacion.estado] }) })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-2", children: [
        notificacion.urgencia && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${COLORES_URGENCIA[notificacion.urgencia]}`, children: ETIQUETAS_URGENCIA[notificacion.urgencia] }),
        notificacion.categoria && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border bg-superficie-700/50 text-superficie-400 border-white/[0.06]", children: notificacion.categoria }),
        notificacion.sincronizadoCalendario && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border bg-emerald-500/10 text-emerald-400 border-emerald-500/20", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarCheck, { className: "w-3 h-3" }),
          " Plazos en Calendar"
        ] }),
        notificacion.prioridadIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${notificacion.prioridadIA === "alta" ? "bg-red-500/10 text-red-400 border-red-500/20" : notificacion.prioridadIA === "media" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"}`, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-3 h-3" }),
          " IA: ",
          notificacion.prioridadIA
        ] })
      ] }),
      (notificacion.fechaLimiteAcceso || notificacion.fechaLimiteRespuesta || notificacion.fechaPublicacion || notificacion.plazoRecursoIA) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-lg bg-superficie-800/60 border border-white/[0.04] p-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5 mb-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-3.5 h-3.5 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Plazos legales" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
          notificacion.fechaPublicacion && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Publicación" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 mt-0.5", children: formatearFecha(notificacion.fechaPublicacion) })
          ] }),
          notificacion.fechaLimiteAcceso && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Plazo acceso" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm mt-0.5", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: notificacion.diasRestantesAcceso != null && notificacion.diasRestantesAcceso <= 3 ? "text-red-400" : notificacion.diasRestantesAcceso != null && notificacion.diasRestantesAcceso <= 7 ? "text-amber-400" : "text-superficie-200", children: formatearFecha(notificacion.fechaLimiteAcceso) }),
              notificacion.diasRestantesAcceso != null && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs ml-1 ${notificacion.diasRestantesAcceso <= 3 ? "text-red-400" : notificacion.diasRestantesAcceso <= 7 ? "text-amber-400" : "text-emerald-400"}`, children: notificacion.diasRestantesAcceso <= 0 ? "(vencida)" : `(${notificacion.diasRestantesAcceso}d)` })
            ] })
          ] }),
          notificacion.fechaLimiteRespuesta && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Plazo respuesta" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm mt-0.5", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: notificacion.diasRestantesRespuesta != null && notificacion.diasRestantesRespuesta <= 3 ? "text-red-400" : notificacion.diasRestantesRespuesta != null && notificacion.diasRestantesRespuesta <= 7 ? "text-amber-400" : "text-superficie-200", children: formatearFecha(notificacion.fechaLimiteRespuesta) }),
              notificacion.diasRestantesRespuesta != null && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs ml-1 ${notificacion.diasRestantesRespuesta <= 3 ? "text-red-400" : notificacion.diasRestantesRespuesta <= 7 ? "text-amber-400" : "text-emerald-400"}`, children: notificacion.diasRestantesRespuesta <= 0 ? "(vencida)" : `(${notificacion.diasRestantesRespuesta}d)` })
            ] })
          ] }),
          notificacion.plazoRecursoIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Plazo recurso (IA)" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-blue-400 mt-0.5", children: notificacion.plazoRecursoIA })
          ] })
        ] })
      ] }),
      (analisisIA || notificacion.resumenIA) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-lg bg-purple-500/5 border border-purple-500/10 p-4 space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-3.5 h-3.5 text-purple-400" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-purple-400 uppercase tracking-wide", children: "Análisis IA" })
          ] }),
          analisisIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-[10px] text-superficie-600", children: [
            analisisIA.tokens,
            " tokens — ",
            analisisIA.modelo
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 leading-relaxed whitespace-pre-wrap", children: analisisIA?.resumen ?? notificacion.resumenIA }),
        analisisIA && analisisIA.fechasClaves.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Fechas clave" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "mt-1.5 space-y-1", children: analisisIA.fechasClaves.map((f, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2 text-sm", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-amber-400 shrink-0 font-medium", children: f.fecha }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-300", children: f.descripcion })
          ] }, i)) })
        ] }),
        analisisIA && analisisIA.accionesRequeridas.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Acciones requeridas" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "mt-1.5 space-y-1", children: analisisIA.accionesRequeridas.map((a, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-2 text-sm", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue-400 shrink-0", children: a.plazo ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-300", children: a.accion })
          ] }, i)) })
        ] }),
        analisisIA && Object.keys(analisisIA.datosExtraidos).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Datos extraídos" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-1.5 grid grid-cols-2 gap-x-4 gap-y-1", children: Object.entries(analisisIA.datosExtraidos).map(([clave, valor]) => valor ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-1.5 text-sm", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-superficie-500 capitalize shrink-0", children: [
              clave.replace(/([A-Z])/g, " $1").trim(),
              ":"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-200 break-words", children: String(valor) })
          ] }, clave) : null) })
        ] }),
        !analisisIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
          notificacion.procedimientoIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Procedimiento" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 mt-0.5", children: notificacion.procedimientoIA })
          ] }),
          notificacion.importeIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Importe" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 mt-0.5 font-medium", children: notificacion.importeIA })
          ] }),
          notificacion.deudorIA && notificacion.deudorIA !== notificacion.certificadoNombre && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Deudor" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 mt-0.5", children: notificacion.deudorIA })
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Contenido" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 p-4 rounded-lg bg-superficie-800/60 border border-white/[0.04]", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 leading-relaxed whitespace-pre-wrap", children: notificacion.contenido ?? "Sin contenido disponible" }) })
      ] }),
      notificacion.notas && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Notas internas" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300 mt-1 italic", children: notificacion.notas })
      ] }),
      notificacion.fechaEnvio && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-3 py-2 rounded-lg bg-acento-500/10 border border-acento-500/20", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-4 h-4 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-acento-400", children: [
          "Enviada por email a ",
          notificacion.emailDestinatario,
          " el ",
          formatearFecha(notificacion.fechaEnvio)
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-2 pt-3 border-t border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: notificacion.estado,
            onChange: (e) => onCambiarEstado(notificacion.id, e.target.value),
            className: "px-3 py-1.5 text-xs rounded-lg bg-superficie-800 border border-white/[0.06] text-superficie-200 outline-none",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "pendiente", children: "Pendiente" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "leida", children: "Leída" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "gestionada", children: "Gestionada" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "descartada", children: "Descartada" })
            ]
          }
        ),
        iaDisponible && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => onAnalizar(notificacion.id),
              disabled: analizando,
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                    bg-purple-500/10 text-purple-400 border border-purple-500/20\n                    hover:bg-purple-500/20 disabled:opacity-50 transition-all",
              children: [
                analizando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3.5 h-3.5 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-3.5 h-3.5" }),
                analizando ? "Analizando..." : "Analizar con IA"
              ]
            }
          ),
          notificacion.urgencia && onGenerarRespuesta && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => onGenerarRespuesta(notificacion),
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                      bg-purple-500/10 text-purple-400 border border-purple-500/20\n                      hover:bg-purple-500/20 transition-all",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Sparkles, { className: "w-3.5 h-3.5" }),
                "Generar respuesta"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => onEnviar(notificacion),
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                    bg-acento-500/10 text-acento-400 border border-acento-500/20\n                    hover:bg-acento-500/20 transition-all",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-3.5 h-3.5" }),
                "Enviar al cliente"
              ]
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Historial" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-3 p-4 rounded-lg bg-superficie-800/40 border border-white/[0.04]", children: /* @__PURE__ */ jsxRuntimeExports.jsx(TimelineHistorial, { registros: historial, cargando: cargandoHistorial }) })
      ] })
    ] })
  ] }) });
}
const ICONOS_TIPO = {
  alegacion: "⚖️",
  recurso_reposicion: "📋",
  recurso_alzada: "🏛️",
  solicitud_aplazamiento: "📅",
  escrito_subsanacion: "📎",
  respuesta_generica: "✉️"
};
function ModalGenerarRespuesta({
  abierto,
  onCerrar,
  notificacion,
  onPreRellenarEmail
}) {
  useEscapeKey(abierto, onCerrar);
  const [paso, setPaso] = reactExports.useState("seleccion");
  const [plantillas, setPlantillas] = reactExports.useState([]);
  const [sugeridos, setSugeridos] = reactExports.useState([]);
  const [tipoSeleccionado, setTipoSeleccionado] = reactExports.useState(null);
  const [resultado, setResultado] = reactExports.useState(null);
  const [asuntoEditado, setAsuntoEditado] = reactExports.useState("");
  const [cuerpoEditado, setCuerpoEditado] = reactExports.useState("");
  const [error, setError] = reactExports.useState(null);
  const [copiado, setCopiado] = reactExports.useState(false);
  const [cargandoPlantillas, setCargandoPlantillas] = reactExports.useState(false);
  reactExports.useEffect(() => {
    if (!abierto || !notificacion) return;
    setPaso("seleccion");
    setTipoSeleccionado(null);
    setResultado(null);
    setError(null);
    let cancelado = false;
    setCargandoPlantillas(true);
    Promise.all([
      obtenerTiposRespuestaApi(),
      sugerirTiposRespuestaApi(notificacion.id)
    ]).then(([tipos, sug]) => {
      if (cancelado) return;
      setPlantillas(tipos);
      setSugeridos(sug);
    }).catch(() => {
      if (cancelado) return;
      setPlantillas([]);
      setSugeridos([]);
    }).finally(() => {
      if (!cancelado) setCargandoPlantillas(false);
    });
    return () => {
      cancelado = true;
    };
  }, [abierto, notificacion]);
  async function handleGenerar() {
    if (!tipoSeleccionado || !notificacion) return;
    setPaso("generando");
    setError(null);
    try {
      const res = await generarRespuestaApi(notificacion.id, tipoSeleccionado);
      setResultado(res);
      setAsuntoEditado(res.asunto);
      setCuerpoEditado(res.cuerpo);
      setPaso("resultado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al generar respuesta");
      setPaso("seleccion");
    }
  }
  function handleCopiar() {
    const texto = `Asunto: ${asuntoEditado}

${cuerpoEditado}`;
    navigator.clipboard.writeText(texto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2e3);
  }
  function handleDescargar() {
    const texto = `Asunto: ${asuntoEditado}

${cuerpoEditado}`;
    const blob = new Blob([texto], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const enlace = document.createElement("a");
    enlace.href = url;
    enlace.download = `respuesta-${tipoSeleccionado ?? "borrador"}.txt`;
    enlace.click();
    URL.revokeObjectURL(url);
  }
  function handlePreRellenarEmail() {
    if (onPreRellenarEmail) {
      onPreRellenarEmail(asuntoEditado, cuerpoEditado);
    }
    onCerrar();
  }
  function handleRegenerar() {
    setPaso("seleccion");
    setResultado(null);
  }
  if (!abierto || !notificacion) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Sparkles, { className: "w-5 h-5 text-purple-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Generar respuesta con IA" })
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
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6", children: [
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: error }),
      paso === "seleccion" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-superficie-400", children: [
          "Selecciona el tipo de respuesta que deseas generar para esta notificación de",
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-white font-medium", children: notificacion.administracion })
        ] }),
        cargandoPlantillas ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid gap-3", children: plantillas.map((plantilla) => {
          const esSugerido = sugeridos.includes(plantilla.tipo);
          const seleccionado = tipoSeleccionado === plantilla.tipo;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => setTipoSeleccionado(plantilla.tipo),
              className: `relative flex items-start gap-3 p-4 rounded-xl border text-left transition-all
                          ${seleccionado ? "bg-purple-500/10 border-purple-500/30 ring-1 ring-purple-500/20" : "bg-superficie-800/40 border-white/[0.06] hover:bg-superficie-800/60 hover:border-white/10"}`,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xl mt-0.5", children: ICONOS_TIPO[plantilla.tipo] ?? "📄" }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm font-medium ${seleccionado ? "text-purple-300" : "text-white"}`, children: plantilla.nombre }),
                    esSugerido && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-1.5 py-0.5 text-[10px] font-medium rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30", children: "Sugerido" })
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-0.5", children: plantilla.descripcion })
                ] }),
                seleccionado && /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4 text-purple-400 mt-1 shrink-0" })
              ]
            },
            plantilla.tipo
          );
        }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-end pt-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: handleGenerar,
            disabled: !tipoSeleccionado,
            className: "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium\n                    bg-purple-600 text-white hover:bg-purple-500 disabled:opacity-50\n                    disabled:cursor-not-allowed transition-all",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Sparkles, { className: "w-4 h-4" }),
              "Generar borrador"
            ]
          }
        ) })
      ] }),
      paso === "generando" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-12 space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "relative", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-10 h-10 text-purple-400 animate-spin" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white font-medium", children: "Generando borrador de respuesta..." }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500 mt-1", children: [
            "La IA está redactando un",
            " ",
            plantillas.find((p) => p.tipo === tipoSeleccionado)?.nombre?.toLowerCase() ?? "escrito"
          ] })
        ] })
      ] }),
      paso === "resultado" && resultado && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 text-xs text-superficie-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-3.5 h-3.5" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
            resultado.tokens,
            " tokens utilizados"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Asunto" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: asuntoEditado,
              onChange: (e) => setAsuntoEditado(e.target.value),
              className: "mt-1 w-full px-3 py-2 rounded-lg bg-superficie-800 border border-white/[0.06]\n                    text-sm text-white outline-none focus:border-purple-500/30 transition-colors"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Cuerpo del escrito" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "textarea",
            {
              value: cuerpoEditado,
              onChange: (e) => setCuerpoEditado(e.target.value),
              rows: 14,
              className: "mt-1 w-full px-3 py-2 rounded-lg bg-superficie-800 border border-white/[0.06]\n                    text-sm text-superficie-200 outline-none focus:border-purple-500/30 transition-colors\n                    resize-y leading-relaxed font-mono"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-2 pt-2 border-t border-white/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: handleCopiar,
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                    bg-superficie-800 text-superficie-300 border border-white/[0.06]\n                    hover:bg-superficie-700 hover:text-white transition-all",
              children: [
                copiado ? /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-3.5 h-3.5 text-green-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "w-3.5 h-3.5" }),
                copiado ? "Copiado" : "Copiar"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: handleDescargar,
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                    bg-superficie-800 text-superficie-300 border border-white/[0.06]\n                    hover:bg-superficie-700 hover:text-white transition-all",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-3.5 h-3.5" }),
                "Descargar .txt"
              ]
            }
          ),
          onPreRellenarEmail && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: handlePreRellenarEmail,
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                      bg-acento-500/10 text-acento-400 border border-acento-500/20\n                      hover:bg-acento-500/20 transition-all",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-3.5 h-3.5" }),
                "Enviar por email"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: handleRegenerar,
              className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium\n                    bg-purple-500/10 text-purple-400 border border-purple-500/20\n                    hover:bg-purple-500/20 transition-all ml-auto",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-3.5 h-3.5" }),
                "Regenerar"
              ]
            }
          )
        ] })
      ] })
    ] })
  ] }) });
}
function ModalEnviarEmail({ notificacion, onCerrar, onEnviado }) {
  const [destinatario, setDestinatario] = reactExports.useState("");
  const [asunto, setAsunto] = reactExports.useState(`Notificación ${notificacion.administracion}`);
  const [mensaje, setMensaje] = reactExports.useState("");
  const [enviando, setEnviando] = reactExports.useState(false);
  const [exito, setExito] = reactExports.useState(false);
  const [errorEnvio, setErrorEnvio] = reactExports.useState(null);
  useEscapeKey(true, onCerrar);
  const manejarEnviar = async () => {
    setEnviando(true);
    setErrorEnvio(null);
    try {
      const actualizada = await enviarNotificacionApi(notificacion.id, {
        destinatario,
        asunto,
        mensaje: mensaje || void 0
      });
      setExito(true);
      setTimeout(() => onEnviado(actualizada), 1500);
    } catch (err) {
      setErrorEnvio(err instanceof Error ? err.message : "Error al enviar");
    } finally {
      setEnviando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-lg", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Enviar al cliente" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-6 space-y-4", children: exito ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center py-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-12 h-12 text-green-400 mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-white font-medium", children: "Email enviado correctamente" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-superficie-400 text-sm mt-1", children: [
        "Se envió a ",
        destinatario
      ] })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1.5", children: "Destinatario *" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "email",
            value: destinatario,
            onChange: (e) => setDestinatario(e.target.value),
            placeholder: "cliente@ejemplo.com",
            className: "w-full px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1.5", children: "Asunto *" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: asunto,
            onChange: (e) => setAsunto(e.target.value),
            className: "w-full px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1.5", children: "Mensaje (opcional)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "textarea",
          {
            value: mensaje,
            onChange: (e) => setMensaje(e.target.value),
            rows: 3,
            placeholder: "Añade un mensaje para el cliente...",
            className: "w-full px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600 resize-none"
          }
        )
      ] }),
      errorEnvio && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 text-red-400 text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4" }),
        errorEnvio
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarEnviar,
          disabled: enviando || !destinatario || !asunto,
          className: "w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-acento-500 hover:bg-acento-400 disabled:opacity-50 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
          children: [
            enviando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-4 h-4" }),
            enviando ? "Enviando..." : "Enviar email"
          ]
        }
      )
    ] }) })
  ] }) });
}
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
function ModalResultadoIA({ analisis, onCerrar }) {
  useEscapeKey(true, onCerrar);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-5 h-5 text-purple-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Resultado del análisis" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 uppercase tracking-wide", children: "Prioridad" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${COLORES_PRIORIDAD[analisis.prioridad]}`, children: ETIQUETAS_PRIORIDAD[analisis.prioridad] })
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
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: analisis.fechasClaves.map((fc, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3 px-3 py-2 rounded-lg bg-superficie-800/60 border border-white/[0.04]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-mono text-acento-400 whitespace-nowrap mt-0.5", children: fc.fecha }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-300", children: fc.descripcion })
        ] }, i)) })
      ] }),
      analisis.accionesRequeridas.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-xs text-superficie-500 uppercase tracking-wide mb-2 flex items-center gap-1.5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(ClipboardList, { className: "w-3.5 h-3.5" }),
          "Acciones requeridas"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: analisis.accionesRequeridas.map((ar, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3 px-3 py-2 rounded-lg bg-superficie-800/60 border border-white/[0.04]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-1.5 h-1.5 rounded-full bg-amber-400 mt-2 shrink-0" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-200", children: ar.accion }),
            ar.plazo && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500 ml-2", children: [
              "Plazo: ",
              ar.plazo
            ] })
          ] })
        ] }, i)) })
      ] }),
      Object.keys(analisis.datosExtraidos).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-xs text-superficie-500 uppercase tracking-wide mb-2", children: "Datos extraídos" }),
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
        ] })
      ] })
    ] })
  ] }) });
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
  "seguridad social": "Seg. Social",
  "junta de andalucia": "J. Andalucía",
  "generalitat de catalunya": "Generalitat",
  "comunidad de madrid": "C. Madrid"
};
function abreviarAdmin(nombre) {
  if (!nombre) return "";
  const lower = nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  for (const [patron, abreviatura] of Object.entries(ABREVIATURAS_ADMIN)) {
    if (lower.includes(patron)) return abreviatura;
  }
  return nombre.length > 20 ? nombre.substring(0, 18) + "…" : nombre;
}
function formatearFechaTabla(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`;
}
function formatearFechaCorta(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}
function colorDotPlazo(dias) {
  if (dias == null) return "bg-superficie-600";
  if (dias <= 0) return "bg-superficie-500";
  if (dias <= 3) return "bg-red-500";
  if (dias <= 7) return "bg-amber-500";
  return "bg-emerald-500";
}
function colorTextoPlazo(dias) {
  if (dias == null) return "text-superficie-500";
  if (dias <= 0) return "text-superficie-500 line-through";
  if (dias <= 3) return "text-red-400";
  if (dias <= 7) return "text-amber-400";
  return "text-emerald-400";
}
function colorImporte(importeStr) {
  if (!importeStr) return "text-superficie-600";
  const limpio = importeStr.replace(/[€\s]/g, "").replace(/\./g, "").replace(",", ".");
  const valor = parseFloat(limpio);
  if (isNaN(valor)) return "text-superficie-300";
  if (valor >= 5e3) return "text-red-400 font-semibold";
  if (valor >= 1e3) return "text-amber-400 font-medium";
  return "text-superficie-200";
}
function colorSemaforo(dias, vencida) {
  if (vencida || dias != null && dias <= 0) return { color: "bg-superficie-400", pulso: false };
  if (dias == null) return { color: "bg-superficie-600", pulso: false };
  if (dias <= 2) return { color: "bg-red-500", pulso: true };
  if (dias <= 5) return { color: "bg-red-500", pulso: false };
  if (dias <= 8) return { color: "bg-amber-400", pulso: false };
  return { color: "bg-emerald-500", pulso: false };
}
function DashboardPlazos({ plazos }) {
  const kpis = [
    {
      icono: ShieldAlert,
      label: "Vencidas",
      valor: plazos.vencidasHoy,
      color: "text-red-400",
      bgColor: "bg-red-500/10 border-red-500/20"
    },
    {
      icono: TriangleAlert,
      label: "Vencen esta semana",
      valor: plazos.vencenEstaSemana,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10 border-amber-500/20"
    },
    {
      icono: Timer,
      label: "Próxima semana",
      valor: plazos.vencenProximaSemana,
      color: "text-blue-400",
      bgColor: "bg-blue-500/10 border-blue-500/20"
    },
    {
      icono: TrendingUp,
      label: "Total pendientes",
      valor: plazos.totalPendientes,
      color: "text-acento-400",
      bgColor: "bg-acento-500/10 border-acento-500/20"
    }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 lg:grid-cols-4 gap-3", children: kpis.map(({ icono: Icono, label, valor, color, bgColor }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `rounded-xl border p-4 ${bgColor}`, children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-4 h-4 ${color}` }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-400", children: label })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `text-2xl font-bold ${color}`, children: valor })
    ] }, label)) }),
    plazos.totalPendientes > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal-sutil rounded-xl p-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-between mb-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-semibold text-superficie-400 uppercase tracking-wide", children: "Distribución por urgencia" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex rounded-full overflow-hidden h-3 bg-superficie-800", children: [
        plazos.porUrgencia.critica > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-red-500 transition-all", style: { width: `${plazos.porUrgencia.critica / plazos.totalPendientes * 100}%` }, title: `Crítica: ${plazos.porUrgencia.critica}` }),
        plazos.porUrgencia.alta > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-amber-500 transition-all", style: { width: `${plazos.porUrgencia.alta / plazos.totalPendientes * 100}%` }, title: `Alta: ${plazos.porUrgencia.alta}` }),
        plazos.porUrgencia.media > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-blue-500 transition-all", style: { width: `${plazos.porUrgencia.media / plazos.totalPendientes * 100}%` }, title: `Media: ${plazos.porUrgencia.media}` }),
        plazos.porUrgencia.baja > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-emerald-500 transition-all", style: { width: `${plazos.porUrgencia.baja / plazos.totalPendientes * 100}%` }, title: `Baja: ${plazos.porUrgencia.baja}` }),
        plazos.sinFechaLimite > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-superficie-600 transition-all", style: { width: `${plazos.sinFechaLimite / plazos.totalPendientes * 100}%` }, title: `Sin plazo: ${plazos.sinFechaLimite}` })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-4 mt-2 text-xs text-superficie-500", children: [
        plazos.porUrgencia.critica > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-2 h-2 rounded-full bg-red-500" }),
          plazos.porUrgencia.critica,
          " crítica"
        ] }),
        plazos.porUrgencia.alta > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-2 h-2 rounded-full bg-amber-500" }),
          plazos.porUrgencia.alta,
          " alta"
        ] }),
        plazos.porUrgencia.media > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-2 h-2 rounded-full bg-blue-500" }),
          plazos.porUrgencia.media,
          " media"
        ] }),
        plazos.porUrgencia.baja > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-2 h-2 rounded-full bg-emerald-500" }),
          plazos.porUrgencia.baja,
          " baja"
        ] }),
        plazos.sinFechaLimite > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-2 h-2 rounded-full bg-superficie-600" }),
          plazos.sinFechaLimite,
          " sin plazo"
        ] })
      ] })
    ] }),
    plazos.porAdministracion.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2", children: plazos.porAdministracion.slice(0, 6).map(({ administracion, pendientes, urgentes }) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal-sutil rounded-lg p-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-superficie-500 truncate", children: administracion }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-baseline gap-1.5 mt-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-lg font-bold text-superficie-100", children: pendientes }),
        urgentes > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-red-400 font-medium", children: [
          urgentes,
          " urg."
        ] })
      ] })
    ] }, administracion)) })
  ] });
}
function CeldaPlazosWeb({ notif }) {
  const tieneAcceso = notif.fechaLimiteAcceso != null;
  const tieneRespuesta = notif.fechaLimiteRespuesta != null;
  const plazoRecurso = notif.plazoRecursoIA && notif.plazoRecursoIA.trim() ? notif.plazoRecursoIA.trim() : null;
  const tienePlazoIA = plazoRecurso != null;
  if (tieneAcceso || tieneRespuesta || tienePlazoIA) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-0.5 text-[11px] leading-tight", children: [
      tieneAcceso && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", title: `Acceso: ${formatearFechaTabla(notif.fechaLimiteAcceso)} (${notif.diasRestantesAcceso ?? "?"} días)`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full shrink-0 ${colorDotPlazo(notif.diasRestantesAcceso)}` }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-500", children: "Acceso" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: colorTextoPlazo(notif.diasRestantesAcceso), children: formatearFechaCorta(notif.fechaLimiteAcceso) }),
        notif.diasRestantesAcceso != null && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-600", children: notif.diasRestantesAcceso <= 0 ? "(vencido)" : `(${notif.diasRestantesAcceso}d)` })
      ] }),
      tieneRespuesta && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", title: `Respuesta: ${formatearFechaTabla(notif.fechaLimiteRespuesta)} (${notif.diasRestantesRespuesta ?? "?"} días)`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full shrink-0 ${colorDotPlazo(notif.diasRestantesRespuesta)}` }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-500", children: "Resp." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: colorTextoPlazo(notif.diasRestantesRespuesta), children: formatearFechaCorta(notif.fechaLimiteRespuesta) }),
        notif.diasRestantesRespuesta != null && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-600", children: notif.diasRestantesRespuesta <= 0 ? "(vencido)" : `(${notif.diasRestantesRespuesta}d)` })
      ] }),
      tienePlazoIA && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5", title: `Recurso (IA): ${plazoRecurso}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "w-1.5 h-1.5 rounded-full shrink-0 bg-blue-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-500", children: "Recurso" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-blue-400 truncate max-w-[120px]", children: /^\d{4}-\d{2}-\d{2}/.test(plazoRecurso) ? formatearFechaCorta(plazoRecurso) : plazoRecurso })
      ] })
    ] });
  }
  const fechaRef = notif.fechaPublicacion ?? notif.fechaDeteccion;
  if (fechaRef) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-[11px] leading-tight text-superficie-500", title: "Sin plazos calculados. Analiza con IA para detectar plazos de recurso.", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
      "Pub: ",
      formatearFechaCorta(fechaRef)
    ] }) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-600", title: "Sin fecha de publicación ni plazos", children: "—" });
}
const COLORES_ESTADO = {
  pendiente: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  leida: "bg-superficie-700/50 text-superficie-400 border-white/[0.06]",
  gestionada: "bg-acento-500/10 text-acento-400 border-acento-500/20",
  descartada: "bg-red-500/10 text-red-400 border-red-500/20"
};
const ETIQUETAS_ESTADO = {
  pendiente: "Pendiente",
  leida: "Leída",
  gestionada: "Gestionada",
  descartada: "Descartada"
};
function PaginaNotificaciones() {
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [cargando, setCargando] = reactExports.useState(true);
  const [comprobando, setComprobando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  const [notificaciones, setNotificaciones] = reactExports.useState([]);
  const [total, setTotal] = reactExports.useState(0);
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(0);
  const [ultimaCarga, setUltimaCarga] = reactExports.useState(null);
  const [planActual, setPlanActual] = reactExports.useState("basico");
  const [analisisModal, setAnalisisModal] = reactExports.useState(null);
  const [analizandoId, setAnalizandoId] = reactExports.useState(null);
  const [errorAnalisis, setErrorAnalisis] = reactExports.useState(null);
  const [detalleNotif, setDetalleNotif] = reactExports.useState(null);
  const [enviarModal, setEnviarModal] = reactExports.useState(null);
  const [descartando, setDescartando] = reactExports.useState(false);
  const [filtroUrgencia, setFiltroUrgencia] = reactExports.useState(null);
  const [filtroEstado, setFiltroEstado] = reactExports.useState(null);
  const [generarRespuestaNotif, setGenerarRespuestaNotif] = reactExports.useState(null);
  const [filtroCertificados, setFiltroCertificados] = reactExports.useState([]);
  const [plazos, setPlazos] = reactExports.useState(null);
  const [tieneCalendario, setTieneCalendario] = reactExports.useState(false);
  const [syncingCalId, setSyncingCalId] = reactExports.useState(null);
  const [seleccionados, setSeleccionados] = reactExports.useState(/* @__PURE__ */ new Set());
  const [eliminando, setEliminando] = reactExports.useState(false);
  const [confirmarEliminar, setConfirmarEliminar] = reactExports.useState(false);
  const rolUsuario = useAuthStore((s) => s.usuario?.rol);
  const esAdmin = rolUsuario === "admin" || rolUsuario === "superadmin";
  useEscapeKey(confirmarEliminar, () => setConfirmarEliminar(false));
  const cargarNotificaciones = reactExports.useCallback(async (textoBusqueda, urgencia, estado, pag = 1, certIds) => {
    try {
      setError(null);
      const certificadoIds = certIds && certIds.length > 0 ? certIds.join(",") : void 0;
      const resultado = await listarNotificacionesApi({
        busqueda: textoBusqueda || void 0,
        limite: 30,
        pagina: pag,
        urgencia: urgencia ?? void 0,
        estado: estado ?? void 0,
        certificadoIds
      });
      setNotificaciones(resultado.notificaciones);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
      setPagina(pag);
      setUltimaCarga(/* @__PURE__ */ new Date());
    } catch (err) {
      const mensaje = err instanceof Error ? err.message : "Error al cargar notificaciones";
      setError(mensaje);
    }
  }, []);
  const cargarPlazos = reactExports.useCallback(async () => {
    try {
      const datos = await obtenerDashboardPlazosApi();
      setPlazos(datos);
    } catch {
    }
  }, []);
  reactExports.useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      await Promise.all([cargarNotificaciones(), cargarPlazos()]);
      setCargando(false);
    };
    cargar();
    obtenerPerfilApi().then((perfil) => setPlanActual(perfil.organizacion.plan)).catch(() => {
    });
    obtenerEstadoIntegracionesApi().then((estado) => setTieneCalendario(estado.google?.activo === true || estado.microsoft?.activo === true)).catch(() => {
    });
  }, [cargarNotificaciones, cargarPlazos]);
  const manejarComprobar = async () => {
    setComprobando(true);
    await Promise.all([
      cargarNotificaciones(busqueda, filtroUrgencia, filtroEstado, 1, filtroCertificados),
      cargarPlazos()
    ]);
    setComprobando(false);
  };
  const manejarBuscar = async () => {
    setCargando(true);
    await cargarNotificaciones(busqueda, filtroUrgencia, filtroEstado, 1, filtroCertificados);
    setCargando(false);
  };
  const manejarFiltroUrgencia = async (urgencia) => {
    setFiltroUrgencia(urgencia);
    setCargando(true);
    await cargarNotificaciones(busqueda, urgencia, filtroEstado, 1, filtroCertificados);
    setCargando(false);
  };
  const manejarFiltroEstado = async (estado) => {
    setFiltroEstado(estado);
    setCargando(true);
    await cargarNotificaciones(busqueda, filtroUrgencia, estado, 1, filtroCertificados);
    setCargando(false);
  };
  const manejarPagina = async (nuevaPagina) => {
    setCargando(true);
    await cargarNotificaciones(busqueda, filtroUrgencia, filtroEstado, nuevaPagina, filtroCertificados);
    setCargando(false);
  };
  const manejarFiltroCertificados = async (ids) => {
    setFiltroCertificados(ids);
    setCargando(true);
    await cargarNotificaciones(busqueda, filtroUrgencia, filtroEstado, 1, ids);
    setCargando(false);
  };
  const manejarAnalizar = async (notificacionId) => {
    setAnalizandoId(notificacionId);
    setErrorAnalisis(null);
    try {
      const resultado = await analizarNotificacionApi(notificacionId);
      setAnalisisModal(resultado);
    } catch (err) {
      setErrorAnalisis(err instanceof Error ? err.message : "Error al analizar");
    } finally {
      setAnalizandoId(null);
    }
  };
  const manejarSyncCalendario = async (notificacionId) => {
    setSyncingCalId(notificacionId);
    try {
      const resultado = await syncPlazosApi(notificacionId);
      if (resultado.eventosCreados > 0) {
        setNotificaciones(
          (prev) => prev.map((n) => n.id === notificacionId ? { ...n, sincronizadoCalendario: true } : n)
        );
      } else {
        setError("No se crearon eventos. Analiza la notificación con IA primero para extraer plazos.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al sincronizar con calendario");
    } finally {
      setSyncingCalId(null);
    }
  };
  const manejarCambiarEstado = async (id, estado) => {
    try {
      const actualizada = await actualizarNotificacionApi(id, { estado });
      setNotificaciones(
        (prev) => prev.map((n) => n.id === id ? actualizada : n)
      );
      if (detalleNotif?.id === id) setDetalleNotif(actualizada);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al actualizar estado");
    }
  };
  const manejarDescartar = async () => {
    setDescartando(true);
    try {
      await descartarAutomaticasApi();
      await cargarNotificaciones(busqueda, filtroUrgencia, filtroEstado, 1, filtroCertificados);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al descartar");
    } finally {
      setDescartando(false);
    }
  };
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
      await cargarNotificaciones(busqueda, filtroUrgencia, filtroEstado, 1, filtroCertificados);
      await cargarPlazos();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar notificaciones");
    } finally {
      setEliminando(false);
    }
  };
  const textoUltimaCarga = ultimaCarga ? `${ultimaCarga.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}` : "nunca";
  const iaDisponible = planActual !== "basico";
  const filtrosUrgencia = [
    { valor: null, etiqueta: "Todas" },
    { valor: "critica", etiqueta: "Crítica" },
    { valor: "alta", etiqueta: "Alta" },
    { valor: "media", etiqueta: "Media" },
    { valor: "baja", etiqueta: "Baja" }
  ];
  const filtrosEstado = [
    { valor: null, etiqueta: "Todos" },
    { valor: "pendiente", etiqueta: "Pendiente" },
    { valor: "leida", etiqueta: "Leída" },
    { valor: "gestionada", etiqueta: "Gestionada" },
    { valor: "descartada", etiqueta: "Descartada" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-5", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Notificaciones" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        esAdmin && seleccionados.size > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setConfirmarEliminar(true),
            className: "flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg\n                bg-red-500/10 text-red-400 border border-red-500/20\n                hover:bg-red-500/20 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" }),
              "Eliminar (",
              seleccionados.size,
              ")"
            ]
          }
        ),
        iaDisponible && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarDescartar,
            disabled: descartando,
            className: "flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg\n                bg-red-500/10 text-red-400 border border-red-500/20\n                hover:bg-red-500/20 disabled:opacity-50 transition-colors",
            children: [
              descartando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }),
              "Descartar antiguas"
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarComprobar,
            disabled: comprobando,
            className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n              disabled:opacity-50 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: `w-4 h-4 ${comprobando ? "animate-spin" : ""}` }),
              comprobando ? "Actualizando..." : "Actualizar"
            ]
          }
        )
      ] })
    ] }),
    plazos && /* @__PURE__ */ jsxRuntimeExports.jsx(DashboardPlazos, { plazos }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: busqueda,
              onChange: (e) => setBusqueda(e.target.value),
              onKeyDown: (e) => e.key === "Enter" && manejarBuscar(),
              placeholder: "Buscar por administración o contenido...",
              className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-3 py-2 cristal-sutil rounded-lg text-sm text-superficie-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-4 h-4 text-superficie-500" }),
          total,
          " notificaciones"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Filter, { className: "w-3.5 h-3.5 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Urgencia:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1", children: filtrosUrgencia.map(({ valor, etiqueta }) => {
            const activo = filtroUrgencia === valor;
            const colorActivo = valor ? COLORES_URGENCIA[valor] : "";
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => manejarFiltroUrgencia(valor),
                className: `px-2.5 py-1 text-xs font-medium rounded-md border transition-colors ${activo ? valor ? colorActivo : "bg-acento-500/20 text-acento-400 border-acento-500/30" : "bg-superficie-800/60 text-superficie-400 border-white/[0.06] hover:border-white/[0.12]"}`,
                children: etiqueta
              },
              String(valor)
            );
          }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Estado:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1", children: filtrosEstado.map(({ valor, etiqueta }) => {
            const activo = filtroEstado === valor;
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => manejarFiltroEstado(valor),
                className: `px-2.5 py-1 text-xs font-medium rounded-md border transition-colors ${activo ? "bg-acento-500/20 text-acento-400 border-acento-500/30" : "bg-superficie-800/60 text-superficie-400 border-white/[0.06] hover:border-white/[0.12]"}`,
                children: etiqueta
              },
              String(valor)
            );
          }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: "Titular:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            SelectorCertificados,
            {
              seleccionados: filtroCertificados,
              onChange: manejarFiltroCertificados
            }
          )
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5 text-xs text-superficie-500", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-3.5 h-3.5" }),
      "Última comprobación: ",
      textoUltimaCarga
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    errorAnalisis && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      errorAnalisis,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setErrorAnalisis(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(EstadoCargando, {}) : notificaciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(EstadoVacio, {}) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm table-fixed", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-10 px-2 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "checkbox",
            checked: notificaciones.length > 0 && seleccionados.size === notificaciones.length,
            onChange: toggleSeleccionTodos,
            className: "w-4 h-4 rounded border-2 border-superficie-400 bg-superficie-700 text-acento-500 focus:ring-acento-500/40 cursor-pointer accent-acento-500"
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-12 px-2 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-left", children: "Urg." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-left", children: "Titular / Asunto" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-20 px-2 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-left", children: "Fecha" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-52 px-2 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-left", children: "Plazos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-28 px-2 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-right", children: "Importe" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-24 px-2 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-left", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "w-28 px-2 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide text-center", children: "Acc." })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: notificaciones.map((notif) => {
        const contenidoCorto = notif.contenido ? notif.contenido.length > 60 ? notif.contenido.substring(0, 60) + "…" : notif.contenido : "";
        const infoIA = [];
        if (notif.procedimientoIA) infoIA.push(notif.procedimientoIA);
        if (notif.deudorIA && notif.deudorIA !== notif.certificadoNombre) infoIA.push(notif.deudorIA);
        const { color: semaforoColor, pulso } = colorSemaforo(notif.diasRestantesAcceso, notif.vencida);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "tr",
          {
            className: `hover:bg-white/[0.02] transition-colors cursor-pointer ${seleccionados.has(notif.id) ? "bg-acento-500/[0.04]" : ""}`,
            onClick: () => setDetalleNotif(notif),
            children: [
              esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-10 px-2 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  type: "checkbox",
                  checked: seleccionados.has(notif.id),
                  onChange: () => toggleSeleccion(notif.id),
                  onClick: (e) => e.stopPropagation(),
                  className: "w-4 h-4 rounded border-2 border-superficie-400 bg-superficie-700 text-acento-500 focus:ring-acento-500/40 cursor-pointer accent-acento-500"
                }
              ) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-12 px-2 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-1", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "span",
                  {
                    className: `inline-block w-3 h-3 rounded-full ${semaforoColor} ${pulso ? "animate-pulse" : ""}`,
                    title: notif.diasRestantesAcceso != null ? `${notif.diasRestantesAcceso} días` : "Sin plazo"
                  }
                ),
                notif.prioridadIA && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-1.5 py-0.5 rounded text-[10px] font-semibold ${notif.prioridadIA === "alta" ? "bg-red-500/10 text-red-400" : notif.prioridadIA === "media" ? "bg-amber-500/10 text-amber-400" : "bg-emerald-500/10 text-emerald-400"}`, children: notif.prioridadIA.charAt(0).toUpperCase() + notif.prioridadIA.slice(1) })
              ] }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-3 py-3 overflow-hidden", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "truncate", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-white font-medium text-sm", children: notif.certificadoNombre ?? "Sin titular" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-600 mx-1.5", children: "·" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium px-1.5 py-0.5 rounded bg-white/[0.04] text-superficie-400", children: abreviarAdmin(notif.administracion) })
                ] }),
                contenidoCorto && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[11px] text-superficie-500 truncate mt-0.5", title: notif.contenido ?? "", children: contenidoCorto }),
                infoIA.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[11px] text-superficie-400 truncate mt-0.5", children: infoIA.join(" · ") })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-20 px-2 py-3 text-superficie-400 text-xs", children: formatearFechaCorta(notif.fechaPublicacion || notif.fechaDeteccion) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-52 px-2 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CeldaPlazosWeb, { notif }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-28 px-2 py-3 text-right", children: notif.importeIA ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs whitespace-nowrap ${colorImporte(notif.importeIA)}`, children: notif.importeIA }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-600", children: "—" }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "w-24 px-2 py-3", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_ESTADO[notif.estado]}`, children: notif.vencida && notif.estado === "pendiente" ? "Caducada" : ETIQUETAS_ESTADO[notif.estado] }),
                notif.descartadaAutomaticamente && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-1 text-xs text-superficie-500", children: "(auto)" })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "w-28 px-2 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center gap-0.5", children: [
                tieneCalendario && (notif.sincronizadoCalendario ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { title: "Plazos en Google Calendar", className: "p-1 text-emerald-400", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarCheck, { className: "w-3.5 h-3.5" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: (e) => {
                      e.stopPropagation();
                      manejarSyncCalendario(notif.id);
                    },
                    disabled: syncingCalId === notif.id,
                    className: "p-1 rounded-lg text-superficie-500 hover:text-blue-400 hover:bg-blue-500/10 transition-colors disabled:opacity-50",
                    title: "Sincronizar plazos a Google Calendar",
                    children: syncingCalId === notif.id ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3.5 h-3.5 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Calendar, { className: "w-3.5 h-3.5" })
                  }
                )),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: (e) => {
                      e.stopPropagation();
                      setDetalleNotif(notif);
                    },
                    className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
                    title: "Ver detalle",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-4 h-4" })
                  }
                ),
                iaDisponible && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: (e) => {
                      e.stopPropagation();
                      manejarAnalizar(notif.id);
                    },
                    disabled: analizandoId === notif.id,
                    className: `p-1.5 rounded-lg disabled:opacity-50 transition-colors ${notif.prioridadIA ? `hover:bg-white/[0.05] ${notif.prioridadIA === "alta" ? "text-red-400" : notif.prioridadIA === "media" ? "text-amber-400" : "text-emerald-400"}` : "text-superficie-500 hover:text-purple-400 hover:bg-purple-500/10"}`,
                    title: notif.prioridadIA ? `IA: ${notif.prioridadIA}${notif.procedimientoIA ? ` — ${notif.procedimientoIA}` : ""} (re-analizar)` : "Analizar con IA",
                    children: analizandoId === notif.id ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-4 h-4" })
                  }
                ),
                iaDisponible && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: (e) => {
                      e.stopPropagation();
                      setEnviarModal(notif);
                    },
                    className: "p-1.5 rounded-lg text-acento-400 hover:bg-acento-500/10 transition-colors",
                    title: "Enviar al cliente",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-4 h-4" })
                  }
                )
              ] }) })
            ]
          },
          notif.id
        );
      }) })
    ] }) }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
        "Página ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " notificaciones)"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => manejarPagina(pagina - 1),
            disabled: pagina <= 1,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => manejarPagina(pagina + 1),
            disabled: pagina >= totalPaginas,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
          }
        )
      ] })
    ] }),
    analisisModal && /* @__PURE__ */ jsxRuntimeExports.jsx(ModalResultadoIA, { analisis: analisisModal, onCerrar: () => setAnalisisModal(null) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalDetalleNotificacion,
      {
        notificacion: detalleNotif,
        abierto: detalleNotif !== null,
        onCerrar: () => setDetalleNotif(null),
        onCambiarEstado: manejarCambiarEstado,
        onEnviar: (notif) => {
          setEnviarModal(notif);
          setDetalleNotif(null);
        },
        onAnalizar: manejarAnalizar,
        onGenerarRespuesta: (notif) => {
          setGenerarRespuestaNotif(notif);
          setDetalleNotif(null);
        },
        iaDisponible,
        analizandoId
      }
    ),
    enviarModal && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalEnviarEmail,
      {
        notificacion: enviarModal,
        onCerrar: () => setEnviarModal(null),
        onEnviado: (actualizada) => {
          setNotificaciones((prev) => prev.map((n) => n.id === actualizada.id ? actualizada : n));
          setEnviarModal(null);
        }
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalGenerarRespuesta,
      {
        abierto: generarRespuestaNotif !== null,
        onCerrar: () => setGenerarRespuestaNotif(null),
        notificacion: generarRespuestaNotif,
        onPreRellenarEmail: () => {
          if (generarRespuestaNotif) setEnviarModal(generarRespuestaNotif);
        }
      }
    ),
    confirmarEliminar && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] flex items-center justify-center p-4", onClick: () => setConfirmarEliminar(false), children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-md", onClick: (e) => e.stopPropagation(), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 px-6 py-4 border-b border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-5 h-5 text-red-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Eliminar notificaciones" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-superficie-300", children: [
          "¿Eliminar permanentemente ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-bold text-white", children: seleccionados.size }),
          " notificaciones? Esta acción no se puede deshacer. Se eliminarán también su historial y relaciones con gestiones."
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-3 justify-end", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setConfirmarEliminar(false),
              disabled: eliminando,
              className: "px-4 py-2 text-sm font-medium rounded-lg text-superficie-400 border border-white/[0.06]\n                    hover:bg-white/[0.05] transition-colors disabled:opacity-50",
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
                eliminando ? "Eliminando..." : "Eliminar permanentemente"
              ]
            }
          )
        ] })
      ] })
    ] }) })
  ] });
}
function EstadoCargando() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-6 h-6 text-superficie-500 animate-spin mb-3" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Cargando notificaciones..." })
  ] });
}
function EstadoVacio() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-7 h-7 text-superficie-500" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "No hay notificaciones" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Haz clic en “Actualizar” para comprobar nuevas notificaciones" })
  ] });
}
export {
  PaginaNotificaciones
};
