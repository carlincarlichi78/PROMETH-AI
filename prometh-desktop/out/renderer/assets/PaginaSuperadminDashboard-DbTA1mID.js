import { r as reactExports, u as useNavigate, j as jsxRuntimeExports, R as Building2, U as Users, a as Shield, B as Bell, s as ArrowRight } from "./index-DMbE3NR1.js";
import { o as obtenerMetricasGlobalesApi } from "./superadminServicio-RgYMJlVk.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
function PaginaSuperadminDashboard() {
  const [metricas, setMetricas] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const navigate = useNavigate();
  reactExports.useEffect(() => {
    obtenerMetricasGlobalesApi().then((datos) => {
      setMetricas(datos);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : "Error cargando metricas");
    }).finally(() => setCargando(false));
  }, []);
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center h-64", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-8 h-8 text-acento-400 animate-spin" }) });
  }
  if (error) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400", children: error });
  }
  if (!metricas) return null;
  const kpis = [
    {
      titulo: "Total organizaciones",
      valor: metricas.organizaciones.total,
      subtitulo: null,
      icono: Building2,
      color: "text-blue-400",
      bgColor: "bg-blue-500/10",
      borderColor: "border-blue-500/20"
    },
    {
      titulo: "Total usuarios",
      valor: metricas.usuarios.total,
      subtitulo: `${metricas.usuarios.activos} activos`,
      icono: Users,
      color: "text-emerald-400",
      bgColor: "bg-emerald-500/10",
      borderColor: "border-emerald-500/20"
    },
    {
      titulo: "Total certificados",
      valor: metricas.certificados.total,
      subtitulo: `${metricas.certificados.caducados} caducados`,
      icono: Shield,
      color: "text-purple-400",
      bgColor: "bg-purple-500/10",
      borderColor: "border-purple-500/20"
    },
    {
      titulo: "Total notificaciones",
      valor: metricas.notificaciones.total,
      subtitulo: `${metricas.notificaciones.pendientes} pendientes`,
      icono: Bell,
      color: "text-amber-400",
      bgColor: "bg-amber-500/10",
      borderColor: "border-amber-500/20"
    }
  ];
  const badgesPlan = [
    { plan: "basico", cantidad: metricas.organizaciones.porPlan.basico, color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
    { plan: "profesional", cantidad: metricas.organizaciones.porPlan.profesional, color: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
    { plan: "plus", cantidad: metricas.organizaciones.porPlan.plus, color: "bg-amber-500/10 text-amber-400 border-amber-500/20" }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-gray-100", children: "Panel Superadmin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400 mt-1", children: "Vision global de todas las organizaciones" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4", children: kpis.map((kpi) => {
      const Icono = kpi.icono;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: `rounded-xl ${kpi.bgColor} border ${kpi.borderColor} p-5`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-10 h-10 rounded-lg ${kpi.bgColor} flex items-center justify-center`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-5 h-5 ${kpi.color}` }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-gray-400", children: kpi.titulo })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-3xl font-bold text-gray-100", children: kpi.valor.toLocaleString() }),
            kpi.subtitulo && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400 mt-1", children: kpi.subtitulo })
          ]
        },
        kpi.titulo
      );
    }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-gray-800 border border-gray-700 p-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-gray-100 mb-4", children: "Distribucion por plan" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-3", children: badgesPlan.map((bp) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: `inline-flex items-center gap-2 px-4 py-2 rounded-lg border ${bp.color}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium capitalize", children: bp.plan }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-lg font-bold", children: bp.cantidad })
          ]
        },
        bp.plan
      )) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 sm:grid-cols-2 gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => navigate("/app/superadmin/organizaciones"),
          className: "flex items-center justify-between p-5 rounded-xl bg-gray-800 border border-gray-700 hover:border-gray-600 transition-colors text-left",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "w-5 h-5 text-blue-400" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-100 font-medium", children: "Gestionar organizaciones" })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowRight, { className: "w-5 h-5 text-gray-500" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => navigate("/app/superadmin/usuarios"),
          className: "flex items-center justify-between p-5 rounded-xl bg-gray-800 border border-gray-700 hover:border-gray-600 transition-colors text-left",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Users, { className: "w-5 h-5 text-emerald-400" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-gray-100 font-medium", children: "Usuarios global" })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowRight, { className: "w-5 h-5 text-gray-500" })
          ]
        }
      )
    ] })
  ] });
}
export {
  PaginaSuperadminDashboard
};
