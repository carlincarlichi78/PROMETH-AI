import { c as createLucideIcon, r as reactExports, j as jsxRuntimeExports, v as Check, f as CircleCheckBig, a1 as actualizarBrandingApi, d as apiClient, X, B as Bell, q as FileText, P as Plus, I as CircleX, z as useAuthStore, a2 as useSearchParams, a3 as COMUNIDADES_AUTONOMAS, a4 as NOMBRES_COMUNIDADES, o as Upload, H as obtenerPerfilApi, a5 as obtenerConfiguracionApi, a6 as actualizarConfiguracionApi, a7 as subirLogoApi, a8 as eliminarLogoApi, a9 as actualizarPerfilApi } from "./index-DMbE3NR1.js";
import { obtenerEstadoIntegracionesApi, autorizarGoogleApi, desconectarIntegracionApi, autorizarMicrosoftApi, sincronizarCalendarioApi } from "./integracionesServicio-C-79KoQl.js";
import { d as descartarAutomaticasApi } from "./notificacionesServicio-B3Srptx0.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { M as Mail } from "./mail-BDEpMyrm.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { P as Pencil } from "./pencil-BuwvL_tU.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { S as Send } from "./send-mu2rTZak.js";
import { H as HardDrive } from "./hard-drive-B8fvoTAs.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { C as Calendar } from "./calendar-KREuhz-X.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Image = createLucideIcon("Image", [
  ["rect", { width: "18", height: "18", x: "3", y: "3", rx: "2", ry: "2", key: "1m3agn" }],
  ["circle", { cx: "9", cy: "9", r: "2", key: "af1f0g" }],
  ["path", { d: "m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21", key: "1xmnt7" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const MapPin = createLucideIcon("MapPin", [
  [
    "path",
    {
      d: "M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0",
      key: "1r0f0z"
    }
  ],
  ["circle", { cx: "12", cy: "10", r: "3", key: "ilqhr7" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Palette = createLucideIcon("Palette", [
  ["circle", { cx: "13.5", cy: "6.5", r: ".5", fill: "currentColor", key: "1okk4w" }],
  ["circle", { cx: "17.5", cy: "10.5", r: ".5", fill: "currentColor", key: "f64h9f" }],
  ["circle", { cx: "8.5", cy: "7.5", r: ".5", fill: "currentColor", key: "fotxhn" }],
  ["circle", { cx: "6.5", cy: "12.5", r: ".5", fill: "currentColor", key: "qy21gx" }],
  [
    "path",
    {
      d: "M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z",
      key: "12rzf8"
    }
  ]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const RotateCcw = createLucideIcon("RotateCcw", [
  ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8", key: "1357e3" }],
  ["path", { d: "M3 3v5h5", key: "1xhq8a" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Save = createLucideIcon("Save", [
  [
    "path",
    {
      d: "M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z",
      key: "1c8476"
    }
  ],
  ["path", { d: "M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7", key: "1ydtos" }],
  ["path", { d: "M7 3v4a1 1 0 0 0 1 1h7", key: "t51u73" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Unlink = createLucideIcon("Unlink", [
  [
    "path",
    {
      d: "m18.84 12.25 1.72-1.71h-.02a5.004 5.004 0 0 0-.12-7.07 5.006 5.006 0 0 0-6.95 0l-1.72 1.71",
      key: "yqzxt4"
    }
  ],
  [
    "path",
    {
      d: "m5.17 11.75-1.71 1.71a5.004 5.004 0 0 0 .12 7.07 5.006 5.006 0 0 0 6.95 0l1.71-1.71",
      key: "4qinb0"
    }
  ],
  ["line", { x1: "8", x2: "8", y1: "2", y2: "5", key: "1041cp" }],
  ["line", { x1: "2", x2: "5", y1: "8", y2: "8", key: "14m1p5" }],
  ["line", { x1: "16", x2: "16", y1: "19", y2: "22", key: "rzdirn" }],
  ["line", { x1: "19", x2: "22", y1: "16", y2: "16", key: "ox905f" }]
]);
const COLORES_PREDEFINIDOS = [
  { nombre: "Esmeralda", hex: "#10b981" },
  { nombre: "Azul", hex: "#3b82f6" },
  { nombre: "Violeta", hex: "#8b5cf6" },
  { nombre: "Rosa", hex: "#ec4899" },
  { nombre: "Rojo", hex: "#ef4444" },
  { nombre: "Naranja", hex: "#f97316" },
  { nombre: "Ambar", hex: "#f59e0b" },
  { nombre: "Cian", hex: "#06b6d4" }
];
function SeccionBranding({ planPermite, colorActual, onColorCambiado }) {
  const [colorSeleccionado, setColorSeleccionado] = reactExports.useState(colorActual);
  const [colorHex, setColorHex] = reactExports.useState(colorActual ?? "#10b981");
  const [guardando, setGuardando] = reactExports.useState(false);
  const [mensaje, setMensaje] = reactExports.useState(null);
  const hayCambios = colorSeleccionado !== colorActual;
  const seleccionarColor = (hex) => {
    setColorSeleccionado(hex);
    setColorHex(hex);
    setMensaje(null);
  };
  const manejarInputHex = (valor) => {
    setColorHex(valor);
    if (/^#[0-9a-fA-F]{6}$/.test(valor)) {
      setColorSeleccionado(valor);
      setMensaje(null);
    }
  };
  const guardarColor = async () => {
    setGuardando(true);
    setMensaje(null);
    try {
      const resultado = await actualizarBrandingApi({ colorPrimario: colorSeleccionado });
      onColorCambiado(resultado.colorPrimario);
      setMensaje({ tipo: "exito", texto: "Color actualizado correctamente" });
    } catch {
      setMensaje({ tipo: "error", texto: "Error al actualizar el color" });
    } finally {
      setGuardando(false);
    }
  };
  const restablecerColor = async () => {
    setGuardando(true);
    setMensaje(null);
    try {
      await actualizarBrandingApi({ colorPrimario: null });
      setColorSeleccionado(null);
      setColorHex("#10b981");
      onColorCambiado(null);
      setMensaje({ tipo: "exito", texto: "Color restablecido al predeterminado" });
    } catch {
      setMensaje({ tipo: "error", texto: "Error al restablecer el color" });
    } finally {
      setGuardando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("section", { className: "cristal rounded-xl p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "text-sm font-semibold text-white mb-5 flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Palette, { className: "w-4 h-4 text-acento-400" }),
      "Personalización corporativa"
    ] }),
    !planPermite ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "La personalización de colores está disponible en el plan Plus. Actualiza tu plan para personalizar la apariencia de CertiGestor." }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Personaliza el color principal de la interfaz. Este color se aplicará en todo el panel de control." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-2", children: "Color principal" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2", children: COLORES_PREDEFINIDOS.map(({ nombre, hex }) => /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => seleccionarColor(hex),
            title: nombre,
            className: "relative w-9 h-9 rounded-lg border-2 transition-all hover:scale-110",
            style: {
              backgroundColor: hex,
              borderColor: colorSeleccionado === hex ? "#ffffff" : "transparent"
            },
            children: colorSeleccionado === hex && /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4 text-white absolute inset-0 m-auto" })
          },
          hex
        )) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1.5", children: "Color personalizado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: "w-9 h-9 rounded-lg border border-white/[0.06] shrink-0",
              style: { backgroundColor: colorSeleccionado ?? "#10b981" }
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: colorHex,
              onChange: (e) => manejarInputHex(e.target.value),
              placeholder: "#10b981",
              maxLength: 7,
              className: "flex-1 px-3.5 py-2.5 rounded-lg border text-sm outline-none transition-colors\n                  text-superficie-100 border-white/[0.06] bg-superficie-800/60\n                  hover:border-white/10 focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40\n                  placeholder:text-superficie-600 font-mono"
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-4 rounded-lg border border-white/[0.06] bg-superficie-800/30", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-2", children: "Vista previa" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: "w-8 h-8 rounded-md flex items-center justify-center",
              style: { backgroundColor: colorSeleccionado ?? "#10b981" },
              children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-bold text-white", children: "C" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: "px-3 py-1.5 rounded-md text-sm font-medium text-white",
              style: { backgroundColor: `${colorSeleccionado ?? "#10b981"}20`, color: colorSeleccionado ?? "#10b981" },
              children: "Elemento activo"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: "px-3 py-1.5 rounded-full text-xs font-medium",
              style: { backgroundColor: `${colorSeleccionado ?? "#10b981"}15`, color: colorSeleccionado ?? "#10b981" },
              children: "Badge"
            }
          )
        ] })
      ] }),
      mensaje && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center gap-2 text-sm ${mensaje.tipo === "exito" ? "text-acento-400" : "text-red-400"}`, children: [
        mensaje.tipo === "exito" ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4" }),
        mensaje.texto
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: guardarColor,
            disabled: guardando || !hayCambios,
            className: "flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg\n                bg-acento-500 text-white hover:bg-acento-600 transition-colors\n                disabled:opacity-50 disabled:cursor-not-allowed",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Save, { className: "w-4 h-4" }),
              guardando ? "Guardando..." : "Guardar color"
            ]
          }
        ),
        colorActual && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: restablecerColor,
            disabled: guardando,
            className: "flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg\n                  text-superficie-300 border border-white/[0.06] hover:bg-white/[0.05] transition-colors\n                  disabled:opacity-50 disabled:cursor-not-allowed",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(RotateCcw, { className: "w-4 h-4" }),
              "Restablecer"
            ]
          }
        )
      ] })
    ] })
  ] });
}
async function obtenerConfigEmailApi() {
  const respuesta = await apiClient.get("/emails-config");
  return respuesta.datos;
}
async function actualizarConfigEmailApi(datos) {
  const respuesta = await apiClient.patch("/emails-config", datos);
  return respuesta.datos;
}
async function listarReportesProgramadosApi() {
  const respuesta = await apiClient.get("/emails-config/reportes");
  return respuesta.datos;
}
async function crearReporteProgramadoApi(datos) {
  const respuesta = await apiClient.post("/emails-config/reportes", datos);
  return respuesta.datos;
}
async function actualizarReporteProgramadoApi(id, datos) {
  const respuesta = await apiClient.put(`/emails-config/reportes/${id}`, datos);
  return respuesta.datos;
}
async function eliminarReporteProgramadoApi(id) {
  await apiClient.del(`/emails-config/reportes/${id}`);
}
async function listarHistorialEnviosApi(limite = 20) {
  const respuesta = await apiClient.get(`/emails-config/historial?limite=${limite}`);
  return respuesta.datos;
}
function ModalReporteProgramado({ reporteExistente, onGuardar, onCerrar }) {
  useEscapeKey(true, onCerrar);
  const esEdicion = !!reporteExistente;
  const [nombre, setNombre] = reactExports.useState(reporteExistente?.nombre ?? "");
  const [tipoReporte, setTipoReporte] = reactExports.useState(reporteExistente?.tipoReporte ?? "certificados");
  const [formato, setFormato] = reactExports.useState(reporteExistente?.formato ?? "pdf");
  const [frecuencia, setFrecuencia] = reactExports.useState(reporteExistente?.frecuencia ?? "semanal");
  const [activo, setActivo] = reactExports.useState(reporteExistente?.activo ?? true);
  const [emailInput, setEmailInput] = reactExports.useState("");
  const [destinatarios, setDestinatarios] = reactExports.useState(reporteExistente?.destinatarios ?? []);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState("");
  function agregarEmail() {
    const email = emailInput.trim().toLowerCase();
    if (!email) return;
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError("Email inválido");
      return;
    }
    if (destinatarios.includes(email)) {
      setError("Email ya agregado");
      return;
    }
    if (destinatarios.length >= 10) {
      setError("Máximo 10 destinatarios");
      return;
    }
    setDestinatarios([...destinatarios, email]);
    setEmailInput("");
    setError("");
  }
  function quitarEmail(email) {
    setDestinatarios(destinatarios.filter((e) => e !== email));
  }
  async function guardar() {
    if (!nombre.trim()) {
      setError("Nombre obligatorio");
      return;
    }
    if (destinatarios.length === 0) {
      setError("Agrega al menos un destinatario");
      return;
    }
    setGuardando(true);
    setError("");
    try {
      const datos = {
        nombre: nombre.trim(),
        tipoReporte,
        formato,
        frecuencia,
        destinatarios,
        activo
      };
      if (esEdicion && reporteExistente) {
        await actualizarReporteProgramadoApi(reporteExistente.id, datos);
      } else {
        await crearReporteProgramadoApi(datos);
      }
      onGuardar();
    } catch {
      setError("Error guardando reporte");
    } finally {
      setGuardando(false);
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: esEdicion ? "Editar reporte programado" : "Nuevo reporte programado" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-400 hover:text-white transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 mb-4", children: error }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Nombre del reporte" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: nombre,
            onChange: (e) => setNombre(e.target.value),
            placeholder: "Ej: Reporte semanal de certificados",
            className: "w-full px-3 py-2 rounded-lg border text-sm text-superficie-100\n                border-white/[0.06] bg-superficie-800/60 outline-none placeholder:text-superficie-600\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Tipo de reporte" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: tipoReporte,
              onChange: (e) => setTipoReporte(e.target.value),
              className: "w-full px-3 py-2 rounded-lg border text-sm text-superficie-100\n                  border-white/[0.06] bg-superficie-800/60 outline-none",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "certificados", children: "Certificados" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "notificaciones", children: "Notificaciones" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "auditoria", children: "Auditoría" })
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Formato" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: formato,
              onChange: (e) => setFormato(e.target.value),
              className: "w-full px-3 py-2 rounded-lg border text-sm text-superficie-100\n                  border-white/[0.06] bg-superficie-800/60 outline-none",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "csv", children: "CSV" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "pdf", children: "PDF" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "excel", children: "Excel" })
              ]
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Frecuencia" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: frecuencia,
              onChange: (e) => setFrecuencia(e.target.value),
              className: "w-full px-3 py-2 rounded-lg border text-sm text-superficie-100\n                  border-white/[0.06] bg-superficie-800/60 outline-none",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "diario", children: "Diario" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "semanal", children: "Semanal (lunes)" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "mensual", children: "Mensual (día 1)" })
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-end pb-1", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2 cursor-pointer", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "checkbox",
              checked: activo,
              onChange: (e) => setActivo(e.target.checked),
              className: "rounded border-white/[0.06] bg-superficie-800/60 text-acento-500\n                    focus:ring-acento-500/40"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-200", children: "Activo" })
        ] }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "block text-xs text-superficie-400 mb-1", children: [
          "Destinatarios (",
          destinatarios.length,
          "/10)"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "email",
              value: emailInput,
              onChange: (e) => setEmailInput(e.target.value),
              onKeyDown: (e) => e.key === "Enter" && (e.preventDefault(), agregarEmail()),
              placeholder: "email@ejemplo.com",
              className: "flex-1 px-3 py-2 rounded-lg border text-sm text-superficie-100\n                  border-white/[0.06] bg-superficie-800/60 outline-none placeholder:text-superficie-600\n                  focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              type: "button",
              onClick: agregarEmail,
              className: "px-3 py-2 text-xs font-medium text-acento-400 border border-acento-500/20\n                  rounded-lg hover:bg-acento-500/5 transition-colors",
              children: "Agregar"
            }
          )
        ] }),
        destinatarios.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5 mt-2", children: destinatarios.map((email) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "span",
          {
            className: "inline-flex items-center gap-1 px-2 py-1 text-xs text-superficie-200\n                      bg-superficie-800/60 border border-white/[0.06] rounded-md",
            children: [
              email,
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => quitarEmail(email),
                  className: "text-superficie-400 hover:text-red-400 transition-colors",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3 h-3" })
                }
              )
            ]
          },
          email
        )) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3 mt-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "px-4 py-2 text-sm text-superficie-300 border border-white/[0.06]\n              rounded-lg hover:bg-white/[0.05] transition-colors",
          children: "Cancelar"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: guardar,
          disabled: guardando,
          className: "px-4 py-2 text-sm font-medium text-white bg-acento-500\n              rounded-lg hover:bg-acento-600 transition-colors disabled:opacity-50",
          children: guardando ? "Guardando..." : esEdicion ? "Guardar cambios" : "Crear reporte"
        }
      )
    ] })
  ] }) });
}
function SeccionEmails({ planOrganizacion }) {
  const [config, setConfig] = reactExports.useState(null);
  const [reportes, setReportes] = reactExports.useState([]);
  const [historial, setHistorial] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [modalAbierto, setModalAbierto] = reactExports.useState(false);
  const [reporteEditando, setReporteEditando] = reactExports.useState(null);
  const [error, setError] = reactExports.useState("");
  const esProfesional = planOrganizacion === "profesional" || planOrganizacion === "plus";
  const esPlus = planOrganizacion === "plus";
  reactExports.useEffect(() => {
    cargarDatos();
  }, []);
  async function cargarDatos() {
    try {
      setCargando(true);
      const configData = await obtenerConfigEmailApi();
      setConfig(configData);
      if (esPlus) {
        const reportesData = await listarReportesProgramadosApi();
        setReportes(reportesData);
      }
      if (esProfesional) {
        const historialData = await listarHistorialEnviosApi();
        setHistorial(historialData);
      }
    } catch {
      setError("Error cargando configuración de emails");
    } finally {
      setCargando(false);
    }
  }
  async function actualizarConfig(campo, valor) {
    if (!config) return;
    setGuardando(true);
    try {
      const nuevaConfig = await actualizarConfigEmailApi({ [campo]: valor });
      setConfig(nuevaConfig);
    } catch {
      setError("Error guardando configuración");
    } finally {
      setGuardando(false);
    }
  }
  async function eliminarReporte(id) {
    try {
      await eliminarReporteProgramadoApi(id);
      setReportes((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setError("Error eliminando reporte");
    }
  }
  function onReporteGuardado() {
    setModalAbierto(false);
    setReporteEditando(null);
    if (esPlus) {
      listarReportesProgramadosApi().then(setReportes).catch(() => {
      });
    }
  }
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("section", { className: "cristal rounded-xl p-6", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "animate-pulse space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-4 bg-superficie-700 rounded w-1/3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-10 bg-superficie-700 rounded" })
    ] }) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("section", { className: "cristal rounded-xl p-6 space-y-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "text-sm font-semibold text-white flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { className: "w-4 h-4 text-acento-400" }),
        "Emails automáticos"
      ] }),
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-sm font-medium text-superficie-200 flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-3.5 h-3.5 text-acento-400" }),
            "Alertas de caducidad"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-1", children: "Email diario a administradores con certificados próximos a vencer" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ToggleSwitch,
          {
            activo: config?.alertasCaducidadActivo ?? true,
            onChange: (v) => actualizarConfig("alertasCaducidadActivo", v),
            deshabilitado: guardando
          }
        )
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-px bg-white/[0.04]" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-sm font-medium text-superficie-200 flex items-center gap-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-3.5 h-3.5 text-acento-400" }),
              "Resumen periódico",
              !esProfesional && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] px-1.5 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded", children: "Plan Profesional" })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-1", children: "Resumen de actividad enviado por email con la frecuencia elegida" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            ToggleSwitch,
            {
              activo: config?.resumenActivo ?? false,
              onChange: (v) => actualizarConfig("resumenActivo", v),
              deshabilitado: guardando || !esProfesional
            }
          )
        ] }),
        esProfesional && config?.resumenActivo && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4 mt-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Frecuencia" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "select",
              {
                value: config.resumenFrecuencia,
                onChange: (e) => actualizarConfig("resumenFrecuencia", e.target.value),
                disabled: guardando,
                className: "w-full px-3 py-2 rounded-lg border text-sm text-superficie-100\n                    border-white/[0.06] bg-superficie-800/60 outline-none",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "diario", children: "Diario" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "semanal", children: "Semanal (lunes)" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "mensual", children: "Mensual (día 1)" })
                ]
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Destinatarios" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "select",
              {
                value: config.resumenSoloAdmin ? "admin" : "todos",
                onChange: (e) => actualizarConfig("resumenSoloAdmin", e.target.value === "admin"),
                disabled: guardando,
                className: "w-full px-3 py-2 rounded-lg border text-sm text-superficie-100\n                    border-white/[0.06] bg-superficie-800/60 outline-none",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "admin", children: "Solo administradores" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "todos", children: "Todos los usuarios" })
                ]
              }
            )
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-px bg-white/[0.04]" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-sm font-medium text-superficie-200 flex items-center gap-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-3.5 h-3.5 text-acento-400" }),
              "Reportes programados",
              !esPlus && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] px-1.5 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded", children: "Plan Plus" })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-1", children: "Genera y envía reportes automáticos por email" })
          ] }),
          esPlus && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => {
                setReporteEditando(null);
                setModalAbierto(true);
              },
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-acento-400\n                  border border-acento-500/20 rounded-lg hover:bg-acento-500/5 transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-3.5 h-3.5" }),
                "Nuevo reporte"
              ]
            }
          )
        ] }),
        esPlus && reportes.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-hidden rounded-lg border border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-xs", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "bg-superficie-800/60", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-2 text-left text-superficie-400 font-medium", children: "Nombre" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-2 text-left text-superficie-400 font-medium", children: "Tipo" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-2 text-left text-superficie-400 font-medium", children: "Formato" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-2 text-left text-superficie-400 font-medium", children: "Frecuencia" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-2 text-center text-superficie-400 font-medium", children: "Estado" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-3 py-2 text-right text-superficie-400 font-medium", children: "Acciones" })
          ] }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: reportes.map((r) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02]", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-2.5 text-superficie-200", children: r.nombre }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-2.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-1.5 py-0.5 bg-acento-500/10 text-acento-400 rounded text-[10px]", children: r.tipoReporte }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-2.5 text-superficie-300 uppercase", children: r.formato }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-2.5 text-superficie-300", children: r.frecuencia }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-2.5 text-center", children: r.activo ? /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-[10px]", children: "Activo" }) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-1.5 py-0.5 bg-red-500/10 text-red-400 rounded text-[10px]", children: "Inactivo" }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-3 py-2.5 text-right", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-1", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => {
                    setReporteEditando(r);
                    setModalAbierto(true);
                  },
                  className: "p-1 text-superficie-400 hover:text-acento-400 transition-colors",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Pencil, { className: "w-3.5 h-3.5" })
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => eliminarReporte(r.id),
                  className: "p-1 text-superficie-400 hover:text-red-400 transition-colors",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3.5 h-3.5" })
                }
              )
            ] }) })
          ] }, r.id)) })
        ] }) }),
        esPlus && reportes.length === 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 text-center py-4", children: "No hay reportes programados configurados" })
      ] }),
      esProfesional && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-px bg-white/[0.04]" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("h3", { className: "text-sm font-medium text-superficie-200 flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-3.5 h-3.5 text-acento-400" }),
            "Historial de envíos"
          ] }),
          historial.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2 max-h-64 overflow-y-auto", children: historial.map((e) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "div",
            {
              className: "flex items-center justify-between px-3 py-2 rounded-lg bg-superficie-800/40 border border-white/[0.04]",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeTipoEnvio, { tipo: e.tipo }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-300", children: new Date(e.enviadoEn).toLocaleDateString("es-ES", {
                    day: "2-digit",
                    month: "short",
                    hour: "2-digit",
                    minute: "2-digit"
                  }) })
                ] }),
                e.estado === "enviado" ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-3.5 h-3.5 text-emerald-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-3.5 h-3.5 text-red-400" })
              ]
            },
            e.id
          )) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 text-center py-4", children: "No hay envíos registrados" })
        ] })
      ] })
    ] }),
    modalAbierto && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalReporteProgramado,
      {
        reporteExistente: reporteEditando,
        onGuardar: onReporteGuardado,
        onCerrar: () => {
          setModalAbierto(false);
          setReporteEditando(null);
        }
      }
    )
  ] });
}
function ToggleSwitch({
  activo,
  onChange,
  deshabilitado
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsx(
    "button",
    {
      type: "button",
      onClick: () => !deshabilitado && onChange(!activo),
      className: `relative inline-flex h-5 w-9 items-center rounded-full transition-colors
        ${deshabilitado ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${activo ? "bg-acento-500" : "bg-superficie-600"}`,
      children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "span",
        {
          className: `inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform
          ${activo ? "translate-x-4" : "translate-x-0.5"}`
        }
      )
    }
  );
}
function BadgeTipoEnvio({ tipo }) {
  const estilos = {
    alerta_caducidad: "bg-amber-500/10 text-amber-400",
    resumen: "bg-blue-500/10 text-blue-400",
    reporte_programado: "bg-purple-500/10 text-purple-400"
  };
  const etiquetas = {
    alerta_caducidad: "Alerta",
    resumen: "Resumen",
    reporte_programado: "Reporte"
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-1.5 py-0.5 rounded text-[10px] font-medium ${estilos[tipo] ?? "bg-superficie-700 text-superficie-300"}`, children: etiquetas[tipo] ?? tipo });
}
const ICONO_GOOGLE = () => /* @__PURE__ */ jsxRuntimeExports.jsx("svg", { viewBox: "0 0 24 24", className: "w-5 h-5", fill: "none", xmlns: "http://www.w3.org/2000/svg", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
  "path",
  {
    d: "M22 6C22 4.9 21.1 4 20 4H4C2.9 4 2 4.9 2 6V18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V6ZM20 6L12 11L4 6H20ZM20 18H4V8L12 13L20 8V18Z",
    fill: "#EA4335"
  }
) });
const ICONO_OUTLOOK = () => /* @__PURE__ */ jsxRuntimeExports.jsxs("svg", { viewBox: "0 0 24 24", className: "w-5 h-5", fill: "none", xmlns: "http://www.w3.org/2000/svg", children: [
  /* @__PURE__ */ jsxRuntimeExports.jsx("rect", { x: "2", y: "4", width: "13", height: "16", rx: "1", fill: "#0078D4" }),
  /* @__PURE__ */ jsxRuntimeExports.jsx("rect", { x: "9", y: "4", width: "13", height: "16", rx: "1", fill: "#28A8E8" }),
  /* @__PURE__ */ jsxRuntimeExports.jsx("path", { d: "M9 4H15L22 8V16L15 20H9V4Z", fill: "#0366D6", opacity: "0.3" }),
  /* @__PURE__ */ jsxRuntimeExports.jsx(
    "path",
    {
      d: "M5.5 9C5.5 7.6 6.6 6.5 8 6.5C9.4 6.5 10.5 7.6 10.5 9C10.5 10.4 9.4 11.5 8 11.5C6.6 11.5 5.5 10.4 5.5 9Z",
      fill: "white"
    }
  ),
  /* @__PURE__ */ jsxRuntimeExports.jsx("rect", { x: "5.5", y: "11.5", width: "5", height: "5", rx: "0.5", fill: "white" })
] });
const PLANES_CON_INTEGRACIONES = ["profesional", "plus"];
const PLANES_CON_DESCARTE = ["profesional", "plus"];
const PLANES_CON_LOGO = ["plus"];
const PLANES_CON_BRANDING = ["plus"];
function PaginaConfiguracion() {
  const { usuario, actualizarUsuario } = useAuthStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const inputLogoRef = reactExports.useRef(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [configGeneral, setConfigGeneral] = reactExports.useState({ diasAviso: 30, diasDescarteAutomatico: 0, comunidadAutonoma: null });
  const [perfil, setPerfil] = reactExports.useState({
    nombre: usuario?.nombre ?? "",
    organizacion: ""
  });
  const [guardandoPerfil, setGuardandoPerfil] = reactExports.useState(false);
  const [perfilGuardado, setPerfilGuardado] = reactExports.useState(false);
  const [guardandoConfig, setGuardandoConfig] = reactExports.useState(false);
  const [integraciones, setIntegraciones] = reactExports.useState(null);
  const [conectandoGoogle, setConectandoGoogle] = reactExports.useState(false);
  const [conectandoMicrosoft, setConectandoMicrosoft] = reactExports.useState(false);
  const [sincronizando, setSincronizando] = reactExports.useState(false);
  const [desconectando, setDesconectando] = reactExports.useState(null);
  const [mensajeIntegracion, setMensajeIntegracion] = reactExports.useState(null);
  const [planOrganizacion, setPlanOrganizacion] = reactExports.useState("");
  const [guardandoComunidad, setGuardandoComunidad] = reactExports.useState(false);
  const [descartando, setDescartando] = reactExports.useState(false);
  const [guardandoDescarte, setGuardandoDescarte] = reactExports.useState(false);
  const [logoBase64, setLogoBase64] = reactExports.useState(null);
  const [subiendoLogo, setSubiendoLogo] = reactExports.useState(false);
  const [eliminandoLogo, setEliminandoLogo] = reactExports.useState(false);
  const [colorPrimario, setColorPrimario] = reactExports.useState(null);
  const planPermiteIntegraciones = PLANES_CON_INTEGRACIONES.includes(planOrganizacion);
  const planPermiteDescarte = PLANES_CON_DESCARTE.includes(planOrganizacion);
  const planPermiteLogo = PLANES_CON_LOGO.includes(planOrganizacion);
  const planPermiteBranding = PLANES_CON_BRANDING.includes(planOrganizacion);
  reactExports.useEffect(() => {
    const resultado = searchParams.get("integracion");
    const proveedor = searchParams.get("proveedor");
    if (resultado === "exito") {
      setMensajeIntegracion({ tipo: "exito", texto: `${proveedor === "google" ? "Google Calendar" : "Outlook"} conectado correctamente` });
      setSearchParams({}, { replace: true });
    } else if (resultado === "error") {
      const mensaje = searchParams.get("mensaje");
      setMensajeIntegracion({ tipo: "error", texto: mensaje ?? `Error al conectar ${proveedor ?? "calendario"}` });
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);
  reactExports.useEffect(() => {
    if (!mensajeIntegracion) return;
    const timer = setTimeout(() => setMensajeIntegracion(null), 5e3);
    return () => clearTimeout(timer);
  }, [mensajeIntegracion]);
  reactExports.useEffect(() => {
    async function cargarDatos() {
      try {
        const [perfilApi, configApi] = await Promise.all([
          obtenerPerfilApi(),
          obtenerConfiguracionApi()
        ]);
        setPerfil({
          nombre: perfilApi.nombre,
          organizacion: perfilApi.organizacion.nombre
        });
        setConfigGeneral({
          diasAviso: configApi.diasAviso,
          diasDescarteAutomatico: configApi.diasDescarteAutomatico ?? 0,
          comunidadAutonoma: configApi.comunidadAutonoma ?? null
        });
        const plan = perfilApi.organizacion.plan;
        setPlanOrganizacion(plan);
        setLogoBase64(perfilApi.organizacion.logotipoBase64 ?? null);
        setColorPrimario(perfilApi.organizacion.colorPrimario ?? null);
        if (PLANES_CON_INTEGRACIONES.includes(plan)) {
          try {
            const estado = await obtenerEstadoIntegracionesApi();
            setIntegraciones(estado);
          } catch {
          }
        }
      } finally {
        setCargando(false);
      }
    }
    cargarDatos();
  }, []);
  const actualizarDiasAviso = (valor) => {
    const numero = Math.max(1, Math.min(365, Number(valor) || 30));
    setConfigGeneral((prev) => ({ ...prev, diasAviso: numero }));
  };
  const manejarGuardarDiasAviso = async () => {
    setGuardandoConfig(true);
    try {
      await actualizarConfiguracionApi({ diasAviso: configGeneral.diasAviso });
    } finally {
      setGuardandoConfig(false);
    }
  };
  const manejarGuardarPerfil = async (e) => {
    e.preventDefault();
    setGuardandoPerfil(true);
    try {
      const perfilActualizado = await actualizarPerfilApi({ nombre: perfil.nombre });
      actualizarUsuario({ nombre: perfilActualizado.nombre });
      setPerfilGuardado(true);
      setTimeout(() => setPerfilGuardado(false), 3e3);
    } finally {
      setGuardandoPerfil(false);
    }
  };
  const manejarGuardarComunidad = async (valor) => {
    setGuardandoComunidad(true);
    try {
      setConfigGeneral((prev) => ({ ...prev, comunidadAutonoma: valor }));
      await actualizarConfiguracionApi({
        diasAviso: configGeneral.diasAviso,
        comunidadAutonoma: valor ?? null
      });
      setMensajeIntegracion({ tipo: "exito", texto: "Comunidad autonoma actualizada" });
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al guardar comunidad autonoma" });
    } finally {
      setGuardandoComunidad(false);
    }
  };
  const manejarGuardarDescarte = async () => {
    setGuardandoDescarte(true);
    try {
      await actualizarConfiguracionApi({ diasAviso: configGeneral.diasAviso, diasDescarteAutomatico: configGeneral.diasDescarteAutomatico });
      setMensajeIntegracion({ tipo: "exito", texto: "Configuración de descarte guardada" });
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al guardar configuración de descarte" });
    } finally {
      setGuardandoDescarte(false);
    }
  };
  const manejarDescartarAhora = async () => {
    setDescartando(true);
    try {
      const resultado = await descartarAutomaticasApi();
      setMensajeIntegracion({
        tipo: "exito",
        texto: resultado.descartadas > 0 ? `${resultado.descartadas} notificaciones descartadas` : "No hay notificaciones antiguas para descartar"
      });
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al descartar notificaciones" });
    } finally {
      setDescartando(false);
    }
  };
  const manejarSubirLogo = async (e) => {
    const archivo = e.target.files?.[0];
    if (!archivo) return;
    if (!["image/png", "image/jpeg"].includes(archivo.type)) {
      setMensajeIntegracion({ tipo: "error", texto: "Solo se permiten imágenes PNG o JPG" });
      return;
    }
    if (archivo.size > 2 * 1024 * 1024) {
      setMensajeIntegracion({ tipo: "error", texto: "El logotipo no puede superar 2 MB" });
      return;
    }
    setSubiendoLogo(true);
    try {
      const resultado = await subirLogoApi(archivo);
      setLogoBase64(resultado.logotipoBase64);
      setMensajeIntegracion({ tipo: "exito", texto: "Logotipo actualizado correctamente" });
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al subir el logotipo" });
    } finally {
      setSubiendoLogo(false);
      if (inputLogoRef.current) inputLogoRef.current.value = "";
    }
  };
  const manejarEliminarLogo = async () => {
    setEliminandoLogo(true);
    try {
      await eliminarLogoApi();
      setLogoBase64(null);
      setMensajeIntegracion({ tipo: "exito", texto: "Logotipo eliminado" });
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al eliminar el logotipo" });
    } finally {
      setEliminandoLogo(false);
    }
  };
  const manejarConectarGoogle = async () => {
    setConectandoGoogle(true);
    try {
      const { url } = await autorizarGoogleApi();
      window.location.href = url;
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al iniciar conexión con Google" });
      setConectandoGoogle(false);
    }
  };
  const manejarConectarMicrosoft = async () => {
    setConectandoMicrosoft(true);
    try {
      const { url } = await autorizarMicrosoftApi();
      window.location.href = url;
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al iniciar conexión con Outlook" });
      setConectandoMicrosoft(false);
    }
  };
  const manejarSincronizar = async () => {
    setSincronizando(true);
    try {
      const resultado = await sincronizarCalendarioApi();
      setMensajeIntegracion({
        tipo: "exito",
        texto: `Sincronización completada: ${resultado.eventosCreados} eventos creados${resultado.errores > 0 ? `, ${resultado.errores} errores` : ""}`
      });
      const estado = await obtenerEstadoIntegracionesApi();
      setIntegraciones(estado);
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: "Error al sincronizar calendario" });
    } finally {
      setSincronizando(false);
    }
  };
  const manejarDesconectar = async (proveedor) => {
    setDesconectando(proveedor);
    try {
      await desconectarIntegracionApi(proveedor);
      setIntegraciones(
        (prev) => prev ? { ...prev, [proveedor]: null } : prev
      );
      setMensajeIntegracion({
        tipo: "exito",
        texto: `${proveedor === "google" ? "Google Calendar" : "Outlook"} desconectado`
      });
    } catch {
      setMensajeIntegracion({ tipo: "error", texto: `Error al desconectar ${proveedor}` });
    } finally {
      setDesconectando(null);
    }
  };
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-2xl space-y-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Configuración" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-6 animate-pulse h-32" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-6 animate-pulse h-24" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-6 animate-pulse h-48" })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-2xl space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Configuración" }),
    mensajeIntegracion && /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "div",
      {
        className: `flex items-center gap-2 px-4 py-3 rounded-lg text-sm ${mensajeIntegracion.tipo === "exito" ? "bg-green-500/10 border border-green-500/20 text-green-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`,
        children: [
          mensajeIntegracion.tipo === "exito" ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-4 h-4 shrink-0" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
          mensajeIntegracion.texto
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs(Seccion, { titulo: "Configuración general", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Aviso de caducidad" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Recibir aviso cuando un certificado caduque en menos de N días" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              min: 1,
              max: 365,
              value: configGeneral.diasAviso,
              onChange: (e) => actualizarDiasAviso(e.target.value),
              onBlur: manejarGuardarDiasAviso,
              disabled: guardandoConfig,
              className: "w-20 px-3 py-1.5 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 text-center\n                disabled:opacity-50"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-500", children: "días" })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Separador, {}),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Copia de seguridad" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Gestiona las copias de seguridad de tus certificados" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-superficie-300\n            border border-white/[0.06] rounded-lg hover:bg-white/[0.05] transition-colors whitespace-nowrap",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(HardDrive, { className: "w-4 h-4" }),
              "Gestionar Copia"
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Separador, {}),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Desinstalar caducados" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Elimina de forma permanente todos los certificados caducados" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-400\n            border border-red-500/20 rounded-lg hover:bg-red-500/5 transition-colors whitespace-nowrap",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" }),
              "Desinstalar Todos los Caducados"
            ]
          }
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Seccion, { titulo: "Comunidad autonoma", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Festivos autonomicos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Selecciona tu comunidad para incluir sus festivos en el calculo de plazos legales (dias habiles)" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(MapPin, { className: "w-4 h-4 text-superficie-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: configGeneral.comunidadAutonoma ?? "",
            onChange: (e) => manejarGuardarComunidad(e.target.value || null),
            disabled: guardandoComunidad,
            className: "px-3 py-1.5 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60\n                disabled:opacity-50 min-w-[200px]",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Solo festivos nacionales" }),
              COMUNIDADES_AUTONOMAS.map((ca) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: ca, children: NOMBRES_COMUNIDADES[ca] }, ca))
            ]
          }
        )
      ] })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Seccion, { titulo: "Descarte automático de notificaciones", children: !planPermiteDescarte ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "El descarte automático está disponible en los planes Profesional y Plus." }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mb-4", children: "Descarta automáticamente las notificaciones pendientes que superen un número de días configurado." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Días para descartar" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Las notificaciones pendientes con más antigüedad se descartarán. 0 = desactivado." })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              min: 0,
              max: 365,
              value: configGeneral.diasDescarteAutomatico,
              onChange: (e) => {
                const v = Math.max(0, Math.min(365, Number(e.target.value) || 0));
                setConfigGeneral((prev) => ({ ...prev, diasDescarteAutomatico: v }));
              },
              disabled: guardandoDescarte,
              className: "w-20 px-3 py-1.5 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                    focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 text-center\n                    disabled:opacity-50"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-500", children: "días" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: manejarGuardarDescarte,
              disabled: guardandoDescarte,
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-acento-400\n                    border border-acento-500/20 rounded-lg hover:bg-acento-500/5 transition-colors disabled:opacity-50",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Save, { className: "w-3.5 h-3.5" }),
                guardandoDescarte ? "Guardando..." : "Guardar"
              ]
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Separador, {}),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Descartar ahora" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Ejecuta el descarte inmediato según la configuración actual" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarDescartarAhora,
            disabled: descartando || configGeneral.diasDescarteAutomatico <= 0,
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-400\n                  border border-amber-500/20 rounded-lg hover:bg-amber-500/5 transition-colors whitespace-nowrap\n                  disabled:opacity-50",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" }),
              descartando ? "Descartando..." : "Descartar antiguas"
            ]
          }
        )
      ] })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Seccion, { titulo: "Logotipo corporativo", children: !planPermiteLogo ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "El logotipo corporativo está disponible en el plan Plus. Se incluye en emails y documentos PDF generados." }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mb-4", children: "Tu logotipo aparecerá en los emails enviados a clientes y en los documentos PDF generados." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-32 h-32 rounded-lg border border-white/[0.06] bg-superficie-800/40 flex items-center justify-center overflow-hidden shrink-0", children: logoBase64 ? /* @__PURE__ */ jsxRuntimeExports.jsx(
          "img",
          {
            src: logoBase64,
            alt: "Logotipo corporativo",
            className: "max-w-full max-h-full object-contain"
          }
        ) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Image, { className: "w-8 h-8 text-superficie-600 mx-auto mb-1" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-600", children: "Sin logotipo" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3 flex-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                ref: inputLogoRef,
                type: "file",
                accept: "image/png,image/jpeg",
                onChange: manejarSubirLogo,
                className: "hidden",
                id: "input-logo"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                onClick: () => inputLogoRef.current?.click(),
                disabled: subiendoLogo,
                className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-acento-400\n                      border border-acento-500/20 rounded-lg hover:bg-acento-500/5 transition-colors\n                      disabled:opacity-50",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-4 h-4" }),
                  subiendoLogo ? "Subiendo..." : logoBase64 ? "Cambiar logotipo" : "Subir logotipo"
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1.5", children: "PNG o JPG, máximo 2 MB" })
          ] }),
          logoBase64 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: manejarEliminarLogo,
              disabled: eliminandoLogo,
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-400\n                      border border-red-500/20 rounded-lg hover:bg-red-500/5 transition-colors\n                      disabled:opacity-50",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3.5 h-3.5" }),
                eliminandoLogo ? "Eliminando..." : "Eliminar logotipo"
              ]
            }
          )
        ] })
      ] })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      SeccionBranding,
      {
        planPermite: planPermiteBranding,
        colorActual: colorPrimario,
        onColorCambiado: setColorPrimario
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(SeccionEmails, { planOrganizacion }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Seccion, { titulo: "Integraciones de calendario", children: !planPermiteIntegraciones ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Las integraciones de calendario están disponibles en los planes Profesional y Plus." }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mb-4", children: "Sincroniza los vencimientos de certificados con tu calendario para recibir recordatorios automáticos." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          IntegracionItem,
          {
            nombre: "Google Calendar",
            icono: /* @__PURE__ */ jsxRuntimeExports.jsx(ICONO_GOOGLE, {}),
            integracion: integraciones?.google ?? null,
            conectando: conectandoGoogle,
            desconectando: desconectando === "google",
            onConectar: manejarConectarGoogle,
            onDesconectar: () => manejarDesconectar("google")
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          IntegracionItem,
          {
            nombre: "Outlook",
            icono: /* @__PURE__ */ jsxRuntimeExports.jsx(ICONO_OUTLOOK, {}),
            integracion: integraciones?.microsoft ?? null,
            conectando: conectandoMicrosoft,
            desconectando: desconectando === "microsoft",
            onConectar: manejarConectarMicrosoft,
            onDesconectar: () => manejarDesconectar("microsoft")
          }
        )
      ] }),
      (integraciones?.google || integraciones?.microsoft) && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-4 pt-4 border-t border-white/[0.04]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: "Sincronizar vencimientos" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5", children: "Crea eventos en el calendario para todos los certificados activos" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarSincronizar,
            disabled: sincronizando,
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-acento-400\n                      border border-acento-500/20 rounded-lg hover:bg-acento-500/5 transition-colors whitespace-nowrap\n                      disabled:opacity-50",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: `w-4 h-4 ${sincronizando ? "animate-spin" : ""}` }),
              sincronizando ? "Sincronizando..." : "Sincronizar ahora"
            ]
          }
        )
      ] }) })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Seccion, { titulo: "Perfil", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarGuardarPerfil, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CampoPerfil,
        {
          etiqueta: "Nombre completo",
          valor: perfil.nombre,
          onChange: (v) => setPerfil((prev) => ({ ...prev, nombre: v })),
          placeholder: "Tu nombre"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CampoPerfil,
        {
          etiqueta: "Correo electrónico",
          valor: usuario?.email ?? "",
          onChange: () => void 0,
          readonly: true,
          placeholder: "tu@email.es"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CampoPerfil,
        {
          etiqueta: "Organización",
          valor: perfil.organizacion,
          onChange: () => void 0,
          readonly: true,
          placeholder: "Nombre de tu empresa"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 pt-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "submit",
            disabled: guardandoPerfil,
            className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n                disabled:opacity-50 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Save, { className: "w-4 h-4" }),
              guardandoPerfil ? "Guardando..." : "Guardar cambios"
            ]
          }
        ),
        perfilGuardado && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-acento-400 font-medium", children: "Cambios guardados" })
      ] })
    ] }) })
  ] });
}
function IntegracionItem({ nombre, icono, integracion, conectando, desconectando, onConectar, onDesconectar }) {
  if (integracion) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg bg-superficie-800/40 border border-white/[0.04]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        icono,
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-100", children: nombre }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
            integracion.emailCalendario ?? "Conectado",
            integracion.ultimoSync && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
              " · Último sync: ",
              new Date(integracion.ultimoSync).toLocaleDateString("es-ES")
            ] })
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: onDesconectar,
          disabled: desconectando,
          className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-400\n            border border-red-500/20 rounded-lg hover:bg-red-500/5 transition-colors disabled:opacity-50",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Unlink, { className: "w-3.5 h-3.5" }),
            desconectando ? "Desconectando..." : "Desconectar"
          ]
        }
      )
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "button",
    {
      onClick: onConectar,
      disabled: conectando,
      className: "flex items-center justify-center gap-2.5 px-4 py-2.5 text-sm font-medium w-full\n        text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.05] transition-colors\n        disabled:opacity-50",
      children: [
        icono,
        conectando ? "Conectando..." : `Conectar ${nombre}`
      ]
    }
  );
}
function Seccion({ titulo, children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("section", { className: "cristal rounded-xl p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "text-sm font-semibold text-white mb-5 flex items-center gap-2", children: [
      titulo === "Integraciones de calendario" && /* @__PURE__ */ jsxRuntimeExports.jsx(Calendar, { className: "w-4 h-4 text-acento-400" }),
      titulo === "Logotipo corporativo" && /* @__PURE__ */ jsxRuntimeExports.jsx(Image, { className: "w-4 h-4 text-acento-400" }),
      titulo
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-4", children })
  ] });
}
function Separador() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-px bg-white/[0.04]" });
}
function CampoPerfil({ etiqueta, valor, onChange, placeholder, readonly }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1.5", children: etiqueta }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "input",
      {
        type: "text",
        value: valor,
        onChange: (e) => onChange(e.target.value),
        placeholder,
        readOnly: readonly,
        className: `w-full px-3.5 py-2.5 rounded-lg border text-sm outline-none transition-colors placeholder:text-superficie-600
          ${readonly ? "bg-superficie-800/30 border-white/[0.04] text-superficie-500 cursor-not-allowed" : "text-superficie-100 border-white/[0.06] bg-superficie-800/60 hover:border-white/10 focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40"}`
      }
    )
  ] });
}
export {
  PaginaConfiguracion
};
