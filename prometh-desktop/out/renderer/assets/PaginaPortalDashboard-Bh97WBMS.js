import { aj as usePortalStore, r as reactExports, j as jsxRuntimeExports, a as Shield, B as Bell, q as FileText, F as FolderOpen } from "./index-DMbE3NR1.js";
import { o as obtenerResumenPortalApi } from "./portalServicio-D-oBBzfH.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
function PaginaPortalDashboard() {
  const { datos } = usePortalStore();
  const [resumen, setResumen] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  reactExports.useEffect(() => {
    const cargar = async () => {
      try {
        const resultado = await obtenerResumenPortalApi();
        setResumen(resultado);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar resumen");
      } finally {
        setCargando(false);
      }
    };
    cargar();
  }, []);
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-20", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando resumen..." })
    ] });
  }
  if (error) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error });
  }
  const kpis = [
    {
      titulo: "Certificados activos",
      valor: resumen?.totalCertificados ?? 0,
      icono: Shield,
      colorIcono: "text-blue-400",
      colorFondo: "bg-blue-500/10",
      colorBorde: "border-blue-500/20"
    },
    {
      titulo: "Notificaciones",
      valor: resumen?.totalNotificaciones ?? 0,
      icono: Bell,
      colorIcono: "text-amber-400",
      colorFondo: "bg-amber-500/10",
      colorBorde: "border-amber-500/20"
    },
    {
      titulo: "Documentos firmados",
      valor: resumen?.totalFirmas ?? 0,
      icono: FileText,
      colorIcono: "text-green-400",
      colorFondo: "bg-green-500/10",
      colorBorde: "border-green-500/20"
    },
    {
      titulo: "Gestiones activas",
      valor: resumen?.totalGestiones ?? 0,
      icono: FolderOpen,
      colorIcono: "text-purple-400",
      colorFondo: "bg-purple-500/10",
      colorBorde: "border-purple-500/20"
    }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "text-xl font-semibold text-white", children: [
        "Bienvenido, ",
        datos?.nombreCliente ?? "Cliente"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Aqui puedes consultar el estado de tus certificados, notificaciones, firmas y gestiones." })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4", children: kpis.map((kpi) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: "cristal rounded-xl p-5",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-3 mb-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-10 h-10 rounded-lg ${kpi.colorFondo} border ${kpi.colorBorde} flex items-center justify-center`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(kpi.icono, { className: `w-5 h-5 ${kpi.colorIcono}` }) }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-2xl font-bold text-white", children: kpi.valor }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-1", children: kpi.titulo })
        ]
      },
      kpi.titulo
    )) })
  ] });
}
export {
  PaginaPortalDashboard
};
