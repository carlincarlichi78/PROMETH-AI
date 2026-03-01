import { c as createLucideIcon, r as reactExports, j as jsxRuntimeExports, F as FolderOpen, S as ShieldCheck, n as ChevronDown, f as CircleCheckBig, D as Download, q as FileText, E as Eye, I as CircleX, ah as CircleHelp } from "./index-DMbE3NR1.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { H as HardDrive } from "./hard-drive-B8fvoTAs.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const BadgeCheck = createLucideIcon("BadgeCheck", [
  [
    "path",
    {
      d: "M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z",
      key: "3c2336"
    }
  ],
  ["path", { d: "m9 12 2 2 4-4", key: "dzmm74" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Bug = createLucideIcon("Bug", [
  ["path", { d: "m8 2 1.88 1.88", key: "fmnt4t" }],
  ["path", { d: "M14.12 3.88 16 2", key: "qol33r" }],
  ["path", { d: "M9 7.13v-1a3.003 3.003 0 1 1 6 0v1", key: "d7y7pr" }],
  [
    "path",
    {
      d: "M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6",
      key: "xs1cw7"
    }
  ],
  ["path", { d: "M12 20v-9", key: "1qisl0" }],
  ["path", { d: "M6.53 9C4.6 8.8 3 7.1 3 5", key: "32zzws" }],
  ["path", { d: "M6 13H2", key: "82j7cp" }],
  ["path", { d: "M3 21c0-2.1 1.7-3.9 3.8-4", key: "4p0ekp" }],
  ["path", { d: "M20.97 5c0 2.1-1.6 3.8-3.5 4", key: "18gb23" }],
  ["path", { d: "M22 13h-4", key: "1jl80f" }],
  ["path", { d: "M17.2 17c2.1.1 3.8 1.9 3.8 4", key: "k3fwyw" }]
]);
function extraerNombreCert(subject) {
  const cn = subject.match(/CN=([^,]+)/i);
  return cn ? cn[1].trim() : subject.substring(0, 40);
}
function formatearTamano(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
const TIPOS_CERTIFICADO_SS = [
  { valor: "1", etiqueta: "Generico" },
  { valor: "2", etiqueta: "Contratacion sector publico" },
  { valor: "3", etiqueta: "Obtencion subvenciones" },
  { valor: "4", etiqueta: "Suscripcion convenios" },
  { valor: "5", etiqueta: "Cesiones de credito" },
  { valor: "6", etiqueta: "Pagos por cuenta de otro" },
  { valor: "7", etiqueta: "Concurrencia con AEAT" }
];
function PaginaDescargaDocumentos() {
  const [catalogo, setCatalogo] = reactExports.useState([]);
  const [historial, setHistorial] = reactExports.useState([]);
  const [certsLocales, setCertsLocales] = reactExports.useState([]);
  const [certSeleccionado, setCertSeleccionado] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [descargando, setDescargando] = reactExports.useState(null);
  const [tabActiva, setTabActiva] = reactExports.useState("catalogo");
  const [seleccionados, setSeleccionados] = reactExports.useState([]);
  const [descargandoBatch, setDescargandoBatch] = reactExports.useState(false);
  const [docActualBatch, setDocActualBatch] = reactExports.useState(null);
  const [progresoBatch, setProgresoBatch] = reactExports.useState({ actual: 0, total: 0 });
  const [archivos, setArchivos] = reactExports.useState([]);
  const [estadisticas, setEstadisticas] = reactExports.useState({ totalArchivos: 0, tamanoTotal: 0, debugCount: 0 });
  const [cargandoArchivos, setCargandoArchivos] = reactExports.useState(false);
  const [ultimosResultados, setUltimosResultados] = reactExports.useState({});
  const [tipoCertSS, setTipoCertSS] = reactExports.useState("1");
  const [emailCirbe, setEmailCirbe] = reactExports.useState("");
  const [fechaNacCirbe, setFechaNacCirbe] = reactExports.useState("");
  const [categoriasAbiertas, setCategoriasAbiertas] = reactExports.useState(/* @__PURE__ */ new Set());
  const api = window.electronAPI;
  const cargar = reactExports.useCallback(async () => {
    if (!api) return;
    try {
      setCargando(true);
      setError(null);
      const [cat, hist, certs, activo, ultimos] = await Promise.all([
        api.documentales.obtenerCatalogo(),
        api.documentales.obtenerHistorial(),
        api.certs.listarInstalados(),
        api.certs.obtenerActivo(),
        api.documentales.ultimosResultados()
      ]);
      setCatalogo(cat);
      setHistorial(hist);
      setCertsLocales(certs);
      setUltimosResultados(ultimos);
      const portales = new Set(cat.map((d) => d.portal || "General"));
      setCategoriasAbiertas(portales);
      if (activo) {
        setCertSeleccionado(activo);
      } else if (certs.length === 1) {
        setCertSeleccionado(certs[0].serialNumber);
        api.certs.activar(certs[0].serialNumber).catch(() => {
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando datos");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  const cargarArchivos = reactExports.useCallback(async () => {
    if (!api || !certSeleccionado) return;
    try {
      setCargandoArchivos(true);
      const [arch, stats] = await Promise.all([
        api.documentales.listarArchivos(certSeleccionado),
        api.documentales.estadisticasCarpeta(certSeleccionado)
      ]);
      setArchivos(arch);
      setEstadisticas(stats);
    } catch {
      setArchivos([]);
      setEstadisticas({ totalArchivos: 0, tamanoTotal: 0, debugCount: 0 });
    } finally {
      setCargandoArchivos(false);
    }
  }, [api, certSeleccionado]);
  reactExports.useEffect(() => {
    if (tabActiva === "archivos") cargarArchivos();
  }, [tabActiva, cargarArchivos]);
  const seleccionarCert = async (serial) => {
    if (!api) return;
    setCertSeleccionado(serial);
    setSeleccionados([]);
    await api.certs.activar(serial);
  };
  const descargarDocumento = async (tipo) => {
    if (!api) return;
    try {
      setDescargando(tipo);
      setError(null);
      if (!certSeleccionado) {
        setError("Selecciona un certificado digital para descargar documentos.");
        return;
      }
      if (tipo === "SOLICITUD_CIRBE") {
        if (!emailCirbe.trim()) {
          setError("Introduce el email donde recibiras el informe CIRBE.");
          return;
        }
        if (!fechaNacCirbe.trim()) {
          setError("Introduce la fecha de nacimiento (dd/mm/aaaa) para la solicitud CIRBE.");
          return;
        }
      }
      let datosExtra;
      if (tipo === "DEUDAS_SS" && tipoCertSS !== "1") {
        datosExtra = { tipoCertificado: tipoCertSS };
      } else if (tipo === "SOLICITUD_CIRBE") {
        datosExtra = { email: emailCirbe.trim(), fechaNacimiento: fechaNacCirbe.trim() };
      }
      await api.documentales.descargarDocumento(tipo, certSeleccionado, datosExtra);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error descargando documento");
    } finally {
      setDescargando(null);
    }
  };
  const descargarSeleccionados = async () => {
    if (!api || !certSeleccionado || seleccionados.length === 0) return;
    try {
      setDescargandoBatch(true);
      setError(null);
      setProgresoBatch({ actual: 0, total: seleccionados.length });
      for (let i = 0; i < seleccionados.length; i++) {
        setDocActualBatch(seleccionados[i]);
        setProgresoBatch({ actual: i + 1, total: seleccionados.length });
        let datosExtraBatch;
        if (seleccionados[i] === "DEUDAS_SS" && tipoCertSS !== "1") {
          datosExtraBatch = { tipoCertificado: tipoCertSS };
        } else if (seleccionados[i] === "SOLICITUD_CIRBE" && emailCirbe.trim()) {
          datosExtraBatch = { email: emailCirbe.trim(), fechaNacimiento: fechaNacCirbe.trim() };
        }
        await api.documentales.descargarDocumento(seleccionados[i], certSeleccionado, datosExtraBatch);
      }
      setSeleccionados([]);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error en descarga masiva");
    } finally {
      setDescargandoBatch(false);
      setDocActualBatch(null);
    }
  };
  const toggleSeleccion = (id) => {
    setSeleccionados(
      (prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };
  const toggleTodos = () => {
    if (seleccionados.length === catalogo.length) {
      setSeleccionados([]);
    } else {
      setSeleccionados(catalogo.map((d) => d.id));
    }
  };
  const toggleCategoria = (cat) => {
    setCategoriasAbiertas((prev) => {
      const nuevo = new Set(prev);
      if (nuevo.has(cat)) {
        nuevo.delete(cat);
      } else {
        nuevo.add(cat);
      }
      return nuevo;
    });
  };
  const abrirCarpeta = async () => {
    if (!api) return;
    try {
      setError(null);
      const res = await api.documentales.abrirCarpeta(certSeleccionado ?? void 0);
      if (res && !res.exito) {
        setError(res.error || "No se pudo abrir la carpeta");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error abriendo carpeta");
    }
  };
  const limpiarHistorial = async () => {
    if (!api) return;
    await api.documentales.limpiarHistorial();
    setHistorial([]);
  };
  const eliminarArchivo = async (ruta) => {
    if (!api) return;
    const res = await api.documentales.eliminarArchivo(ruta);
    if (res.exito) {
      await cargarArchivos();
    } else {
      setError(res.error || "Error eliminando archivo");
    }
  };
  const limpiarDebug = async () => {
    if (!api || !certSeleccionado) return;
    const res = await api.documentales.limpiarDebug(certSeleccionado);
    if (res.exito) {
      await cargarArchivos();
    }
  };
  const abrirArchivo = async (ruta) => {
    if (!api) return;
    const res = await api.documentales.abrirArchivo(ruta);
    if (!res.exito) {
      setError(res.error || "Error abriendo archivo");
    }
  };
  const renderizarEstado = (doc) => {
    const ultimo = ultimosResultados[doc.id];
    if (ultimo) {
      const fechaFormateada = new Date(ultimo.fecha).toLocaleString("es-ES");
      if (ultimo.exito) {
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: "inline-flex items-center gap-1 text-emerald-400 shrink-0",
            title: `Ultima descarga exitosa: ${fechaFormateada}`,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-4 h-4" })
          }
        );
      }
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "span",
        {
          className: "inline-flex items-center gap-1 text-red-400 shrink-0",
          title: `Ultimo error: ${ultimo.error ?? "Error desconocido"} (${fechaFormateada})`,
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-4 h-4" })
        }
      );
    }
    switch (doc.estadoVerificacion) {
      case "VERIFICADO":
        return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center gap-1 text-acento-400 shrink-0", title: "Scraper verificado", children: /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeCheck, { className: "w-4 h-4" }) });
      case "NO_FUNCIONA":
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: "inline-flex items-center gap-1 text-red-400 shrink-0",
            title: doc.notaVerificacion ?? "Este scraper no funciona actualmente",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-4 h-4" })
          }
        );
      case "NO_PROBADO":
      default:
        return /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: "inline-flex items-center gap-1 text-superficie-500 shrink-0",
            title: doc.notaVerificacion ?? "No probado todavia",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleHelp, { className: "w-4 h-4" })
          }
        );
    }
  };
  const categorias = catalogo.reduce((acc, doc) => {
    const cat = doc.portal || "General";
    return { ...acc, [cat]: [...acc[cat] ?? [], doc] };
  }, {});
  if (!api) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Descarga de documentos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Descarga automatizada de documentos de administraciones publicas" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: abrirCarpeta,
          className: "flex items-center gap-2 px-3 py-2 text-sm font-medium text-superficie-300 bg-superficie-800 hover:bg-superficie-700 rounded-lg border border-white/[0.06] transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(FolderOpen, { className: "w-4 h-4" }),
            "Abrir carpeta"
          ]
        }
      )
    ] }),
    certsLocales.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-amber-500/10 border border-amber-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-amber-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-amber-400", children: "No hay certificados digitales instalados. Importa uno desde la pagina de Certificados Locales." })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-3 mb-4 cristal rounded-xl border border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(ShieldCheck, { className: "w-5 h-5 text-acento-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-400", children: "Certificado:" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: certSeleccionado ?? "",
            onChange: (e) => seleccionarCert(e.target.value),
            className: "w-full appearance-none bg-superficie-800 text-white text-sm font-medium rounded-lg px-3 py-2 pr-8 border border-white/[0.08] hover:border-white/[0.15] focus:border-acento-500/50 focus:outline-none transition-colors cursor-pointer",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", disabled: true, children: "Selecciona un certificado..." }),
              certsLocales.map((cert) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: cert.serialNumber, children: extraerNombreCert(cert.subject) }, cert.serialNumber))
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "w-4 h-4 text-superficie-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" })
      ] }),
      certSeleccionado && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-emerald-400 flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-3.5 h-3.5" }),
        " Activo"
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5 mb-4", children: [
      { id: "catalogo", etiqueta: `Catalogo (${catalogo.length})` },
      { id: "archivos", etiqueta: `Archivos (${estadisticas.totalArchivos})` },
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
    !cargando && tabActiva === "catalogo" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-4 p-3 cristal rounded-xl border border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2 text-sm text-superficie-300 cursor-pointer select-none", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "checkbox",
              checked: seleccionados.length === catalogo.length && catalogo.length > 0,
              onChange: toggleTodos,
              className: "rounded border-white/20 bg-superficie-800 text-acento-500 focus:ring-acento-500/30"
            }
          ),
          "Seleccionar todos"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: descargarSeleccionados,
            disabled: seleccionados.length === 0 || descargandoBatch || !certSeleccionado,
            className: "flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-acento-600 hover:bg-acento-500 rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
            children: [
              descargandoBatch ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-4 h-4" }),
              "Descargar seleccionados (",
              seleccionados.length,
              ")"
            ]
          }
        )
      ] }),
      descargandoBatch && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 p-3 cristal rounded-xl border border-acento-500/20", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-acento-400", children: [
            "Descargando ",
            progresoBatch.actual,
            "/",
            progresoBatch.total,
            docActualBatch && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-superficie-400 ml-2", children: [
              "— ",
              docActualBatch
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
            Math.round(progresoBatch.actual / progresoBatch.total * 100),
            "%"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-full bg-superficie-800 rounded-full h-1.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: "bg-acento-500 h-1.5 rounded-full transition-all duration-300",
            style: { width: `${progresoBatch.actual / progresoBatch.total * 100}%` }
          }
        ) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-3", children: Object.entries(categorias).map(([categoria, docs]) => {
        const abierta = categoriasAbiertas.has(categoria);
        const selEnCategoria = docs.filter((d) => seleccionados.includes(d.id)).length;
        const verificados = docs.filter((d) => d.estadoVerificacion === "VERIFICADO" || ultimosResultados[d.id]?.exito).length;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl border border-white/[0.06] overflow-hidden", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => toggleCategoria(categoria),
              className: "w-full flex items-center gap-2 px-4 py-2.5 hover:bg-white/[0.02] transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: `w-4 h-4 text-superficie-400 transition-transform ${abierta ? "rotate-90" : ""}` }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-semibold text-superficie-300 uppercase tracking-wide flex-1 text-left", children: categoria }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500 flex items-center gap-2", children: [
                  selEnCategoria > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-acento-400", children: [
                    selEnCategoria,
                    " sel."
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-emerald-400/70", children: [
                    verificados,
                    "/",
                    docs.length
                  ] }),
                  docs.length,
                  " docs"
                ] })
              ]
            }
          ),
          abierta && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "border-t border-white/[0.04]", children: docs.map((doc) => {
            const descargandoEste = descargando === doc.id || docActualBatch === doc.id;
            return /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "div",
              {
                className: "flex items-center gap-3 px-4 py-2 hover:bg-white/[0.02] transition-colors border-b border-white/[0.03] last:border-b-0",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "input",
                    {
                      type: "checkbox",
                      checked: seleccionados.includes(doc.id),
                      onChange: () => toggleSeleccion(doc.id),
                      disabled: descargandoBatch,
                      className: "rounded border-white/20 bg-superficie-800 text-acento-500 focus:ring-acento-500/30 shrink-0"
                    }
                  ),
                  renderizarEstado(doc),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1 min-w-0", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-white", children: doc.nombre }) }),
                  doc.id === "DEUDAS_SS" && /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "select",
                    {
                      value: tipoCertSS,
                      onChange: (e) => setTipoCertSS(e.target.value),
                      className: "text-xs bg-superficie-800 text-superficie-300 border border-white/10 rounded-md px-2 py-1 focus:ring-1 focus:ring-acento-500/30 focus:border-acento-500/30 shrink-0",
                      children: TIPOS_CERTIFICADO_SS.map((t) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: t.valor, children: t.etiqueta }, t.valor))
                    }
                  ),
                  doc.id === "SOLICITUD_CIRBE" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 shrink-0", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "input",
                      {
                        type: "email",
                        placeholder: "Email *",
                        value: emailCirbe,
                        onChange: (e) => setEmailCirbe(e.target.value),
                        className: "w-44 text-xs bg-superficie-800 text-superficie-300 border border-white/10 rounded-md px-2 py-1 placeholder:text-superficie-600 focus:ring-1 focus:ring-acento-500/30 focus:border-acento-500/30"
                      }
                    ),
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "input",
                      {
                        type: "text",
                        placeholder: "Nacimiento dd/mm/aaaa *",
                        value: fechaNacCirbe,
                        onChange: (e) => setFechaNacCirbe(e.target.value),
                        className: "w-44 text-xs bg-superficie-800 text-superficie-300 border border-white/10 rounded-md px-2 py-1 placeholder:text-superficie-600 focus:ring-1 focus:ring-acento-500/30 focus:border-acento-500/30"
                      }
                    )
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsxs(
                    "button",
                    {
                      onClick: () => descargarDocumento(doc.id),
                      disabled: descargandoEste || descargandoBatch,
                      className: "flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-acento-400 bg-acento-500/10 hover:bg-acento-500/20 rounded-md border border-acento-500/20 transition-colors disabled:opacity-50 shrink-0",
                      children: [
                        descargandoEste ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3 h-3 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-3 h-3" }),
                        "Descargar"
                      ]
                    }
                  )
                ]
              },
              doc.id
            );
          }) })
        ] }, categoria);
      }) })
    ] }),
    !cargando && tabActiva === "archivos" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: !certSeleccionado ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(ShieldCheck, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Selecciona un certificado para ver archivos descargados" })
    ] }) : cargandoArchivos ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-500 animate-spin" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between p-3 mb-4 cristal rounded-xl border border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(HardDrive, { className: "w-4 h-4 text-superficie-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-superficie-300", children: [
            estadisticas.totalArchivos,
            " documentos",
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-superficie-500 ml-1", children: [
              "(",
              formatearTamano(estadisticas.tamanoTotal),
              ")"
            ] })
          ] })
        ] }),
        estadisticas.debugCount > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: limpiarDebug,
            className: "flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-amber-400 bg-amber-500/10 hover:bg-amber-500/20 rounded-md border border-amber-500/20 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Bug, { className: "w-3 h-3" }),
              "Limpiar debug (",
              estadisticas.debugCount,
              ")"
            ]
          }
        )
      ] }),
      archivos.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "No hay archivos descargados para este certificado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-600 mt-1", children: "Los documentos descargados apareceran aqui" })
      ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden border border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Archivo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tamano" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Acciones" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: archivos.map((arch) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-2.5", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4 text-red-400 shrink-0" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-white truncate max-w-[300px]", title: arch.nombre, children: arch.nombre })
          ] }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-2.5 text-superficie-400", children: new Date(arch.fecha).toLocaleString("es-ES") }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-2.5 text-superficie-400 text-right font-mono text-xs", children: formatearTamano(arch.tamano) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-2.5 text-right", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-1", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                onClick: () => abrirArchivo(arch.ruta),
                className: "flex items-center gap-1 px-2 py-1 text-xs text-superficie-300 hover:text-white hover:bg-white/[0.05] rounded transition-colors",
                title: "Abrir",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-3 h-3" }),
                  "Abrir"
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => eliminarArchivo(arch.ruta),
                className: "flex items-center gap-1 px-2 py-1 text-xs text-superficie-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors",
                title: "Eliminar",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3 h-3" })
              }
            )
          ] }) })
        ] }, arch.ruta)) })
      ] }) })
    ] }) }),
    !cargando && tabActiva === "historial" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "No hay descargas registradas" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
          "Ultimos ",
          Math.min(historial.length, 500),
          " registros (max 500)"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: limpiarHistorial,
            className: "flex items-center gap-1.5 px-2 py-1 text-xs text-superficie-500 hover:text-red-400 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3 h-3" }),
              "Limpiar"
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden border border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Documento" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Certificado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: historial.slice(0, 50).map((reg, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3 text-white", children: reg.tipo }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-5 py-3 text-superficie-400 font-mono text-xs", children: [
            reg.certificadoSerial.slice(0, 12),
            "..."
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3 text-superficie-400", children: new Date(reg.fechaDescarga).toLocaleString("es-ES") }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3", children: reg.exito ? /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 text-emerald-400 text-xs", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-3.5 h-3.5" }),
            " Exitoso"
          ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 text-red-400 text-xs", title: reg.error, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-3.5 h-3.5" }),
            " Error"
          ] }) })
        ] }, `${reg.tipo}-${i}`)) })
      ] }) })
    ] }) })
  ] });
}
export {
  PaginaDescargaDocumentos
};
