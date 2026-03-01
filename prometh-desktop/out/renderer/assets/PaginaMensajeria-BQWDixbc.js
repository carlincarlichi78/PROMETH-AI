import { c as createLucideIcon, d as apiClient, r as reactExports, j as jsxRuntimeExports, O as MessageSquare, X, v as Check, Z as Zap } from "./index-DMbE3NR1.js";
import { S as Send } from "./send-mu2rTZak.js";
import { H as History } from "./history-CoQ7xusF.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { P as Phone } from "./phone-GsPdPFZ6.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { P as Power } from "./power-BwvIjpEF.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Bot = createLucideIcon("Bot", [
  ["path", { d: "M12 8V4H8", key: "hb8ula" }],
  ["rect", { width: "16", height: "12", x: "4", y: "8", rx: "2", key: "enze0r" }],
  ["path", { d: "M2 14h2", key: "vft8re" }],
  ["path", { d: "M20 14h2", key: "4cs60a" }],
  ["path", { d: "M15 13v2", key: "1xurst" }],
  ["path", { d: "M9 13v2", key: "rq6x2g" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const PowerOff = createLucideIcon("PowerOff", [
  ["path", { d: "M18.36 6.64A9 9 0 0 1 20.77 15", key: "dxknvb" }],
  ["path", { d: "M6.16 6.16a9 9 0 1 0 12.68 12.68", key: "1x7qb5" }],
  ["path", { d: "M12 2v4", key: "3427ic" }],
  ["path", { d: "m2 2 20 20", key: "1ooewy" }]
]);
const BASE = "/mensajeria";
async function listarCanalesApi() {
  const respuesta = await apiClient.get(`${BASE}/canales`);
  return respuesta.datos;
}
async function guardarCanalApi(datos) {
  const respuesta = await apiClient.post(`${BASE}/canales`, datos);
  return respuesta.datos;
}
async function toggleCanalApi(tipo, activo) {
  const respuesta = await apiClient.patch(`${BASE}/canales/${tipo}`, { activo });
  return respuesta.datos;
}
async function testConexionApi(tipo) {
  const respuesta = await apiClient.post(`${BASE}/test`, { tipo });
  return respuesta.datos;
}
async function enviarMensajeApi(datos) {
  const respuesta = await apiClient.post(`${BASE}/enviar`, datos);
  return respuesta.datos;
}
async function listarHistorialApi(params) {
  const query = new URLSearchParams();
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  if (params?.canal) query.set("canal", params.canal);
  if (params?.exito) query.set("exito", params.exito);
  const qs = query.toString();
  const respuesta = await apiClient.get(
    `${BASE}/historial${qs ? `?${qs}` : ""}`
  );
  return respuesta.datos;
}
const TABS = [
  { id: "canales", label: "Canales", icono: MessageSquare },
  { id: "enviar", label: "Enviar", icono: Send },
  { id: "historial", label: "Historial", icono: History }
];
const CONFIG_CAMPOS = {
  whatsapp: [
    { label: "Account SID", placeholder: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" },
    { label: "Auth Token", placeholder: "Token de autenticacion Twilio", tipo: "password" },
    { label: "Numero origen", placeholder: "+34600000000" }
  ],
  telegram: [
    { label: "Bot Token", placeholder: "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11", tipo: "password" },
    { label: "Chat ID por defecto", placeholder: "-1001234567890" }
  ]
};
const CONFIG_KEYS = {
  whatsapp: ["accountSid", "authToken", "numeroOrigen"],
  telegram: ["botToken", "chatIdDefecto"]
};
function formatearFechaCorta(fecha) {
  return new Date(fecha).toLocaleString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}
function PaginaMensajeria() {
  const [tab, setTab] = reactExports.useState("canales");
  const [canales, setCanales] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const cargarCanales = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const datos = await listarCanalesApi();
      setCanales(datos);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar canales");
    } finally {
      setCargando(false);
    }
  }, []);
  reactExports.useEffect(() => {
    cargarCanales();
  }, [cargarCanales]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(MessageSquare, { className: "w-5 h-5 text-acento-400" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Mensajeria" })
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
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    tab === "canales" && /* @__PURE__ */ jsxRuntimeExports.jsx(
      SeccionCanales,
      {
        canales,
        cargando,
        onRecargar: cargarCanales
      }
    ),
    tab === "enviar" && /* @__PURE__ */ jsxRuntimeExports.jsx(SeccionEnviar, { canales }),
    tab === "historial" && /* @__PURE__ */ jsxRuntimeExports.jsx(SeccionHistorial, {})
  ] });
}
function SeccionCanales({
  canales,
  cargando,
  onRecargar
}) {
  const tipos = ["whatsapp", "telegram"];
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando canales..." })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid gap-6 md:grid-cols-2", children: tipos.map((tipo) => {
    const canal = canales.find((c) => c.tipo === tipo);
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      TarjetaCanal,
      {
        tipo,
        canal: canal ?? null,
        onGuardado: onRecargar
      },
      tipo
    );
  }) });
}
function TarjetaCanal({
  tipo,
  canal,
  onGuardado
}) {
  const campos = CONFIG_CAMPOS[tipo];
  const keys = CONFIG_KEYS[tipo];
  const esWhatsApp = tipo === "whatsapp";
  const [config, setConfig] = reactExports.useState(() => {
    const inicial = {};
    keys.forEach((k) => {
      inicial[k] = canal?.configuracion[k] ?? "";
    });
    return inicial;
  });
  const [guardando, setGuardando] = reactExports.useState(false);
  const [testeando, setTesteando] = reactExports.useState(false);
  const [toggling, setToggling] = reactExports.useState(false);
  const [resultadoTest, setResultadoTest] = reactExports.useState(null);
  const [errorLocal, setErrorLocal] = reactExports.useState(null);
  const manejarGuardar = async () => {
    const vacios = keys.filter((k) => !config[k]?.trim());
    if (vacios.length > 0) {
      setErrorLocal("Completa todos los campos de configuracion");
      return;
    }
    setGuardando(true);
    setErrorLocal(null);
    try {
      await guardarCanalApi({ tipo, configuracion: config, activo: true });
      onGuardado();
    } catch (err) {
      setErrorLocal(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setGuardando(false);
    }
  };
  const manejarTest = async () => {
    setTesteando(true);
    setResultadoTest(null);
    try {
      const res = await testConexionApi(tipo);
      setResultadoTest({ ok: res.conectado, msg: res.mensaje });
    } catch (err) {
      setResultadoTest({ ok: false, msg: err instanceof Error ? err.message : "Error de conexion" });
    } finally {
      setTesteando(false);
    }
  };
  const manejarToggle = async () => {
    if (!canal) return;
    setToggling(true);
    try {
      await toggleCanalApi(tipo, !canal.activo);
      onGuardado();
    } catch {
    } finally {
      setToggling(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6 space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `p-2.5 rounded-lg ${esWhatsApp ? "bg-green-500/10" : "bg-blue-500/10"}`, children: esWhatsApp ? /* @__PURE__ */ jsxRuntimeExports.jsx(Phone, { className: "w-5 h-5 text-green-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Bot, { className: "w-5 h-5 text-blue-400" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-base font-semibold text-white", children: esWhatsApp ? "WhatsApp" : "Telegram" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: esWhatsApp ? "Via Twilio API" : "Via Bot API" })
        ] })
      ] }),
      canal && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarToggle,
          disabled: toggling,
          className: `flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${canal.activo ? "bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/20" : "bg-superficie-800/60 text-superficie-500 border-white/[0.06] hover:text-superficie-300"}`,
          children: [
            toggling ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3 h-3 animate-spin" }) : canal.activo ? /* @__PURE__ */ jsxRuntimeExports.jsx(Power, { className: "w-3 h-3" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(PowerOff, { className: "w-3 h-3" }),
            canal.activo ? "Activo" : "Inactivo"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-3", children: campos.map((campo, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: campo.label }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: campo.tipo ?? "text",
          value: config[keys[i]] ?? "",
          onChange: (e) => setConfig({ ...config, [keys[i]]: e.target.value }),
          placeholder: campo.placeholder,
          className: "w-full px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                outline-none focus:ring-2 focus:ring-acento-500/40 placeholder:text-superficie-600"
        }
      )
    ] }, keys[i])) }),
    errorLocal && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-red-400", children: errorLocal }),
    resultadoTest && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${resultadoTest.ok ? "bg-green-500/10 border border-green-500/20 text-green-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`, children: [
      resultadoTest.ok ? /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-3.5 h-3.5" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3.5 h-3.5" }),
      resultadoTest.msg
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2 pt-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarGuardar,
          disabled: guardando,
          className: "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500\n            hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
          children: [
            guardando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
            "Guardar"
          ]
        }
      ),
      canal && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarTest,
          disabled: testeando,
          className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06]\n              rounded-lg hover:bg-white/[0.05] transition-colors disabled:opacity-50",
          children: [
            testeando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "w-4 h-4" }),
            "Test conexion"
          ]
        }
      )
    ] })
  ] });
}
function SeccionEnviar({ canales }) {
  const canalesActivos = canales.filter((c) => c.activo);
  const [canal, setCanal] = reactExports.useState(
    canalesActivos[0]?.tipo ?? "whatsapp"
  );
  const [destinatario, setDestinatario] = reactExports.useState("");
  const [mensaje, setMensaje] = reactExports.useState("");
  const [enviando, setEnviando] = reactExports.useState(false);
  const [resultado, setResultado] = reactExports.useState(null);
  const manejarEnviar = async (e) => {
    e.preventDefault();
    if (!destinatario.trim() || !mensaje.trim()) return;
    setEnviando(true);
    setResultado(null);
    try {
      await enviarMensajeApi({
        canal,
        destinatario: destinatario.trim(),
        mensaje: mensaje.trim()
      });
      setResultado({ ok: true, msg: "Mensaje enviado correctamente" });
      setMensaje("");
      setDestinatario("");
    } catch (err) {
      setResultado({ ok: false, msg: err instanceof Error ? err.message : "Error al enviar" });
    } finally {
      setEnviando(false);
    }
  };
  if (canalesActivos.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-8 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(MessageSquare, { className: "w-10 h-10 text-superficie-600 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "No hay canales activos. Configura al menos un canal en la pestana Canales." })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6 max-w-xl", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-base font-semibold text-white mb-4", children: "Enviar mensaje" }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarEnviar, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: "Canal" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: canalesActivos.map((c) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "button",
            onClick: () => setCanal(c.tipo),
            className: `flex items-center gap-2 flex-1 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${canal === c.tipo ? c.tipo === "whatsapp" ? "bg-green-500/10 text-green-400 border-green-500/20" : "bg-blue-500/10 text-blue-400 border-blue-500/20" : "text-superficie-400 border-white/[0.06] hover:bg-white/[0.05]"}`,
            children: [
              c.tipo === "whatsapp" ? /* @__PURE__ */ jsxRuntimeExports.jsx(Phone, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Bot, { className: "w-4 h-4" }),
              c.tipo === "whatsapp" ? "WhatsApp" : "Telegram"
            ]
          },
          c.tipo
        )) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: "Destinatario" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: destinatario,
            onChange: (e) => setDestinatario(e.target.value),
            placeholder: canal === "whatsapp" ? "+34600000000" : "Chat ID o @usuario",
            className: "w-full px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n              outline-none focus:ring-2 focus:ring-acento-500/40 placeholder:text-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: "Mensaje" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "textarea",
          {
            value: mensaje,
            onChange: (e) => setMensaje(e.target.value),
            rows: 4,
            placeholder: "Escribe el mensaje a enviar...",
            className: "w-full px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n              outline-none focus:ring-2 focus:ring-acento-500/40 placeholder:text-superficie-600 resize-none"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "mt-1 text-xs text-superficie-600", children: [
          mensaje.length,
          " caracteres"
        ] })
      ] }),
      resultado && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${resultado.ok ? "bg-green-500/10 border border-green-500/20 text-green-400" : "bg-red-500/10 border border-red-500/20 text-red-400"}`, children: [
        resultado.ok ? /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }),
        resultado.msg
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          type: "submit",
          disabled: enviando || !destinatario.trim() || !mensaje.trim(),
          className: "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500\n            hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
          children: [
            enviando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-4 h-4" }),
            "Enviar mensaje"
          ]
        }
      )
    ] })
  ] });
}
function SeccionHistorial() {
  const [historial, setHistorial] = reactExports.useState([]);
  const [meta, setMeta] = reactExports.useState({ total: 0, pagina: 1, limite: 20, totalPaginas: 0 });
  const [cargando, setCargando] = reactExports.useState(true);
  const [filtroCanal, setFiltroCanal] = reactExports.useState("");
  const [filtroExito, setFiltroExito] = reactExports.useState("");
  const cargar = reactExports.useCallback(async (pagina = 1) => {
    setCargando(true);
    try {
      const resultado = await listarHistorialApi({
        pagina,
        limite: 20,
        canal: filtroCanal || void 0,
        exito: filtroExito || void 0
      });
      setHistorial(resultado.datos);
      setMeta(resultado.meta);
    } catch {
    } finally {
      setCargando(false);
    }
  }, [filtroCanal, filtroExito]);
  reactExports.useEffect(() => {
    cargar(1);
  }, [cargar]);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtroCanal,
          onChange: (e) => setFiltroCanal(e.target.value),
          className: "px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n            outline-none focus:ring-2 focus:ring-acento-500/40",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todos los canales" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "whatsapp", children: "WhatsApp" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "telegram", children: "Telegram" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtroExito,
          onChange: (e) => setFiltroExito(e.target.value),
          className: "px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n            outline-none focus:ring-2 focus:ring-acento-500/40",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todos los resultados" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "true", children: "Exitosos" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "false", children: "Fallidos" })
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => cargar(1),
          className: "flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06]\n            rounded-lg hover:bg-white/[0.05] transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-3.5 h-3.5" }),
            "Actualizar"
          ]
        }
      )
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando historial..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Canal" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Destinatario" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Mensaje" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Resultado" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 5, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No hay envios en el historial" }) }) : historial.map((envio) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 whitespace-nowrap text-xs", children: formatearFechaCorta(envio.enviadoEn) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${envio.canalTipo === "whatsapp" ? "bg-green-500/10 text-green-400" : "bg-blue-500/10 text-blue-400"}`, children: [
          envio.canalTipo === "whatsapp" ? /* @__PURE__ */ jsxRuntimeExports.jsx(Phone, { className: "w-3 h-3" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Bot, { className: "w-3 h-3" }),
          envio.canalTipo === "whatsapp" ? "WhatsApp" : "Telegram"
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 font-mono text-xs", children: envio.destinatario }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 max-w-xs truncate", children: envio.mensaje }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: envio.exito ? /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-3 h-3" }),
          "Enviado"
        ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "span",
          {
            className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20",
            title: envio.error ?? void 0,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3 h-3" }),
              "Fallido"
            ]
          }
        ) })
      ] }, envio.id)) })
    ] }) }) }),
    meta.totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Pagina ",
        meta.pagina,
        " de ",
        meta.totalPaginas,
        " (",
        meta.total,
        " envios)"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => cargar(Math.max(1, meta.pagina - 1)),
            disabled: meta.pagina <= 1,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => cargar(Math.min(meta.totalPaginas, meta.pagina + 1)),
            disabled: meta.pagina >= meta.totalPaginas,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
          }
        )
      ] })
    ] })
  ] });
}
export {
  PaginaMensajeria
};
