import { c as createLucideIcon, d as apiClient, r as reactExports, u as useNavigate, j as jsxRuntimeExports, C as CalendarDays, e as SquareCheckBig, a as Shield, f as CircleCheckBig, T as TriangleAlert, B as Bell, U as Users, A as Activity, g as ErrorApiCliente } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { l as listarTareasApi } from "./tareasServicio-CSpOVgN6.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const FileWarning = createLucideIcon("FileWarning", [
  ["path", { d: "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z", key: "1rqfz7" }],
  ["path", { d: "M12 9v4", key: "juzpu7" }],
  ["path", { d: "M12 17h.01", key: "p32p05" }]
]);
async function obtenerMetricasApi() {
  const respuesta = await apiClient.get("/dashboard/metricas");
  return respuesta.datos;
}
async function obtenerProximosEventosApi(dias = 7, limite = 5) {
  const respuesta = await apiClient.get(
    `/agenda/proximos?dias=${dias}&limite=${limite}`
  );
  return respuesta.datos ?? [];
}
const COLORES_URGENCIA = {
  critica: "text-red-400",
  alta: "text-amber-400",
  media: "text-green-400",
  baja: "text-blue-400"
};
const DOT_URGENCIA = {
  critica: "bg-red-400",
  alta: "bg-amber-400",
  media: "bg-green-400",
  baja: "bg-blue-400"
};
function formatearFechaRelativa$1(fechaStr) {
  const fecha = new Date(fechaStr);
  const ahora = /* @__PURE__ */ new Date();
  const diffMs = fecha.getTime() - ahora.getTime();
  const diffDias = Math.ceil(diffMs / (1e3 * 60 * 60 * 24));
  if (diffDias < 0) return `hace ${Math.abs(diffDias)}d`;
  if (diffDias === 0) return "hoy";
  if (diffDias === 1) return "mañana";
  return `en ${diffDias}d`;
}
function WidgetProximosEventos({ limite = 5, dias = 7 }) {
  const [eventos, setEventos] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const navigate = useNavigate();
  reactExports.useEffect(() => {
    const cargar = async () => {
      try {
        const datos = await obtenerProximosEventosApi(dias, limite);
        setEventos(datos);
      } catch {
      } finally {
        setCargando(false);
      }
    };
    cargar();
  }, [dias, limite]);
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-400 animate-spin" }) });
  }
  if (eventos.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-5 py-6 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarDays, { className: "w-8 h-8 text-superficie-600 mx-auto mb-2" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-500", children: "Sin eventos próximos" })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "divide-y divide-white/[0.04]", children: eventos.map((evento) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "li",
      {
        className: "flex items-center gap-3 px-5 py-3 hover:bg-white/[0.02] transition-colors",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-2 h-2 rounded-full flex-shrink-0 ${DOT_URGENCIA[evento.urgencia]}` }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 truncate", children: evento.titulo }),
            evento.nombreReferencia && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 truncate", children: evento.nombreReferencia })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-medium flex-shrink-0 ${COLORES_URGENCIA[evento.urgencia]}`, children: formatearFechaRelativa$1(evento.fecha) })
        ]
      },
      evento.id
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => navigate("/app/calendario"),
        className: "flex items-center justify-center gap-1 w-full px-5 py-3 text-xs font-medium text-acento-400 hover:text-acento-300 hover:bg-white/[0.02] border-t border-white/[0.06] transition-colors",
        children: [
          "Ver calendario",
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-3.5 h-3.5" })
        ]
      }
    )
  ] });
}
const DOT_PRIORIDAD = {
  critica: "bg-red-400",
  alta: "bg-amber-400",
  media: "bg-emerald-400",
  baja: "bg-blue-400"
};
const COLOR_PRIORIDAD = {
  critica: "text-red-400",
  alta: "text-amber-400",
  media: "text-emerald-400",
  baja: "text-blue-400"
};
function formatearFechaRelativa(fechaStr) {
  if (!fechaStr) return "Sin fecha";
  const fecha = new Date(fechaStr);
  const ahora = /* @__PURE__ */ new Date();
  const diffMs = fecha.getTime() - ahora.getTime();
  const diffDias = Math.ceil(diffMs / (1e3 * 60 * 60 * 24));
  if (diffDias < 0) return `hace ${Math.abs(diffDias)}d`;
  if (diffDias === 0) return "hoy";
  if (diffDias === 1) return "manana";
  return `en ${diffDias}d`;
}
function WidgetTareasPendientes() {
  const [tareas, setTareas] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const navigate = useNavigate();
  reactExports.useEffect(() => {
    const cargar = async () => {
      try {
        const resultado = await listarTareasApi({ estado: "pendiente", limite: 5 });
        const resultadoProgreso = await listarTareasApi({ estado: "en_progreso", limite: 5 });
        const todas = [...resultado.tareas, ...resultadoProgreso.tareas];
        const ORDEN_PRIORIDAD = {
          critica: 0,
          alta: 1,
          media: 2,
          baja: 3
        };
        todas.sort((a, b) => (ORDEN_PRIORIDAD[a.prioridad] ?? 99) - (ORDEN_PRIORIDAD[b.prioridad] ?? 99));
        setTareas(todas.slice(0, 5));
      } catch {
      } finally {
        setCargando(false);
      }
    };
    cargar();
  }, []);
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-400 animate-spin" }) });
  }
  if (tareas.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-5 py-6 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(SquareCheckBig, { className: "w-8 h-8 text-superficie-600 mx-auto mb-2" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-500", children: "No hay tareas pendientes" })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "divide-y divide-white/[0.04]", children: tareas.map((tarea) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "li",
      {
        className: "flex items-center gap-3 px-5 py-3 hover:bg-white/[0.02] transition-colors",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-2 h-2 rounded-full flex-shrink-0 ${DOT_PRIORIDAD[tarea.prioridad]}` }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 truncate", children: tarea.titulo }),
            tarea.nombreAsignado && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 truncate", children: tarea.nombreAsignado })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-medium flex-shrink-0 ${COLOR_PRIORIDAD[tarea.prioridad]}`, children: formatearFechaRelativa(tarea.fechaLimite) })
        ]
      },
      tarea.id
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => navigate("/app/tareas"),
        className: "flex items-center justify-center gap-1 w-full px-5 py-3 text-xs font-medium text-acento-400 hover:text-acento-300 hover:bg-white/[0.02] border-t border-white/[0.06] transition-colors",
        children: [
          "Ver todas las tareas",
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-3.5 h-3.5" })
        ]
      }
    )
  ] });
}
function CardKpi({
  titulo,
  valor,
  subtitulo,
  icono: Icono,
  color
}) {
  const colores = {
    green: "bg-green-500/10 text-green-400 border-green-500/20",
    red: "bg-red-500/10 text-red-400 border-red-500/20",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    acento: "bg-acento-500/10 text-acento-400 border-acento-500/20",
    violet: "bg-violet-500/10 text-violet-400 border-violet-500/20"
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl p-5 flex items-start justify-between", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: titulo }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-3xl font-bold text-white mt-1", children: valor }),
      subtitulo && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: subtitulo })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `p-2.5 rounded-lg border ${colores[color]}`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-5 h-5" }) })
  ] });
}
function TablaActividad({ registros }) {
  if (registros.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-500 text-center py-8", children: "Sin actividad reciente registrada" });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Usuario" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Certificado" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Accion" })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: registros.map((reg) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3 text-superficie-400 whitespace-nowrap", children: formatearFecha(reg.fecha) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3 text-superficie-200", children: reg.nombreUsuario ?? "—" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3 text-superficie-300", children: reg.nombreCertificado ?? "—" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-acento-500/10 text-acento-400 border border-acento-500/20", children: reg.accion }) })
    ] }, reg.id)) })
  ] }) });
}
function PaginaDashboard() {
  const [metricas, setMetricas] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const cargarMetricas = async () => {
    setCargando(true);
    setError(null);
    try {
      const datos = await obtenerMetricasApi();
      setMetricas(datos);
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al cargar las metricas del dashboard");
      }
    } finally {
      setCargando(false);
    }
  };
  reactExports.useEffect(() => {
    cargarMetricas();
  }, []);
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-24", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando dashboard..." })
    ] });
  }
  if (error) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-24 gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400 max-w-md text-center", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: cargarMetricas,
          className: "px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500 hover:bg-acento-400 rounded-lg transition-colors",
          children: "Reintentar"
        }
      )
    ] });
  }
  if (!metricas) return null;
  const { certificados, notificaciones, usuarios, actividadReciente } = metricas;
  const metricasExtendidas = metricas;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Dashboard" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Resumen de tu organización" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-400 uppercase tracking-wide mb-3", children: "Certificados" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Total",
          valor: certificados.total,
          icono: Shield,
          color: "acento"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Activos",
          valor: certificados.activos,
          icono: CircleCheckBig,
          color: "green"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Caducados",
          valor: certificados.caducados,
          icono: FileWarning,
          color: "red"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Por vencer",
          valor: certificados.proximosAVencer,
          icono: TriangleAlert,
          color: "amber"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-400 uppercase tracking-wide mb-3", children: "Notificaciones" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Pendientes",
          valor: notificaciones.pendientes,
          icono: Clock,
          color: "amber"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Leidas",
          valor: notificaciones.leidas,
          icono: Bell,
          color: "blue"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CardKpi,
        {
          titulo: "Gestionadas",
          valor: notificaciones.gestionadas,
          icono: CircleCheckBig,
          color: "green"
        }
      )
    ] }),
    metricasExtendidas.notificacionesPorUrgencia && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-3 mb-8", children: [
      { etiqueta: "Criticas", clave: "critica", color: "bg-red-500/20 text-red-400" },
      { etiqueta: "Altas", clave: "alta", color: "bg-amber-500/20 text-amber-400" },
      { etiqueta: "Medias", clave: "media", color: "bg-green-500/20 text-green-400" },
      { etiqueta: "Bajas", clave: "baja", color: "bg-blue-500/20 text-blue-400" }
    ].map(({ etiqueta, clave, color }) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: "bg-superficie-800/60 border border-white/[0.06] rounded-xl p-3 text-center",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-lg font-bold ${color.split(" ")[1]}`, children: metricasExtendidas.notificacionesPorUrgencia[clave] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: etiqueta })
        ]
      },
      clave
    )) }),
    !metricasExtendidas.notificacionesPorUrgencia && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-8" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-400 uppercase tracking-wide mb-3", children: "Usuarios" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
      CardKpi,
      {
        titulo: "Usuarios",
        valor: usuarios.activos,
        subtitulo: `${usuarios.activos} activos de ${usuarios.total}`,
        icono: Users,
        color: "violet"
      }
    ) }),
    metricasExtendidas.gestiones && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-8", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-800/60 border border-white/[0.06] rounded-xl p-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-superficie-300 mb-3", children: "Gestiones" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-6", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-2xl font-bold text-green-400", children: metricasExtendidas.gestiones.activas }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Activas" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-2xl font-bold text-blue-400", children: metricasExtendidas.gestiones.completadas }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Completadas" })
        ] })
      ] })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl overflow-hidden", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-5 py-3 border-b border-white/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarDays, { className: "w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-superficie-300", children: "Próximos eventos" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(WidgetProximosEventos, { limite: 5, dias: 14 })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl overflow-hidden", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-5 py-3 border-b border-white/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(SquareCheckBig, { className: "w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-superficie-300", children: "Tareas pendientes" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(WidgetTareasPendientes, {})
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-8", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-5 py-3 border-b border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Activity, { className: "w-4 h-4 text-superficie-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm font-medium text-superficie-300", children: [
          "Últimos ",
          actividadReciente.length,
          " registros"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(TablaActividad, { registros: actividadReciente })
    ] }) })
  ] });
}
export {
  PaginaDashboard
};
