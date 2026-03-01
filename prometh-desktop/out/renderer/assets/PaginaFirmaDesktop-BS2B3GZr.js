import { r as reactExports, j as jsxRuntimeExports, o as Upload, aa as PenLine, f as CircleCheckBig, a as Shield, Z as Zap, q as FileText } from "./index-DMbE3NR1.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
function PaginaFirmaDesktop() {
  const [modos, setModos] = reactExports.useState([]);
  const [historial, setHistorial] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [progreso, setProgreso] = reactExports.useState(null);
  const [tabActiva, setTabActiva] = reactExports.useState("firmar");
  const [tieneAutoFirma, setTieneAutoFirma] = reactExports.useState(false);
  const api = window.electronAPI;
  const cargar = reactExports.useCallback(async () => {
    if (!api) return;
    try {
      setCargando(true);
      setError(null);
      const [m, hist, af] = await Promise.all([
        api.firma.modosDisponibles(),
        api.firma.obtenerHistorial(),
        api.firma.detectarAutoFirma()
      ]);
      setModos(m);
      setHistorial(hist.documentos ?? []);
      setTieneAutoFirma(af);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando datos");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  reactExports.useEffect(() => {
    if (!api) return;
    api.firma.onProgreso((datos) => {
      setProgreso(datos);
    });
  }, [api]);
  const sincronizarCloud = async () => {
    if (!api) return;
    try {
      await api.firma.sincronizarCloud("", "");
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error sincronizando");
    }
  };
  const pendientesSync = historial.filter((d) => !d.sincronizadoCloud).length;
  if (!api) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Firma digital" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Firma PAdES local y via AutoFirma" })
      ] }),
      pendientesSync > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: sincronizarCloud,
          className: "flex items-center gap-2 px-3 py-2 text-sm font-medium text-superficie-300 bg-superficie-800 hover:bg-superficie-700 rounded-lg border border-white/[0.06] transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-4 h-4" }),
            "Sincronizar (",
            pendientesSync,
            ")"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error })
    ] }),
    progreso && progreso.total > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 cristal rounded-xl p-4 border border-acento-500/30 bg-acento-500/5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-400 animate-spin" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm font-medium text-white", children: [
          "Firmando: ",
          progreso.actual
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-400 ml-auto", children: [
          progreso.completados,
          "/",
          progreso.total
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-full bg-superficie-800 rounded-full h-1.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: "bg-acento-500 h-1.5 rounded-full transition-all duration-300",
          style: { width: `${Math.round(progreso.completados / progreso.total * 100)}%` }
        }
      ) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5 mb-4", children: [
      { id: "firmar", etiqueta: "Modos de firma" },
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
    !cargando && tabActiva === "firmar" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid gap-4 sm:grid-cols-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-5 border border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-acento-500/10 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(PenLine, { className: "w-5 h-5 text-acento-400" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white", children: "Firma PAdES local" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Con certificado P12/PFX del disco" })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2 text-xs text-superficie-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "• Firma PAdES (ETSI.CAdES.detached)" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "• No requiere software externo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "• Soporta firma batch (multiples PDFs)" })
        ] }),
        modos.includes("local") && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 mt-3 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-3 h-3" }),
          " Disponible"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-5 border border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Shield, { className: "w-5 h-5 text-blue-400" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white", children: "AutoFirma" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Protocolo afirma:// del Ministerio" })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2 text-xs text-superficie-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "• Firma con certificado del almacen Windows" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "• Aislamiento de certificado automatico" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "• Compatible con sedes electronicas" })
        ] }),
        tieneAutoFirma ? /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 mt-3 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-3 h-3" }),
          " Instalado"
        ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 mt-3 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "w-3 h-3" }),
          " No detectado"
        ] })
      ] })
    ] }),
    !cargando && tabActiva === "historial" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "No hay firmas registradas" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: historial.slice().reverse().slice(0, 50).map((doc) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-4 border border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-9 h-9 rounded-lg bg-superficie-800 flex items-center justify-center shrink-0", children: /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4 text-superficie-400" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white truncate", children: doc.rutaPdfFirmado.split(/[\\/]/).pop() }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mt-1 text-xs text-superficie-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: doc.modo === "local" ? "PAdES local" : "AutoFirma" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: new Date(doc.fechaFirma).toLocaleString("es-ES") }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: doc.razon })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-2 shrink-0", children: doc.sincronizadoCloud ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-emerald-400", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-4 h-4" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-amber-400", title: "Pendiente de sincronizar", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-4 h-4" }) }) })
    ] }) }, doc.id)) }) })
  ] });
}
export {
  PaginaFirmaDesktop
};
