import { c as createLucideIcon, z as useAuthStore, r as reactExports, j as jsxRuntimeExports, f as CircleCheckBig, Z as Zap, A as Activity, n as ChevronDown, I as CircleX } from "./index-DMbE3NR1.js";
import { P as Play } from "./play-B9P3AzSW.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { S as Settings2 } from "./settings-2-rsIHKSP7.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CircleMinus = createLucideIcon("CircleMinus", [
  ["circle", { cx: "12", cy: "12", r: "10", key: "1mglay" }],
  ["path", { d: "M8 12h8", key: "1wcyev" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Square = createLucideIcon("Square", [
  ["rect", { width: "18", height: "18", x: "3", y: "3", rx: "2", key: "afitv7" }]
]);
const PORTALES_DISPONIBLES = [
  { id: "SEGURIDAD_SOCIAL", nombre: "Seguridad Social" },
  { id: "AEAT_DIRECTA", nombre: "AEAT Directa" },
  { id: "DGT", nombre: "DGT" },
  { id: "E_NOTUM", nombre: "e-NOTUM" },
  { id: "JUNTA_ANDALUCIA", nombre: "Junta Andalucia" }
];
const DOCUMENTOS_DISPONIBLES = [
  { id: "DEUDAS_AEAT", nombre: "Deudas AEAT", grupo: "AEAT" },
  { id: "DATOS_FISCALES", nombre: "Datos fiscales", grupo: "AEAT" },
  { id: "CERTIFICADOS_IRPF", nombre: "Certificados IRPF", grupo: "AEAT" },
  { id: "CNAE_AUTONOMO", nombre: "CNAE Autonomo", grupo: "AEAT" },
  { id: "IAE_ACTIVIDADES", nombre: "IAE Actividades", grupo: "AEAT" },
  { id: "DEUDAS_SS", nombre: "Deudas SS", grupo: "Seguridad Social" },
  { id: "VIDA_LABORAL", nombre: "Vida laboral", grupo: "Seguridad Social" },
  { id: "CERTIFICADO_INSS", nombre: "Certificado INSS", grupo: "Seguridad Social" },
  { id: "CONSULTA_VEHICULOS", nombre: "Vehiculos", grupo: "Carpeta Ciudadana" },
  { id: "CONSULTA_INMUEBLES", nombre: "Inmuebles", grupo: "Carpeta Ciudadana" },
  { id: "EMPADRONAMIENTO", nombre: "Empadronamiento", grupo: "Carpeta Ciudadana" },
  { id: "CERTIFICADO_PENALES", nombre: "Antecedentes penales", grupo: "Carpeta Ciudadana" },
  { id: "CERTIFICADO_NACIMIENTO", nombre: "Nacimiento", grupo: "Justicia" },
  { id: "APUD_ACTA", nombre: "APUD Acta", grupo: "Justicia" },
  { id: "CERTIFICADO_SEPE", nombre: "Certificado SEPE", grupo: "Otros" }
];
function extraerNombreCert(subject) {
  const match = subject.match(/CN=([^,]+)/);
  return match ? match[1].trim() : subject.slice(0, 30);
}
function formatearDuracion(ms) {
  if (ms < 1e3) return `${ms}ms`;
  const s = Math.round(ms / 1e3);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}
function formatearFecha(iso) {
  return new Date(iso).toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}
function IconoEstado({ estado }) {
  switch (estado) {
    case "COMPLETED":
    case "completado":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-4 h-4 text-emerald-400" });
    case "FAILED":
    case "fallido":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-4 h-4 text-red-400" });
    case "RUNNING":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-500 animate-spin" });
    case "PARTIALLY_COMPLETED":
    case "parcial":
      return /* @__PURE__ */ jsxRuntimeExports.jsx(CircleMinus, { className: "w-4 h-4 text-amber-400" });
    default:
      return /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-4 h-4 text-superficie-500" });
  }
}
function PaginaScrapingDesktop() {
  const { accessToken: token } = useAuthStore();
  const [certs, setCerts] = reactExports.useState([]);
  const [seleccion, setSeleccion] = reactExports.useState([]);
  const [estado, setEstado] = reactExports.useState(null);
  const [config, setConfig] = reactExports.useState(null);
  const [historial, setHistorial] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [ejecutando, setEjecutando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  const [tabActiva, setTabActiva] = reactExports.useState("multicert");
  const [certExpandido, setCertExpandido] = reactExports.useState(null);
  const [toasts, setToasts] = reactExports.useState([]);
  const api = window.electronAPI;
  const apiUrl = window.electronAPI?.isDesktop ? "https://www.carloscanetegomez.dev/certigestor/api" : `${window.location.origin}/certigestor/api`;
  const cargarDatos = reactExports.useCallback(async () => {
    if (!api) return;
    try {
      setCargando(true);
      const [certsLocales, cfg, hist] = await Promise.all([
        api.certs.listarInstalados(),
        api.scraping.obtenerConfig(),
        api.multicert.obtenerHistorial(20)
      ]);
      setCerts(certsLocales);
      setConfig(cfg);
      setHistorial(hist);
      setSeleccion((prev) => {
        if (prev.length > 0) return prev;
        return certsLocales.map((c) => ({
          serial: c.serialNumber,
          thumbprint: c.thumbprint,
          nombre: extraerNombreCert(c.subject),
          seleccionado: false,
          dehu: true,
          portalesNotificaciones: [],
          documentos: []
        }));
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando datos");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);
  reactExports.useEffect(() => {
    if (!api) return;
    api.scraping.onProgreso((datos) => {
      const est = datos;
      setEstado(est);
      setEjecutando(est.status === "RUNNING");
    });
  }, [api]);
  reactExports.useEffect(() => {
    if (!api?.scraping?.onNotificacionesNuevas) return;
    api.scraping.onNotificacionesNuevas((datos) => {
      const id = Date.now();
      setToasts((prev) => [...prev, { id, portal: datos.portal, nuevas: datos.nuevas }]);
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, 6e3);
    });
  }, [api]);
  const iniciar = async () => {
    if (!api || !token) return;
    const certsSeleccionados2 = seleccion.filter((s) => s.seleccionado);
    if (certsSeleccionados2.length === 0) {
      setError("Selecciona al menos un certificado");
      return;
    }
    const configs = certsSeleccionados2.map((s) => ({
      certificadoSerial: s.serial,
      certificadoId: s.serial,
      nombreCert: s.nombre,
      thumbprint: s.thumbprint,
      dehu: s.dehu ? { certificadoSerial: s.serial, estadoAlta: "DESCONOCIDO" } : void 0,
      portalesNotificaciones: s.portalesNotificaciones.length > 0 ? s.portalesNotificaciones : void 0,
      documentos: s.documentos.length > 0 ? s.documentos : void 0
    }));
    try {
      setError(null);
      setEjecutando(true);
      const resultado = await api.multicert.iniciar(configs, apiUrl, token);
      if (!resultado.exito) {
        setError(resultado.error ?? "Error iniciando consulta");
      }
      const hist = await api.multicert.obtenerHistorial(20);
      setHistorial(hist);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error iniciando consulta");
    } finally {
      setEjecutando(false);
    }
  };
  const detener = async () => {
    if (!api) return;
    try {
      await api.multicert.detener();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error deteniendo");
    }
  };
  const guardarConfig = async () => {
    if (!api || !config) return;
    try {
      await api.scraping.configurar(config);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error guardando config");
    }
  };
  const toggleCert = (serial) => {
    setSeleccion(
      (prev) => prev.map(
        (s) => s.serial === serial ? { ...s, seleccionado: !s.seleccionado } : s
      )
    );
  };
  const toggleDehu = (serial) => {
    setSeleccion(
      (prev) => prev.map(
        (s) => s.serial === serial ? { ...s, dehu: !s.dehu } : s
      )
    );
  };
  const togglePortal = (serial, portal) => {
    setSeleccion(
      (prev) => prev.map((s) => {
        if (s.serial !== serial) return s;
        const tiene = s.portalesNotificaciones.includes(portal);
        return {
          ...s,
          portalesNotificaciones: tiene ? s.portalesNotificaciones.filter((p) => p !== portal) : [...s.portalesNotificaciones, portal]
        };
      })
    );
  };
  const toggleDocumento = (serial, doc) => {
    setSeleccion(
      (prev) => prev.map((s) => {
        if (s.serial !== serial) return s;
        const tiene = s.documentos.includes(doc);
        return {
          ...s,
          documentos: tiene ? s.documentos.filter((d) => d !== doc) : [...s.documentos, doc]
        };
      })
    );
  };
  const seleccionarTodosPortales = (serial) => {
    setSeleccion(
      (prev) => prev.map(
        (s) => s.serial === serial ? { ...s, portalesNotificaciones: PORTALES_DISPONIBLES.map((p) => p.id) } : s
      )
    );
  };
  const seleccionarTodosDocs = (serial) => {
    setSeleccion(
      (prev) => prev.map(
        (s) => s.serial === serial ? { ...s, documentos: DOCUMENTOS_DISPONIBLES.map((d) => d.id) } : s
      )
    );
  };
  if (!api) return null;
  const certsSeleccionados = seleccion.filter((s) => s.seleccionado).length;
  const totalTareas = seleccion.filter((s) => s.seleccionado).reduce(
    (sum, s) => sum + (s.dehu ? 1 : 0) + s.portalesNotificaciones.length + s.documentos.length,
    0
  );
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    toasts.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed top-4 right-4 z-50 flex flex-col gap-2", children: toasts.map((toast) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: "flex items-center gap-3 bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-lg animate-in slide-in-from-right",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "h-5 w-5 shrink-0" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-semibold text-sm", children: "Nueva(s) notificacion(es)" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-emerald-100", children: [
              toast.portal,
              ": ",
              toast.nuevas,
              " nueva(s) recibida(s)"
            ] })
          ] })
        ]
      },
      toast.id
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Scraping multi-certificado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Consulta automatizada de portales publicos para multiples certificados" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: ejecutando ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: detener,
          className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-500 hover:bg-red-600 rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Square, { className: "w-4 h-4" }),
            "Detener"
          ]
        }
      ) : /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: iniciar,
          disabled: cargando || certsSeleccionados === 0,
          className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-acento-500 hover:bg-acento-600 rounded-lg transition-colors disabled:opacity-50",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Play, { className: "w-4 h-4" }),
            "Iniciar (",
            certsSeleccionados,
            " certs, ",
            totalTareas,
            " tareas)"
          ]
        }
      ) })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5 mb-4", children: [
      { id: "multicert", etiqueta: "Multi-certificado", icono: Zap },
      { id: "historial", etiqueta: "Historial", icono: Clock },
      { id: "config", etiqueta: "Configuracion", icono: Settings2 }
    ].map(({ id, etiqueta, icono: Icono }) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => setTabActiva(id),
        className: `flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${tabActiva === id ? "bg-acento-500/10 text-acento-400 border border-acento-500/20" : "text-superficie-400 hover:bg-white/[0.05] border border-transparent"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4 h-4" }),
          etiqueta
        ]
      },
      id
    )) }),
    tabActiva === "multicert" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      estado && ejecutando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-5 border border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Activity, { className: "w-5 h-5 text-acento-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-white", children: "Consultando portales..." }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-400 ml-auto", children: [
            estado.progreso,
            "%"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-full bg-superficie-800 rounded-full h-2 mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "div",
          {
            className: "bg-acento-500 h-2 rounded-full transition-all duration-500",
            style: { width: `${estado.progreso}%` }
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: estado.cadenas.map((cadena) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 px-3 py-2 bg-superficie-800/50 rounded-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(IconoEstado, { estado: cadena.estado }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-white truncate flex-1", children: cadena.nombreCert ?? cadena.certificadoSerial }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-400", children: [
            cadena.bloquesCompletados,
            "/",
            cadena.totalBloques
          ] }),
          cadena.bloques && cadena.bloques.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1", children: cadena.bloques.map((b) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              title: b.descripcion,
              className: `w-2 h-2 rounded-full ${b.estado === "COMPLETED" ? "bg-emerald-400" : b.estado === "FAILED" ? "bg-red-400" : b.estado === "RUNNING" ? "bg-acento-500 animate-pulse" : "bg-superficie-600"}`
            },
            b.id
          )) })
        ] }, cadena.id)) })
      ] }),
      cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-12", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-500 animate-spin" }) }) : certs.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-8 border border-white/[0.06] text-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400", children: "No hay certificados instalados. Instala un certificado desde la pagina de Certificados." }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-3", children: seleccion.map((cert) => {
        const expandido = certExpandido === cert.serial;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: `cristal rounded-xl border transition-colors ${cert.seleccionado ? "border-acento-500/30 bg-acento-500/[0.03]" : "border-white/[0.06]"}`,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "input",
                  {
                    type: "checkbox",
                    checked: cert.seleccionado,
                    onChange: () => toggleCert(cert.serial),
                    className: "w-4 h-4 rounded border-superficie-600 text-acento-500 focus:ring-acento-500/20 bg-superficie-800"
                  }
                ),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white truncate", children: cert.nombre }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 truncate", children: cert.serial })
                ] }),
                cert.seleccionado && /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "button",
                  {
                    onClick: () => setCertExpandido(expandido ? null : cert.serial),
                    className: "text-superficie-400 hover:text-white transition-colors",
                    children: expandido ? /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
                  }
                ),
                cert.seleccionado && !expandido && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-1.5", children: [
                  cert.dehu && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-2 py-0.5 text-[10px] font-medium rounded bg-blue-500/10 text-blue-400", children: "DEHU" }),
                  cert.portalesNotificaciones.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "px-2 py-0.5 text-[10px] font-medium rounded bg-purple-500/10 text-purple-400", children: [
                    cert.portalesNotificaciones.length,
                    " portales"
                  ] }),
                  cert.documentos.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "px-2 py-0.5 text-[10px] font-medium rounded bg-amber-500/10 text-amber-400", children: [
                    cert.documentos.length,
                    " docs"
                  ] })
                ] })
              ] }),
              cert.seleccionado && expandido && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-4 pb-4 space-y-4 border-t border-white/[0.04] pt-4", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "input",
                    {
                      type: "checkbox",
                      checked: cert.dehu,
                      onChange: () => toggleDehu(cert.serial),
                      className: "w-3.5 h-3.5 rounded border-superficie-600 text-blue-500 focus:ring-blue-500/20 bg-superficie-800"
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-white", children: "DEHU (notificaciones electronicas)" })
                ] }) }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-2", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium text-superficie-400 uppercase tracking-wider", children: "Portales de notificaciones" }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "button",
                      {
                        onClick: () => seleccionarTodosPortales(cert.serial),
                        className: "text-[10px] text-acento-400 hover:text-acento-300",
                        children: "Todos"
                      }
                    )
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-2", children: PORTALES_DISPONIBLES.map((portal) => /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "input",
                      {
                        type: "checkbox",
                        checked: cert.portalesNotificaciones.includes(portal.id),
                        onChange: () => togglePortal(cert.serial, portal.id),
                        className: "w-3.5 h-3.5 rounded border-superficie-600 text-purple-500 focus:ring-purple-500/20 bg-superficie-800"
                      }
                    ),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-300", children: portal.nombre })
                  ] }, portal.id)) })
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-2", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium text-superficie-400 uppercase tracking-wider", children: "Documentos a descargar" }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "button",
                      {
                        onClick: () => seleccionarTodosDocs(cert.serial),
                        className: "text-[10px] text-acento-400 hover:text-acento-300",
                        children: "Todos"
                      }
                    )
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-2", children: DOCUMENTOS_DISPONIBLES.map((doc) => /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx(
                      "input",
                      {
                        type: "checkbox",
                        checked: cert.documentos.includes(doc.id),
                        onChange: () => toggleDocumento(cert.serial, doc.id),
                        className: "w-3.5 h-3.5 rounded border-superficie-600 text-amber-500 focus:ring-amber-500/20 bg-superficie-800"
                      }
                    ),
                    /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-300", children: [
                      doc.nombre,
                      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-superficie-600 ml-1", children: [
                        "(",
                        doc.grupo,
                        ")"
                      ] })
                    ] })
                  ] }, doc.id)) })
                ] })
              ] })
            ]
          },
          cert.serial
        );
      }) })
    ] }),
    tabActiva === "historial" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-4", children: historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-8 border border-white/[0.06] text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-8 h-8 text-superficie-600 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400", children: "Sin ejecuciones previas" })
    ] }) : historial.map((h, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-4 border border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-white", children: formatearFecha(h.fecha) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-400", children: formatearDuracion(h.duracionMs) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
            h.totalCadenas,
            " cadenas"
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1.5", children: h.certificados.map((cert, j) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 px-3 py-1.5 bg-superficie-800/50 rounded-lg", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(IconoEstado, { estado: cert.estado }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-white truncate flex-1", children: cert.nombre ?? cert.serial }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-1", children: [
          cert.dominios.dehu && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-1.5 py-0.5 text-[9px] rounded bg-blue-500/10 text-blue-400", children: "DEHU" }),
          cert.dominios.notificaciones && cert.dominios.notificaciones.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "px-1.5 py-0.5 text-[9px] rounded bg-purple-500/10 text-purple-400", children: [
            cert.dominios.notificaciones.length,
            "P"
          ] }),
          cert.dominios.documentos && cert.dominios.documentos.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "px-1.5 py-0.5 text-[9px] rounded bg-amber-500/10 text-amber-400", children: [
            cert.dominios.documentos.length,
            "D"
          ] })
        ] })
      ] }, j)) })
    ] }, i)) }),
    tabActiva === "config" && config && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-5 border border-white/[0.06] space-y-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white", children: "Modo rapido (Fast Mode)" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Ejecuta multiples scrapers en paralelo" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setConfig({ ...config, fastMode: !config.fastMode }),
            className: `relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${config.fastMode ? "bg-acento-500" : "bg-superficie-700"}`,
            children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${config.fastMode ? "translate-x-6" : "translate-x-1"}` })
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm font-medium text-white", children: "Scrapers concurrentes" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-2", children: "Numero maximo de scrapers ejecutandose a la vez" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "number",
            min: 1,
            max: 5,
            value: config.replicas,
            onChange: (e) => setConfig({ ...config, replicas: Number(e.target.value) }),
            className: "w-20 px-3 py-1.5 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white focus:outline-none focus:border-acento-500/40"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm font-medium text-white", children: "Timeout global (ms)" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-2", children: "Tiempo maximo de espera por scraper" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "number",
            min: 5e3,
            max: 12e4,
            step: 5e3,
            value: config.timeoutGlobal,
            onChange: (e) => setConfig({ ...config, timeoutGlobal: Number(e.target.value) }),
            className: "w-28 px-3 py-1.5 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white focus:outline-none focus:border-acento-500/40"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-sm font-medium text-white", children: "Reintentos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-2", children: "Intentos por bloque antes de marcar como fallido" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "number",
            min: 1,
            max: 5,
            value: config.maxReintentos,
            onChange: (e) => setConfig({ ...config, maxReintentos: Number(e.target.value) }),
            className: "w-20 px-3 py-1.5 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white focus:outline-none focus:border-acento-500/40"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: guardarConfig,
          className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-acento-500 hover:bg-acento-600 rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-4 h-4" }),
            "Guardar configuracion"
          ]
        }
      )
    ] })
  ] });
}
export {
  PaginaScrapingDesktop
};
