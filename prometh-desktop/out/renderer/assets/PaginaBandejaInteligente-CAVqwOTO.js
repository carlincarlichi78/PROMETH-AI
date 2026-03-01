import { c as createLucideIcon, d as apiClient, r as reactExports, j as jsxRuntimeExports, T as TriangleAlert, Q as ChartColumn, R as Building2, A as Activity, m as Search, X, V as Star, a as Shield, Y as EyeOff, F as FolderOpen, B as Bell, P as Plus, Z as Zap, E as Eye, G as Globe, _ as Inbox } from "./index-DMbE3NR1.js";
import { l as listarGestionesApi } from "./gestionesServicio-z25W8jIF.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { M as Mail } from "./mail-BDEpMyrm.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { U as User } from "./user-Cs3upA-3.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { C as Calendar } from "./calendar-KREuhz-X.js";
import { L as ListTodo } from "./list-todo-WH_1tbpH.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { P as Pencil } from "./pencil-BuwvL_tU.js";
import { S as Settings2 } from "./settings-2-rsIHKSP7.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const BookOpen = createLucideIcon("BookOpen", [
  ["path", { d: "M12 7v14", key: "1akyts" }],
  [
    "path",
    {
      d: "M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z",
      key: "ruj8y"
    }
  ]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const MailOpen = createLucideIcon("MailOpen", [
  [
    "path",
    {
      d: "M21.2 8.4c.5.38.8.97.8 1.6v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V10a2 2 0 0 1 .8-1.6l8-6a2 2 0 0 1 2.4 0l8 6Z",
      key: "1jhwl8"
    }
  ],
  ["path", { d: "m22 10-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 10", key: "1qfld7" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const ToggleLeft = createLucideIcon("ToggleLeft", [
  ["rect", { width: "20", height: "12", x: "2", y: "6", rx: "6", ry: "6", key: "f2vt7d" }],
  ["circle", { cx: "8", cy: "12", r: "2", key: "1nvbw3" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const ToggleRight = createLucideIcon("ToggleRight", [
  ["rect", { width: "20", height: "12", x: "2", y: "6", rx: "6", ry: "6", key: "f2vt7d" }],
  ["circle", { cx: "16", cy: "12", r: "2", key: "4ma0v8" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const WifiOff = createLucideIcon("WifiOff", [
  ["path", { d: "M12 20h.01", key: "zekei9" }],
  ["path", { d: "M8.5 16.429a5 5 0 0 1 7 0", key: "1bycff" }],
  ["path", { d: "M5 12.859a10 10 0 0 1 5.17-2.69", key: "1dl1wf" }],
  ["path", { d: "M19 12.859a10 10 0 0 0-2.007-1.523", key: "4k23kn" }],
  ["path", { d: "M2 8.82a15 15 0 0 1 4.177-2.643", key: "1grhjp" }],
  ["path", { d: "M22 8.82a15 15 0 0 0-11.288-3.764", key: "z3jwby" }],
  ["path", { d: "m2 2 20 20", key: "1ooewy" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Wifi = createLucideIcon("Wifi", [
  ["path", { d: "M12 20h.01", key: "zekei9" }],
  ["path", { d: "M2 8.82a15 15 0 0 1 20 0", key: "dnpr2z" }],
  ["path", { d: "M5 12.859a10 10 0 0 1 14 0", key: "1x1e6c" }],
  ["path", { d: "M8.5 16.429a5 5 0 0 1 7 0", key: "1bycff" }]
]);
const BASE = "/bandeja-inteligente";
async function listarCuentasApi() {
  const respuesta = await apiClient.get(`${BASE}/cuentas`);
  return respuesta.datos ?? [];
}
async function crearCuentaApi(datos) {
  const respuesta = await apiClient.post(`${BASE}/cuentas`, datos);
  return respuesta.datos;
}
async function actualizarCuentaApi(id, datos) {
  const respuesta = await apiClient.put(`${BASE}/cuentas/${id}`, datos);
  return respuesta.datos;
}
async function eliminarCuentaApi(id) {
  await apiClient.del(`${BASE}/cuentas/${id}`);
}
async function testConexionApi(id) {
  const respuesta = await apiClient.post(
    `${BASE}/cuentas/${id}/test`,
    {}
  );
  return respuesta.datos;
}
async function forzarPollingApi(id) {
  const respuesta = await apiClient.post(
    `${BASE}/cuentas/${id}/polling`,
    {}
  );
  return respuesta.datos;
}
async function listarEmailsApi(params) {
  const query = new URLSearchParams();
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  if (params?.estado) query.set("estado", params.estado);
  if (params?.cuentaCorreoId) query.set("cuentaCorreoId", params.cuentaCorreoId);
  if (params?.gestionId) query.set("gestionId", params.gestionId);
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  const qs = query.toString();
  const respuesta = await apiClient.get(
    `${BASE}/emails${qs ? `?${qs}` : ""}`
  );
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
async function clasificarEmailApi(id, datos) {
  const respuesta = await apiClient.post(
    `${BASE}/emails/${id}/clasificar`,
    datos
  );
  return respuesta.datos;
}
async function ignorarEmailApi(id) {
  await apiClient.post(`${BASE}/emails/${id}/ignorar`, {});
}
async function listarReglasApi(params) {
  const query = new URLSearchParams();
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  if (params?.gestionId) query.set("gestionId", params.gestionId);
  if (params?.tipo) query.set("tipo", params.tipo);
  if (params?.activa) query.set("activa", params.activa);
  const qs = query.toString();
  const respuesta = await apiClient.get(
    `${BASE}/reglas${qs ? `?${qs}` : ""}`
  );
  return {
    datos: respuesta.datos ?? [],
    meta: respuesta.meta ?? {
      total: 0,
      pagina: 1,
      limite: 50,
      totalPaginas: 0
    }
  };
}
async function crearReglaApi(datos) {
  const respuesta = await apiClient.post(`${BASE}/reglas`, datos);
  return respuesta.datos;
}
async function actualizarReglaApi(id, datos) {
  const respuesta = await apiClient.put(`${BASE}/reglas/${id}`, datos);
  return respuesta.datos;
}
async function eliminarReglaApi(id) {
  await apiClient.del(`${BASE}/reglas/${id}`);
}
async function marcarEmailLeidoApi(id, leido = true) {
  const respuesta = await apiClient.patch(
    `${BASE}/emails/${id}/leer`,
    { leido }
  );
  return respuesta.datos;
}
async function toggleDestacarEmailApi(id) {
  const respuesta = await apiClient.patch(
    `${BASE}/emails/${id}/destacar`,
    {}
  );
  return respuesta.datos;
}
async function obtenerEstadisticasApi() {
  const respuesta = await apiClient.get(`${BASE}/estadisticas`);
  return respuesta.datos;
}
async function listarOrganismosApi() {
  const respuesta = await apiClient.get(`${BASE}/organismos`);
  return respuesta.datos;
}
async function crearOrganismoApi(datos) {
  const respuesta = await apiClient.post(`${BASE}/organismos`, datos);
  return respuesta.datos;
}
async function actualizarOrganismoApi(id, datos) {
  const respuesta = await apiClient.put(`${BASE}/organismos/${id}`, datos);
  return respuesta.datos;
}
async function eliminarOrganismoApi(id) {
  await apiClient.del(`${BASE}/organismos/${id}`);
}
function formatearFechaRelativa(fechaStr) {
  if (!fechaStr) return "—";
  const fecha = new Date(fechaStr);
  const ahora = /* @__PURE__ */ new Date();
  const diffMs = ahora.getTime() - fecha.getTime();
  const diffMin = Math.floor(diffMs / 6e4);
  const diffHoras = Math.floor(diffMs / 36e5);
  const diffDias = Math.floor(diffMs / 864e5);
  if (diffMin < 1) return "Ahora";
  if (diffMin < 60) return `hace ${diffMin}m`;
  if (diffHoras < 24) return `hace ${diffHoras}h`;
  if (diffDias === 1) return "Ayer";
  if (diffDias < 7) return `hace ${diffDias}d`;
  return fecha.toLocaleDateString("es-ES", { day: "2-digit", month: "short" });
}
const COLORES_URGENCIA_TEMPORAL = {
  critica: "bg-red-500/10 text-red-400 border-red-500/20",
  alta: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  media: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  baja: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
};
function BadgeEstado({ estado }) {
  const estilos = {
    pendiente: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    clasificado: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    cuarentena: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    procesado: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    ignorado: "bg-superficie-700/50 text-superficie-500 border-superficie-600/50",
    error: "bg-red-500/10 text-red-400 border-red-500/20"
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "span",
    {
      className: `inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${estilos[estado] ?? estilos.pendiente}`,
      children: estado
    }
  );
}
function KPICard({
  label,
  valor,
  icono: Icono,
  color = "acento"
}) {
  const colores = {
    acento: "text-acento-400",
    amber: "text-amber-400",
    blue: "text-blue-400",
    emerald: "text-emerald-400",
    red: "text-red-400"
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-4 h-4 ${colores[color] ?? colores.acento}` }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: label })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-2xl font-semibold text-white mt-1", children: valor })
  ] });
}
function TabBandejaEmails() {
  const [emails, setEmails] = reactExports.useState([]);
  const [estadisticas, setEstadisticas] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [filtroEstado, setFiltroEstado] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const [modalClasificar, setModalClasificar] = reactExports.useState(null);
  const [emailDetalle, setEmailDetalle] = reactExports.useState(null);
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const [resultado, stats] = await Promise.all([
        listarEmailsApi({
          pagina,
          limite: 25,
          estado: filtroEstado || void 0,
          busqueda: busqueda || void 0
        }),
        obtenerEstadisticasApi()
      ]);
      setEmails(resultado.datos);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
      setEstadisticas(stats);
    } catch {
      setError("Error al cargar emails");
    } finally {
      setCargando(false);
    }
  }, [pagina, filtroEstado, busqueda]);
  reactExports.useEffect(() => {
    const timer = setTimeout(cargar, 300);
    return () => clearTimeout(timer);
  }, [cargar]);
  async function manejarIgnorar(id) {
    try {
      await ignorarEmailApi(id);
      cargar();
    } catch {
      setError("Error al ignorar email");
    }
  }
  async function manejarToggleDestacado(id) {
    try {
      const resultado = await toggleDestacarEmailApi(id);
      setEmails((prev) => prev.map((e) => e.id === id ? { ...e, destacado: resultado.destacado } : e));
    } catch {
      setError("Error al destacar email");
    }
  }
  async function manejarMarcarLeido(id, leido) {
    try {
      await marcarEmailLeidoApi(id, leido);
      setEmails((prev) => prev.map((e) => e.id === id ? { ...e, leido } : e));
    } catch {
      setError("Error al marcar como leído");
    }
  }
  function abrirDetalle(email) {
    setEmailDetalle(email);
    if (!email.leido) {
      manejarMarcarLeido(email.id, true);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    estadisticas && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(KPICard, { label: "Sin leer", valor: estadisticas.sinLeer, icono: Mail, color: "blue" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(KPICard, { label: "Cuarentena", valor: estadisticas.cuarentena, icono: CircleAlert, color: "amber" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(KPICard, { label: "Urgentes", valor: estadisticas.urgentes, icono: TriangleAlert, color: "red" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(KPICard, { label: "Hoy", valor: estadisticas.hoy, icono: Clock }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(KPICard, { label: "Esta semana", valor: estadisticas.estaSemana, icono: ChartColumn, color: "emerald" })
      ] }),
      estadisticas.porAdministracion.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2", children: estadisticas.porAdministracion.slice(0, 8).map(({ administracion, cantidad }) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "span",
        {
          className: "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-superficie-800/50 border border-white/[0.04] text-xs",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "w-3 h-3 text-superficie-500" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-300", children: administracion }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-acento-400 font-semibold", children: cantidad })
          ]
        },
        administracion
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-3 gap-3", children: [
        (estadisticas.porOrganismo ?? []).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 space-y-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 text-xs text-superficie-500", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "w-3.5 h-3.5" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium", children: "Por organismo" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1.5", children: (estadisticas.porOrganismo ?? []).slice(0, 5).map((org) => {
            const maxCantidad = Math.max(...(estadisticas.porOrganismo ?? []).map((o) => o.cantidad));
            const pct = maxCantidad > 0 ? org.cantidad / maxCantidad * 100 : 0;
            return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-0.5", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between text-xs", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-300 truncate max-w-[150px]", children: org.nombre }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-acento-400 font-semibold", children: org.cantidad })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-1 rounded-full bg-superficie-800", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-full rounded-full bg-acento-500/40", style: { width: `${pct}%` } }) })
            ] }, org.organismoId ?? org.nombre);
          }) })
        ] }),
        (estadisticas.porCertificado ?? []).length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 space-y-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 text-xs text-superficie-500", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(User, { className: "w-3.5 h-3.5" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium", children: "Por cliente (NIF)" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1.5", children: (estadisticas.porCertificado ?? []).slice(0, 5).map((cert) => {
            const maxCantidad = Math.max(...(estadisticas.porCertificado ?? []).map((c) => c.cantidad));
            const pct = maxCantidad > 0 ? cert.cantidad / maxCantidad * 100 : 0;
            return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-0.5", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between text-xs", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-300 font-mono", children: cert.nif ?? "Sin NIF" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-acento-400 font-semibold", children: cert.cantidad })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-1 rounded-full bg-superficie-800", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-full rounded-full bg-blue-500/40", style: { width: `${pct}%` } }) })
            ] }, cert.nif ?? "sin-nif");
          }) })
        ] }),
        (estadisticas.accionesEjecutadasHoy ?? 0) > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 flex flex-col justify-center items-center text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Activity, { className: "w-5 h-5 text-emerald-400 mb-2" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-2xl font-semibold text-white", children: estadisticas.accionesEjecutadasHoy }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: "Acciones ejecutadas hoy" })
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: busqueda,
            onChange: (e) => {
              setBusqueda(e.target.value);
              setPagina(1);
            },
            placeholder: "Buscar por remitente, asunto o administración...",
            className: "w-full pl-9 pr-4 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-500 focus:outline-none focus:border-acento-500/30"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5", children: ["", "pendiente", "cuarentena", "clasificado", "procesado", "ignorado"].map((estado) => {
        const labels = {
          "": "Todos",
          pendiente: "Pendientes",
          cuarentena: "Cuarentena",
          clasificado: "Clasificados",
          procesado: "Procesados",
          ignorado: "Ignorados"
        };
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => {
              setFiltroEstado(estado);
              setPagina(1);
            },
            className: `px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors ${filtroEstado === estado ? "bg-acento-500/20 text-acento-400 border-acento-500/30" : "bg-superficie-800/60 text-superficie-400 border-white/[0.06] hover:border-white/[0.12]"}`,
            children: labels[estado]
          },
          estado
        );
      }) })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando correos..." })
    ] }) : emails.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-12 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-10 h-10 text-superficie-600 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "No hay correos" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Los correos aparecerán aquí cuando se descarguen de tus cuentas IMAP" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden divide-y divide-white/[0.04]", children: emails.map((email) => {
      const esNoLeido = !email.leido;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          onClick: () => abrirDetalle(email),
          className: `flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-white/[0.02] ${esNoLeido ? "bg-acento-500/[0.03]" : ""}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: (e) => {
                  e.stopPropagation();
                  manejarToggleDestacado(email.id);
                },
                className: `shrink-0 p-0.5 rounded transition-colors ${email.destacado ? "text-amber-400" : "text-superficie-600 hover:text-superficie-400"}`,
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Star, { className: `w-4 h-4 ${email.destacado ? "fill-current" : ""}` })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: (e) => {
                  e.stopPropagation();
                  manejarMarcarLeido(email.id, !email.leido);
                },
                className: "shrink-0 p-0.5 rounded text-superficie-500 hover:text-superficie-300 transition-colors",
                title: email.leido ? "Marcar como no leído" : "Marcar como leído",
                children: email.leido ? /* @__PURE__ */ jsxRuntimeExports.jsx(MailOpen, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-4 h-4 text-acento-400" })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm truncate max-w-[200px] ${esNoLeido ? "font-semibold text-white" : "text-superficie-300"}`, children: email.remitente.split("@")[0] }),
                email.administracion && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-superficie-800/60 text-superficie-400 border border-white/[0.04]", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "w-2.5 h-2.5" }),
                  email.administracion
                ] }),
                email.urgenciaTemporal && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${COLORES_URGENCIA_TEMPORAL[email.urgenciaTemporal]}`, children: email.urgenciaTemporal })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mt-0.5", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm truncate ${esNoLeido ? "text-superficie-200" : "text-superficie-400"}`, children: email.asunto ?? "(sin asunto)" }),
                email.cuerpoPreview && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-600 truncate hidden sm:inline", children: [
                  "— ",
                  email.cuerpoPreview.slice(0, 80)
                ] })
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 shrink-0", children: [
              email.nombreGestion && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 hidden lg:inline max-w-[120px] truncate", children: email.nombreCliente ?? email.nombreGestion }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeEstado, { estado: email.estado }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 whitespace-nowrap w-14 text-right", children: formatearFechaRelativa(email.fechaEmail) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-0.5", children: [
                (email.estado === "cuarentena" || email.estado === "pendiente") && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: (e) => {
                      e.stopPropagation();
                      setModalClasificar(email);
                    },
                    className: "p-1 text-acento-400 hover:bg-acento-500/10 rounded transition-colors",
                    title: "Clasificar",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(Shield, { className: "w-3.5 h-3.5" })
                  }
                ),
                email.estado !== "ignorado" && email.estado !== "procesado" && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: (e) => {
                      e.stopPropagation();
                      manejarIgnorar(email.id);
                    },
                    className: "p-1 text-superficie-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors",
                    title: "Ignorar",
                    children: /* @__PURE__ */ jsxRuntimeExports.jsx(EyeOff, { className: "w-3.5 h-3.5" })
                  }
                )
              ] })
            ] })
          ]
        },
        email.id
      );
    }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Página ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " correos)"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setPagina((p) => Math.max(1, p - 1)),
            disabled: pagina <= 1,
            className: "p-1.5 rounded-lg text-superficie-400 disabled:opacity-30 hover:bg-white/[0.03]",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
            disabled: pagina >= totalPaginas,
            className: "p-1.5 rounded-lg text-superficie-400 disabled:opacity-30 hover:bg-white/[0.03]",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
          }
        )
      ] })
    ] }),
    modalClasificar && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalClasificar,
      {
        email: modalClasificar,
        onCerrar: () => setModalClasificar(null),
        onClasificado: () => {
          setModalClasificar(null);
          cargar();
        }
      }
    ),
    emailDetalle && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalDetalleEmail,
      {
        email: emailDetalle,
        onCerrar: () => setEmailDetalle(null),
        onClasificar: (email) => {
          setEmailDetalle(null);
          setModalClasificar(email);
        }
      }
    )
  ] });
}
function ModalDetalleEmail({
  email,
  onCerrar,
  onClasificar
}) {
  useEscapeKey(true, onCerrar);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-5 h-5 text-acento-400 shrink-0" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white truncate", children: email.asunto ?? "(sin asunto)" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors shrink-0", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-superficie-200", children: "De: " }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-100", children: email.remitente })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: email.fechaEmail ? new Date(email.fechaEmail).toLocaleString("es-ES") : "—" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeEstado, { estado: email.estado }),
          email.administracion && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-superficie-800/60 text-superficie-300 border border-white/[0.04]", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "w-3 h-3" }),
            email.administracion
          ] }),
          email.urgenciaTemporal && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${COLORES_URGENCIA_TEMPORAL[email.urgenciaTemporal]}`, children: [
            "Urgencia: ",
            email.urgenciaTemporal
          ] }),
          email.nombreGestion && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20", children: email.nombreCliente ?? email.nombreGestion })
        ] })
      ] }),
      email.resumenIa && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 rounded-lg bg-purple-500/5 border border-purple-500/10", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-purple-400 font-medium mb-1", children: "Resumen IA" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300", children: email.resumenIa })
      ] }),
      email.razonamientoIa && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 rounded-lg bg-purple-500/5 border border-purple-500/10", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-purple-400 font-medium mb-1", children: [
          "Sugerencia IA (confianza: ",
          email.confianzaIa,
          "%)"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300", children: email.razonamientoIa })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-lg bg-superficie-800/40 border border-white/[0.04] p-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300 whitespace-pre-wrap leading-relaxed", children: email.cuerpoPreview ?? "Sin contenido" }) }),
      email.notificacionId && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 p-3 rounded-lg bg-acento-500/5 border border-acento-500/10", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-4 h-4 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-acento-400", children: [
          "Notificación vinculada: ",
          email.notificacionId.slice(0, 8),
          "..."
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2 pt-2 border-t border-white/[0.06]", children: [
        (email.estado === "cuarentena" || email.estado === "pendiente") && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => onClasificar(email),
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Shield, { className: "w-4 h-4" }),
              "Clasificar"
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.03]",
            children: "Cerrar"
          }
        )
      ] })
    ] })
  ] }) });
}
function ModalClasificar({
  email,
  onCerrar,
  onClasificado
}) {
  useEscapeKey(true, onCerrar);
  const [gestionesDisp, setGestionesDisp] = reactExports.useState([]);
  const [gestionId, setGestionId] = reactExports.useState("");
  const [crearRegla, setCrearRegla] = reactExports.useState(false);
  const [tipoRegla, setTipoRegla] = reactExports.useState("remitente_exacto");
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState("");
  reactExports.useEffect(() => {
    listarGestionesApi({ limite: 100 }).then((r) => setGestionesDisp(r.gestiones ?? [])).catch(() => {
    });
  }, []);
  async function guardar() {
    setGuardando(true);
    setError("");
    try {
      await clasificarEmailApi(email.id, {
        gestionId: gestionId || void 0,
        crearRegla,
        tipoRegla: crearRegla ? tipoRegla : void 0
      });
      onClasificado();
    } catch {
      setError("Error al clasificar");
    } finally {
      setGuardando(false);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6 w-full max-w-lg mx-4", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Clasificar email" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 rounded-lg bg-superficie-800/50 border border-white/[0.04]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-400", children: [
          "De: ",
          email.remitente
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 mt-1", children: email.asunto ?? "(sin asunto)" })
      ] }),
      email.razonamientoIa && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 rounded-lg bg-purple-500/5 border border-purple-500/10", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-purple-400 font-medium mb-1", children: [
          "Sugerencia IA (confianza: ",
          email.confianzaIa,
          "%)"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-300", children: email.razonamientoIa })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Asignar a gestion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: gestionId,
            onChange: (e) => setGestionId(e.target.value),
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 focus:outline-none focus:border-acento-500/30",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Sin asignar" }),
              gestionesDisp.map((g) => /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: g.id, children: [
                g.nombre,
                " ",
                g.cliente ? `(${g.cliente})` : ""
              ] }, g.id))
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "button",
            onClick: () => setCrearRegla(!crearRegla),
            className: `relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${crearRegla ? "bg-acento-500" : "bg-superficie-600"}`,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: `inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${crearRegla ? "translate-x-4" : "translate-x-0.5"}`
              }
            )
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-300", children: "Crear regla automatica" })
      ] }),
      crearRegla && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: tipoRegla,
          onChange: (e) => setTipoRegla(e.target.value),
          className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 focus:outline-none focus:border-acento-500/30",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: "remitente_exacto", children: [
              "Por remitente exacto (",
              email.remitente,
              ")"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: "dominio", children: [
              "Por dominio (",
              email.remitente.split("@")[1] ?? "",
              ")"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "asunto_contiene", children: "Por asunto contiene" })
          ]
        }
      ),
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-red-400", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 pt-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "flex-1 px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.03]",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: guardar,
            disabled: guardando,
            className: "flex-1 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 disabled:opacity-50",
            children: guardando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin mx-auto" }) : "Clasificar"
          }
        )
      ] })
    ] })
  ] }) });
}
const TIPOS_ACCION = [
  { tipo: "crear_evento_calendario", label: "Crear evento calendario", icono: Calendar, color: "text-blue-400" },
  { tipo: "crear_tarea", label: "Crear tarea", icono: ListTodo, color: "text-emerald-400" },
  { tipo: "vincular_gestion", label: "Vincular gestion", icono: FolderOpen, color: "text-purple-400" },
  { tipo: "notificar_usuario", label: "Notificar usuario", icono: Bell, color: "text-amber-400" },
  { tipo: "marcar_urgente", label: "Marcar urgente", icono: TriangleAlert, color: "text-red-400" }
];
const PLACEHOLDERS = "{organismo}, {titular}, {asunto}, {nif}, {fecha}";
function ModalReglaAcciones({ regla, onCerrar, onGuardado }) {
  const [acciones, setAcciones] = reactExports.useState(regla.accionesAutomaticas ?? []);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [tipoNuevo, setTipoNuevo] = reactExports.useState("");
  function agregarAccion() {
    if (!tipoNuevo) return;
    const configDefault = obtenerConfigDefault(tipoNuevo);
    setAcciones([...acciones, { tipo: tipoNuevo, config: configDefault }]);
    setTipoNuevo("");
  }
  function eliminarAccion(index) {
    setAcciones(acciones.filter((_, i) => i !== index));
  }
  function actualizarConfig(index, campo, valor) {
    setAcciones(acciones.map(
      (a, i) => i === index ? { ...a, config: { ...a.config, [campo]: valor } } : a
    ));
  }
  async function guardar() {
    setGuardando(true);
    try {
      await actualizarReglaApi(regla.id, {
        accionesAutomaticas: acciones
      });
      onGuardado();
    } catch {
    } finally {
      setGuardando(false);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 flex items-center justify-center z-50", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "div",
    {
      className: "bg-superficie-900 border border-white/[0.06] rounded-xl p-6 w-full max-w-lg shadow-xl max-h-[80vh] overflow-y-auto",
      onClick: (e) => e.stopPropagation(),
      children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-lg font-semibold text-white", children: "Configurar acciones" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500 mt-0.5", children: [
              "Regla: ",
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-mono text-superficie-400", children: regla.valor })
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500 mb-4", children: [
          "Estas acciones se ejecutan automaticamente cuando un email coincida con esta regla. Placeholders: ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "text-superficie-400", children: PLACEHOLDERS })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3 mb-4", children: [
          acciones.length === 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-500 text-center py-4", children: "Sin acciones configuradas" }),
          acciones.map((accion, index) => {
            const tipoInfo = TIPOS_ACCION.find((t) => t.tipo === accion.tipo);
            if (!tipoInfo) return null;
            const Icono = tipoInfo.icono;
            return /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "div",
              {
                className: "cristal rounded-lg p-3 space-y-2",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
                      /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-4 h-4 ${tipoInfo.color}` }),
                      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-superficie-200", children: tipoInfo.label })
                    ] }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "button",
                      {
                        onClick: () => eliminarAccion(index),
                        className: "p-1 text-superficie-500 hover:text-red-400 rounded transition-colors",
                        children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3.5 h-3.5" })
                      }
                    )
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    FormularioAccion,
                    {
                      tipo: accion.tipo,
                      config: accion.config,
                      onCambio: (campo, valor) => actualizarConfig(index, campo, valor)
                    }
                  )
                ]
              },
              index
            );
          })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-6", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: tipoNuevo,
              onChange: (e) => setTipoNuevo(e.target.value),
              className: "flex-1 px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 focus:outline-none focus:border-acento-500/30",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Seleccionar accion..." }),
                TIPOS_ACCION.map((t) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: t.tipo, children: t.label }, t.tipo))
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: agregarAccion,
              disabled: !tipoNuevo,
              className: "flex items-center gap-1 px-3 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 disabled:opacity-40 transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
                "Agregar"
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3 border-t border-white/[0.06] pt-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: onCerrar,
              className: "px-4 py-2 text-sm text-superficie-400 hover:text-white transition-colors",
              children: "Cancelar"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: guardar,
              disabled: guardando,
              className: "flex items-center gap-2 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 disabled:opacity-50 transition-colors",
              children: [
                guardando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
                "Guardar acciones"
              ]
            }
          )
        ] })
      ]
    }
  ) });
}
function FormularioAccion({
  tipo,
  config,
  onCambio
}) {
  const inputClase = "w-full px-3 py-1.5 text-xs bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-500 focus:outline-none focus:border-acento-500/30";
  switch (tipo) {
    case "crear_evento_calendario":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-[10px] text-superficie-500 uppercase font-medium", children: "Titulo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: config.titulo ?? "",
              onChange: (e) => onCambio("titulo", e.target.value),
              placeholder: "Aviso {organismo} - {titular}",
              className: inputClase
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-[10px] text-superficie-500 uppercase font-medium", children: "Dias anticipacion" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              min: 0,
              max: 90,
              value: config.diasAnticipacion ?? 2,
              onChange: (e) => onCambio("diasAnticipacion", parseInt(e.target.value) || 0),
              className: inputClase
            }
          )
        ] })
      ] });
    case "crear_tarea":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-[10px] text-superficie-500 uppercase font-medium", children: "Titulo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: config.titulo ?? "",
              onChange: (e) => onCambio("titulo", e.target.value),
              placeholder: "Revisar: {asunto}",
              className: inputClase
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-[10px] text-superficie-500 uppercase font-medium", children: "Prioridad" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: config.prioridad ?? "media",
              onChange: (e) => onCambio("prioridad", e.target.value),
              className: inputClase,
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "baja", children: "Baja" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "media", children: "Media" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "alta", children: "Alta" })
              ]
            }
          )
        ] })
      ] });
    case "vincular_gestion":
      return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2 cursor-pointer", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "checkbox",
            checked: config.autoCrear ?? false,
            onChange: (e) => onCambio("autoCrear", e.target.checked),
            className: "w-3.5 h-3.5 rounded border-2 border-superficie-600 accent-acento-500"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-300", children: "Crear gestion automaticamente si no existe" })
      ] }) });
    case "notificar_usuario":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-[10px] text-superficie-500 uppercase font-medium", children: "Destino" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: config.destino ?? "gestor",
            onChange: (e) => onCambio("destino", e.target.value),
            className: inputClase,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "gestor", children: "Gestor asignado" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "cliente", children: "Cliente" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "ambos", children: "Ambos" })
            ]
          }
        )
      ] });
    case "marcar_urgente":
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-[10px] text-superficie-500 uppercase font-medium", children: "Nivel de urgencia" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: config.nivel ?? "alta",
            onChange: (e) => onCambio("nivel", e.target.value),
            className: inputClase,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "baja", children: "Baja" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "media", children: "Media" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "alta", children: "Alta" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "critica", children: "Critica" })
            ]
          }
        )
      ] });
    default:
      return null;
  }
}
function obtenerConfigDefault(tipo) {
  switch (tipo) {
    case "crear_evento_calendario":
      return { titulo: "Aviso {organismo} - {titular}", diasAnticipacion: 2 };
    case "crear_tarea":
      return { titulo: "Revisar: {asunto}", prioridad: "media" };
    case "vincular_gestion":
      return { autoCrear: false };
    case "notificar_usuario":
      return { destino: "gestor" };
    case "marcar_urgente":
      return { nivel: "alta" };
    default:
      return {};
  }
}
function TabReglasClasificacion() {
  const [reglas, setReglas] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [modalNueva, setModalNueva] = reactExports.useState(false);
  const [modalAcciones, setModalAcciones] = reactExports.useState(null);
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarReglasApi({ limite: 100 });
      setReglas(resultado.datos);
    } catch {
      setError("Error al cargar reglas");
    } finally {
      setCargando(false);
    }
  }, []);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  async function toggleActiva(regla) {
    try {
      await actualizarReglaApi(regla.id, { activa: !regla.activa });
      cargar();
    } catch {
      setError("Error al actualizar regla");
    }
  }
  async function eliminar(id) {
    try {
      await eliminarReglaApi(id);
      cargar();
    } catch {
      setError("Error al eliminar regla");
    }
  }
  const ETIQUETAS_TIPO = {
    remitente_exacto: "Remitente exacto",
    dominio: "Dominio",
    cuenta_origen: "Cuenta origen",
    asunto_contiene: "Asunto contiene"
  };
  const ETIQUETAS_ACCION = {
    clasificar: { texto: "Clasificar", clase: "bg-emerald-500/10 text-emerald-400" },
    ignorar: { texto: "Ignorar", clase: "bg-red-500/10 text-red-400" },
    archivar: { texto: "Archivar", clase: "bg-blue-500/10 text-blue-400" }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-superficie-400", children: [
        reglas.length,
        " reglas configuradas"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalNueva(true),
          className: "flex items-center gap-2 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Nueva regla"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error
    ] }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-12", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Tipo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Valor" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Cliente/Gestion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Accion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Prioridad" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Usos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Activa" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-4 py-3 text-xs font-semibold text-superficie-500 uppercase", children: "Acciones" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: reglas.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 8, className: "px-4 py-12 text-center text-superficie-500", children: "No hay reglas configuradas" }) }) : reglas.map((regla) => {
        const accion = ETIQUETAS_ACCION[regla.accion] ?? {
          texto: regla.accion,
          clase: "bg-gray-500/10 text-gray-400"
        };
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-superficie-300 text-xs", children: ETIQUETAS_TIPO[regla.tipo] ?? regla.tipo }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-superficie-200 font-mono text-xs max-w-[200px] truncate", children: regla.valor }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-superficie-400 text-xs", children: regla.nombreCliente ?? regla.nombreGestion ?? "---" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-1.5 py-0.5 rounded text-[10px] font-medium ${accion.clase}`, children: accion.texto }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-superficie-400 text-xs", children: regla.prioridad }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-superficie-400 text-xs", children: regla.vecesAplicada }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => toggleActiva(regla),
              className: `relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${regla.activa ? "bg-acento-500" : "bg-superficie-600"}`,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                "span",
                {
                  className: `inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${regla.activa ? "translate-x-4" : "translate-x-0.5"}`
                }
              )
            }
          ) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center gap-1", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => setModalAcciones(regla),
                className: `p-1 rounded transition-colors ${(regla.accionesAutomaticas ?? []).length > 0 ? "text-amber-400 hover:bg-amber-500/10" : "text-superficie-500 hover:text-superficie-300 hover:bg-white/[0.03]"}`,
                title: `Acciones (${(regla.accionesAutomaticas ?? []).length})`,
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "w-3.5 h-3.5" })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => eliminar(regla.id),
                className: "p-1 text-superficie-500 hover:text-red-400 rounded",
                title: "Eliminar regla",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3.5 h-3.5" })
              }
            )
          ] }) })
        ] }, regla.id);
      }) })
    ] }) }),
    modalNueva && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalNuevaRegla,
      {
        onCerrar: () => setModalNueva(false),
        onCreada: () => {
          setModalNueva(false);
          cargar();
        }
      }
    ),
    modalAcciones && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalReglaAcciones,
      {
        regla: modalAcciones,
        onCerrar: () => setModalAcciones(null),
        onGuardado: () => {
          setModalAcciones(null);
          cargar();
        }
      }
    )
  ] });
}
function ModalNuevaRegla({
  onCerrar,
  onCreada
}) {
  useEscapeKey(true, onCerrar);
  const [tipo, setTipo] = reactExports.useState("remitente_exacto");
  const [valor, setValor] = reactExports.useState("");
  const [accion, setAccion] = reactExports.useState("clasificar");
  const [prioridad, setPrioridad] = reactExports.useState(100);
  const [gestionId, setGestionId] = reactExports.useState("");
  const [gestionesDisp, setGestionesDisp] = reactExports.useState([]);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState("");
  reactExports.useEffect(() => {
    listarGestionesApi({ limite: 100 }).then((r) => setGestionesDisp(r.gestiones ?? [])).catch(() => {
    });
  }, []);
  async function guardar() {
    if (!valor.trim()) {
      setError("El valor es obligatorio");
      return;
    }
    setGuardando(true);
    setError("");
    try {
      await crearReglaApi({
        tipo,
        valor: valor.trim(),
        accion,
        prioridad,
        gestionId: gestionId || void 0
      });
      onCreada();
    } catch {
      setError("Error al crear regla");
    } finally {
      setGuardando(false);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6 w-full max-w-lg mx-4", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Nueva regla de clasificacion" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Tipo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: tipo,
            onChange: (e) => setTipo(e.target.value),
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "remitente_exacto", children: "Remitente exacto" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "dominio", children: "Dominio" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "asunto_contiene", children: "Asunto contiene" })
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Valor" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: valor,
            onChange: (e) => setValor(e.target.value),
            placeholder: tipo === "remitente_exacto" ? "noreply@aeat.es" : tipo === "dominio" ? "aeat.es" : "Texto en asunto...",
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Accion" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: accion,
              onChange: (e) => setAccion(e.target.value),
              className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "clasificar", children: "Clasificar" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "ignorar", children: "Ignorar" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "archivar", children: "Archivar" })
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Prioridad" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              value: prioridad,
              onChange: (e) => setPrioridad(Number(e.target.value)),
              min: 1,
              max: 9999,
              className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200"
            }
          )
        ] })
      ] }),
      accion === "clasificar" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Asignar a gestion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: gestionId,
            onChange: (e) => setGestionId(e.target.value),
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Sin asignar" }),
              gestionesDisp.map((g) => /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: g.id, children: [
                g.nombre,
                " ",
                g.cliente ? `(${g.cliente})` : ""
              ] }, g.id))
            ]
          }
        )
      ] }),
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-red-400", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 pt-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "flex-1 px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.03]",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: guardar,
            disabled: guardando,
            className: "flex-1 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 disabled:opacity-50",
            children: guardando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin mx-auto" }) : "Crear regla"
          }
        )
      ] })
    ] })
  ] }) });
}
function TabCuentasCorreo() {
  const [cuentas, setCuentas] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [modalNueva, setModalNueva] = reactExports.useState(false);
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarCuentasApi();
      setCuentas(resultado);
    } catch {
      setError("Error al cargar cuentas");
    } finally {
      setCargando(false);
    }
  }, []);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  async function manejarTest(id) {
    try {
      const resultado = await testConexionApi(id);
      if (resultado.conectado) {
        setError(null);
        cargar();
      } else {
        setError(`Test fallido: ${resultado.mensaje}`);
      }
    } catch {
      setError("Error al probar conexion");
    }
  }
  async function manejarPolling(id) {
    try {
      await forzarPollingApi(id);
      setError(null);
      cargar();
    } catch {
      setError("Error al forzar polling");
    }
  }
  async function manejarToggle(cuenta) {
    try {
      await actualizarCuentaApi(cuenta.id, { activo: !cuenta.activo });
      cargar();
    } catch {
      setError("Error al cambiar estado");
    }
  }
  async function manejarEliminar(id) {
    try {
      await eliminarCuentaApi(id);
      cargar();
    } catch {
      setError("Error al eliminar cuenta");
    }
  }
  const COLORES_ESTADO = {
    activa: { icono: Wifi, clase: "text-emerald-400" },
    pausada: { icono: WifiOff, clase: "text-superficie-500" },
    error: { icono: CircleAlert, clase: "text-red-400" },
    desconectada: { icono: WifiOff, clase: "text-amber-400" }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-superficie-400", children: [
        cuentas.length,
        " cuentas configuradas"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalNueva(true),
          className: "flex items-center gap-2 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Nueva cuenta"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error
    ] }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-12", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }) }) : cuentas.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-8 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-10 h-10 text-superficie-600 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "No hay cuentas de correo configuradas" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Conecta tu buzon IMAP para empezar a recibir notificaciones" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid gap-4", children: cuentas.map((cuenta) => {
      const estadoInfo = COLORES_ESTADO[cuenta.estado] ?? COLORES_ESTADO.desconectada;
      const Icono = estadoInfo.icono;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-5 h-5 ${estadoInfo.clase}` }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-medium text-white", children: cuenta.nombre }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-0.5", children: cuenta.email })
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => manejarToggle(cuenta),
              className: `relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${cuenta.activo ? "bg-acento-500" : "bg-superficie-600"}`,
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                "span",
                {
                  className: `inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${cuenta.activo ? "translate-x-4" : "translate-x-0.5"}`
                }
              )
            }
          ) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4 mt-4 text-xs text-superficie-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
            "Intervalo: ",
            cuenta.intervaloPollingSegundos,
            "s"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
            "Ultimo polling:",
            " ",
            cuenta.ultimoPolling ? new Date(cuenta.ultimoPolling).toLocaleString("es-ES") : "Nunca"
          ] })
        ] }),
        cuenta.errorMensaje && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-red-400 mt-2", children: cuenta.errorMensaje }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mt-4 pt-3 border-t border-white/[0.04]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => manejarTest(cuenta.id),
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-superficie-300 bg-superficie-800/50 border border-white/[0.06] rounded-lg hover:bg-white/[0.03]",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "w-3 h-3" }),
                "Test"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => manejarPolling(cuenta.id),
              disabled: !cuenta.activo,
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-superficie-300 bg-superficie-800/50 border border-white/[0.06] rounded-lg hover:bg-white/[0.03] disabled:opacity-30",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-3 h-3" }),
                "Polling"
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => manejarEliminar(cuenta.id),
              className: "p-1.5 text-superficie-500 hover:text-red-400 rounded",
              title: "Eliminar cuenta",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3.5 h-3.5" })
            }
          )
        ] })
      ] }, cuenta.id);
    }) }),
    modalNueva && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalNuevaCuenta,
      {
        onCerrar: () => setModalNueva(false),
        onCreada: () => {
          setModalNueva(false);
          cargar();
        }
      }
    )
  ] });
}
function ModalNuevaCuenta({
  onCerrar,
  onCreada
}) {
  useEscapeKey(true, onCerrar);
  const [nombre, setNombre] = reactExports.useState("");
  const [email, setEmail] = reactExports.useState("");
  const [host, setHost] = reactExports.useState("");
  const [puerto, setPuerto] = reactExports.useState(993);
  const [usuario, setUsuario] = reactExports.useState("");
  const [contrasena, setContrasena] = reactExports.useState("");
  const [usarTls, setUsarTls] = reactExports.useState(true);
  const [mostrarContrasena, setMostrarContrasena] = reactExports.useState(false);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState("");
  async function guardar() {
    if (!nombre.trim() || !email.trim() || !host.trim() || !usuario.trim() || !contrasena.trim()) {
      setError("Todos los campos son obligatorios");
      return;
    }
    setGuardando(true);
    setError("");
    try {
      await crearCuentaApi({ nombre, email, host, puerto, usuario, contrasena, usarTls });
      onCreada();
    } catch {
      setError("Error al crear cuenta");
    } finally {
      setGuardando(false);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Nueva cuenta de correo IMAP" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Nombre" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: nombre,
            onChange: (e) => setNombre(e.target.value),
            placeholder: "Email trabajo Javier",
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Email" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "email",
            value: email,
            onChange: (e) => setEmail(e.target.value),
            placeholder: "javier@asesoria.es",
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-3 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "col-span-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Servidor IMAP" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: host,
              onChange: (e) => setHost(e.target.value),
              placeholder: "imap.asesoria.es",
              className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Puerto" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              value: puerto,
              onChange: (e) => setPuerto(Number(e.target.value)),
              className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200"
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Usuario" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: usuario,
            onChange: (e) => setUsuario(e.target.value),
            placeholder: "javier@asesoria.es",
            className: "w-full px-3 py-2 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200 placeholder-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Contrasena" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: mostrarContrasena ? "text" : "password",
              value: contrasena,
              onChange: (e) => setContrasena(e.target.value),
              className: "w-full px-3 py-2 pr-10 text-sm bg-superficie-800/50 border border-white/[0.06] rounded-lg text-superficie-200"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              type: "button",
              onClick: () => setMostrarContrasena(!mostrarContrasena),
              className: "absolute right-2 top-1/2 -translate-y-1/2 text-superficie-500 hover:text-superficie-300",
              children: mostrarContrasena ? /* @__PURE__ */ jsxRuntimeExports.jsx(EyeOff, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-4 h-4" })
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "button",
            onClick: () => setUsarTls(!usarTls),
            className: `relative inline-flex h-5 w-9 items-center rounded-full transition-colors cursor-pointer ${usarTls ? "bg-acento-500" : "bg-superficie-600"}`,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: `inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${usarTls ? "translate-x-4" : "translate-x-0.5"}`
              }
            )
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-300", children: "Usar TLS/SSL" })
      ] }),
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-red-400", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 pt-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "flex-1 px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.03]",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: guardar,
            disabled: guardando,
            className: "flex-1 px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 disabled:opacity-50",
            children: guardando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin mx-auto" }) : "Crear cuenta"
          }
        )
      ] })
    ] })
  ] }) });
}
function TabOrganismos() {
  const [organismos, setOrganismos] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [modalAbierto, setModalAbierto] = reactExports.useState(false);
  const [editando, setEditando] = reactExports.useState(null);
  const [nombre, setNombre] = reactExports.useState("");
  const [codigo, setCodigo] = reactExports.useState("");
  const [dominios, setDominios] = reactExports.useState("");
  const [emails, setEmails] = reactExports.useState("");
  const [guardando, setGuardando] = reactExports.useState(false);
  const cargar = reactExports.useCallback(async () => {
    try {
      setCargando(true);
      const datos = await listarOrganismosApi();
      setOrganismos(datos);
    } catch {
    } finally {
      setCargando(false);
    }
  }, []);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  const abrirCrear = () => {
    setEditando(null);
    setNombre("");
    setCodigo("");
    setDominios("");
    setEmails("");
    setModalAbierto(true);
  };
  const abrirEditar = (org) => {
    setEditando(org);
    setNombre(org.nombre);
    setCodigo(org.codigo);
    setDominios((org.dominiosEmail ?? []).join(", "));
    setEmails((org.emailsConocidos ?? []).join(", "));
    setModalAbierto(true);
  };
  const guardar = async () => {
    if (!nombre.trim() || !codigo.trim()) return;
    setGuardando(true);
    try {
      const dominiosArr = dominios.split(",").map((d) => d.trim()).filter(Boolean);
      const emailsArr = emails.split(",").map((e) => e.trim()).filter(Boolean);
      if (editando) {
        await actualizarOrganismoApi(editando.id, {
          nombre: nombre.trim(),
          codigo: codigo.trim().toUpperCase(),
          dominiosEmail: dominiosArr,
          emailsConocidos: emailsArr
        });
      } else {
        await crearOrganismoApi({
          nombre: nombre.trim(),
          codigo: codigo.trim().toUpperCase(),
          dominiosEmail: dominiosArr,
          emailsConocidos: emailsArr
        });
      }
      setModalAbierto(false);
      cargar();
    } catch {
    } finally {
      setGuardando(false);
    }
  };
  const eliminar = async (id) => {
    if (!confirm("Eliminar este organismo?")) return;
    try {
      await eliminarOrganismoApi(id);
      cargar();
    } catch {
    }
  };
  const toggleActivo = async (org) => {
    try {
      await actualizarOrganismoApi(org.id, { activo: !org.activo });
      cargar();
    } catch {
    }
  };
  const filtrados = organismos.filter(
    (o) => !busqueda || o.nombre.toLowerCase().includes(busqueda.toLowerCase()) || o.codigo.toLowerCase().includes(busqueda.toLowerCase())
  );
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-12", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "h-6 w-6 animate-spin text-blue-400" }) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-xs", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            placeholder: "Buscar organismo...",
            value: busqueda,
            onChange: (e) => setBusqueda(e.target.value),
            className: "w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: abrirCrear,
          className: "flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "h-4 w-4" }),
            "Nuevo"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "bg-gray-800/50 border border-gray-700 rounded-lg overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-gray-700 text-gray-400", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 font-medium", children: "Organismo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 font-medium", children: "Codigo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 font-medium", children: "Dominios" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center px-4 py-3 font-medium", children: "Detecciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center px-4 py-3 font-medium", children: "Activo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right px-4 py-3 font-medium", children: "Acciones" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { children: filtrados.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 6, className: "text-center py-8 text-gray-500", children: "No hay organismos configurados" }) }) : filtrados.map((org) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-gray-700/50 hover:bg-gray-800/80", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "h-4 w-4 text-blue-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-white font-medium", children: org.nombre })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-300 font-mono", children: org.codigo }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-1", children: [
          (org.dominiosEmail ?? []).slice(0, 3).map((d) => /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 bg-gray-700/50 rounded text-xs text-gray-400", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Globe, { className: "h-3 w-3" }),
            d
          ] }, d)),
          (org.dominiosEmail ?? []).length > 3 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-gray-500", children: [
            "+",
            (org.dominiosEmail ?? []).length - 3
          ] })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-300", children: org.vecesDetectado ?? 0 }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => toggleActivo(org), className: "text-gray-400 hover:text-white", children: org.activo ? /* @__PURE__ */ jsxRuntimeExports.jsx(ToggleRight, { className: "h-5 w-5 text-green-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ToggleLeft, { className: "h-5 w-5 text-gray-500" }) }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-right", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => abrirEditar(org),
              className: "p-1.5 text-gray-400 hover:text-blue-400 hover:bg-gray-700 rounded transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(Pencil, { className: "h-4 w-4" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => eliminar(org.id),
              className: "p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "h-4 w-4" })
            }
          )
        ] }) })
      ] }, org.id)) })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-gray-500", children: "Los organismos se detectan automaticamente al recibir emails. Puedes agregar o editar manualmente." }),
    modalAbierto && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 flex items-center justify-center z-50", onClick: () => setModalAbierto(false), children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-xl", onClick: (e) => e.stopPropagation(), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-lg font-semibold text-white", children: editando ? "Editar organismo" : "Nuevo organismo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setModalAbierto(false), className: "text-gray-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "h-5 w-5" }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm text-gray-400 mb-1", children: "Nombre" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: nombre,
              onChange: (e) => setNombre(e.target.value),
              placeholder: "Agencia Tributaria",
              className: "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm text-gray-400 mb-1", children: "Codigo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: codigo,
              onChange: (e) => setCodigo(e.target.value),
              placeholder: "AEAT",
              className: "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500 uppercase"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "block text-sm text-gray-400 mb-1", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Globe, { className: "inline h-3.5 w-3.5 mr-1" }),
            "Dominios email (separados por coma)"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: dominios,
              onChange: (e) => setDominios(e.target.value),
              placeholder: "aeat.es, agenciatributaria.gob.es",
              className: "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "block text-sm text-gray-400 mb-1", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "inline h-3.5 w-3.5 mr-1" }),
            "Emails conocidos (opcional, separados por coma)"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: emails,
              onChange: (e) => setEmails(e.target.value),
              placeholder: "notificaciones@aeat.es",
              className: "w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3 mt-6", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setModalAbierto(false),
            className: "px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: guardar,
            disabled: guardando || !nombre.trim() || !codigo.trim(),
            className: "flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors",
            children: [
              guardando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "h-4 w-4 animate-spin" }),
              editando ? "Guardar" : "Crear"
            ]
          }
        )
      ] })
    ] }) })
  ] });
}
const TABS = [
  { id: "bandeja", label: "Bandeja", icono: Inbox },
  { id: "reglas", label: "Reglas", icono: BookOpen },
  { id: "organismos", label: "Organismos", icono: Building2 },
  { id: "cuentas", label: "Cuentas", icono: Settings2 }
];
function PaginaBandejaInteligente() {
  const [tab, setTab] = reactExports.useState("bandeja");
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Inbox, { className: "w-5 h-5 text-acento-400" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Bandeja inteligente" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1 border-b border-white/[0.06] pb-px", children: TABS.map(({ id, label, icono: Icono }) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => setTab(id),
        className: `flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors ${tab === id ? "bg-acento-500/10 text-acento-400 border-b-2 border-acento-500" : "text-superficie-400 hover:text-superficie-200 hover:bg-white/[0.03]"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4 h-4" }),
          label
        ]
      },
      id
    )) }),
    tab === "bandeja" && /* @__PURE__ */ jsxRuntimeExports.jsx(TabBandejaEmails, {}),
    tab === "reglas" && /* @__PURE__ */ jsxRuntimeExports.jsx(TabReglasClasificacion, {}),
    tab === "cuentas" && /* @__PURE__ */ jsxRuntimeExports.jsx(TabCuentasCorreo, {}),
    tab === "organismos" && /* @__PURE__ */ jsxRuntimeExports.jsx(TabOrganismos, {})
  ] });
}
export {
  PaginaBandejaInteligente
};
