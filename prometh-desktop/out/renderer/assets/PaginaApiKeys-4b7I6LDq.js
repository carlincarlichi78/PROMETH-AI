import { d as apiClient, r as reactExports, J as BASE_URL, j as jsxRuntimeExports, K as Key, P as Plus, v as Check, M as PERMISOS_API_DISPONIBLES } from "./index-DMbE3NR1.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { E as ExternalLink } from "./external-link-Bh_6IHXn.js";
import { C as Copy } from "./copy-BxtWXfxP.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
function listarApiKeysApi() {
  return apiClient.get("/api-keys");
}
function crearApiKeyApi(datos) {
  return apiClient.post("/api-keys", datos);
}
function actualizarApiKeyApi(id, datos) {
  return apiClient.put(`/api-keys/${id}`, datos);
}
function eliminarApiKeyApi(id) {
  return apiClient.del(`/api-keys/${id}`);
}
function regenerarApiKeyApi(id) {
  return apiClient.post(`/api-keys/${id}/regenerar`, {});
}
function PaginaApiKeys() {
  const [keys, setKeys] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [modalAbierto, setModalAbierto] = reactExports.useState(false);
  const [claveVisible, setClaveVisible] = reactExports.useState(null);
  const [copiado, setCopiado] = reactExports.useState(false);
  const [nombre, setNombre] = reactExports.useState("");
  const [permisosSeleccionados, setPermisosSeleccionados] = reactExports.useState([
    "certificados:leer",
    "notificaciones:leer"
  ]);
  const cargar = reactExports.useCallback(async () => {
    try {
      setCargando(true);
      const resp = await listarApiKeysApi();
      if (resp.exito && resp.datos) setKeys(resp.datos);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando API keys");
    } finally {
      setCargando(false);
    }
  }, []);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  const crearKey = async () => {
    if (!nombre.trim()) return;
    try {
      const resp = await crearApiKeyApi({
        nombre: nombre.trim(),
        permisos: permisosSeleccionados
      });
      if (resp.exito && resp.datos) {
        setClaveVisible(resp.datos.clave);
        setModalAbierto(false);
        setNombre("");
        setPermisosSeleccionados(["certificados:leer", "notificaciones:leer"]);
        await cargar();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error creando API key");
    }
  };
  const eliminarKey = async (id) => {
    try {
      await eliminarApiKeyApi(id);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error eliminando API key");
    }
  };
  const regenerar = async (id) => {
    try {
      const resp = await regenerarApiKeyApi(id);
      if (resp.exito && resp.datos) {
        setClaveVisible(resp.datos.clave);
        await cargar();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error regenerando API key");
    }
  };
  const toggleActivo = async (key) => {
    try {
      await actualizarApiKeyApi(key.id, { activo: !key.activo });
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error actualizando API key");
    }
  };
  const copiarClave = async (clave) => {
    await navigator.clipboard.writeText(clave);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 2e3);
  };
  const togglePermiso = (permiso) => {
    setPermisosSeleccionados(
      (prev) => prev.includes(permiso) ? prev.filter((p) => p !== permiso) : [...prev, permiso]
    );
  };
  const cerrarModal = reactExports.useCallback(() => setModalAbierto(false), []);
  useEscapeKey(modalAbierto, cerrarModal);
  const urlDocs = BASE_URL.replace(/\/api$/, "/api/docs/");
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-5xl mx-auto space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "text-2xl font-bold text-white flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Key, { className: "w-7 h-7 text-acento-400" }),
          "API Publica"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 mt-1", children: "Crea API keys para integrar CertiGestor con tus aplicaciones" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "a",
          {
            href: urlDocs,
            target: "_blank",
            rel: "noopener noreferrer",
            className: "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-superficie-300 border border-white/[0.08] hover:bg-white/[0.05] transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(ExternalLink, { className: "w-4 h-4" }),
              "Documentacion API"
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setModalAbierto(true),
            className: "flex items-center gap-2 px-4 py-2.5 bg-acento-500 hover:bg-acento-600 text-white rounded-lg text-sm font-medium transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
              "Nueva API key"
            ]
          }
        )
      ] })
    ] }),
    claveVisible && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-emerald-400 text-sm font-medium mb-2", children: "Copia esta clave ahora. No podras volver a verla." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 bg-superficie-900 rounded-lg px-4 py-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "text-sm text-white font-mono flex-1 break-all", children: claveVisible }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => copiarClave(claveVisible),
            className: "p-2 rounded-md hover:bg-white/[0.05] text-superficie-400 hover:text-white transition-colors",
            children: copiado ? /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4 text-emerald-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "w-4 h-4" })
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setClaveVisible(null),
          className: "mt-3 text-xs text-superficie-500 hover:text-superficie-300 transition-colors",
          children: "Ocultar clave"
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm", children: [
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setError(null),
          className: "ml-3 underline hover:text-red-300",
          children: "Cerrar"
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-superficie-900 border border-white/[0.06] p-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white mb-2", children: "Como usar la API" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-sm text-superficie-400 space-y-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "1. Crea una API key con los permisos necesarios" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
          "2. Envia el header ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "text-acento-400 bg-white/[0.05] px-1.5 py-0.5 rounded", children: "X-API-Key: tu_clave" }),
          " en cada peticion"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { children: [
          "3. Los endpoints estan en ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("code", { className: "text-acento-400 bg-white/[0.05] px-1.5 py-0.5 rounded", children: "/api/v1/" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { children: "4. Limite: 100 peticiones/minuto por API key" })
      ] })
    ] }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-center py-12 text-superficie-500", children: "Cargando..." }) : keys.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Key, { className: "w-12 h-12 text-superficie-700 mx-auto mb-4" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400", children: "No tienes API keys aun" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm mt-1", children: "Crea una para empezar a integrar con aplicaciones externas" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl bg-superficie-900 border border-white/[0.06] overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-left text-superficie-500 font-medium", children: "Nombre" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-left text-superficie-500 font-medium", children: "Prefijo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-left text-superficie-500 font-medium", children: "Permisos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-left text-superficie-500 font-medium", children: "Peticiones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-left text-superficie-500 font-medium", children: "Ultimo uso" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-left text-superficie-500 font-medium", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3 text-right text-superficie-500 font-medium", children: "Acciones" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: keys.map((key) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02]", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5 text-white font-medium", children: key.nombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("code", { className: "text-xs text-superficie-400 bg-white/[0.05] px-2 py-1 rounded", children: [
          key.prefijo,
          "..."
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1", children: key.permisos.map((p) => /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: "text-[10px] px-1.5 py-0.5 rounded bg-acento-500/10 text-acento-400 border border-acento-500/20",
            children: p
          },
          p
        )) }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5 text-superficie-400", children: key.totalPeticiones.toLocaleString() }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5 text-superficie-500 text-xs", children: key.ultimoUso ? new Date(key.ultimoUso).toLocaleDateString("es-ES", {
          day: "2-digit",
          month: "short",
          hour: "2-digit",
          minute: "2-digit"
        }) : "Nunca" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => toggleActivo(key),
            className: `text-xs px-2 py-1 rounded-full font-medium ${key.activo ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`,
            children: key.activo ? "Activa" : "Desactivada"
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-3.5", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => regenerar(key.id),
              title: "Regenerar clave",
              className: "p-1.5 rounded-md text-superficie-500 hover:text-amber-400 hover:bg-amber-500/10 transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-3.5 h-3.5" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => eliminarKey(key.id),
              title: "Eliminar",
              className: "p-1.5 rounded-md text-superficie-500 hover:text-red-400 hover:bg-red-500/10 transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3.5 h-3.5" })
            }
          )
        ] }) })
      ] }, key.id)) })
    ] }) }),
    modalAbierto && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: cerrarModal, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.08] rounded-2xl w-full max-w-lg shadow-2xl", onClick: (e) => e.stopPropagation(), children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-6 border-b border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Nueva API key" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 space-y-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1.5", children: "Nombre" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: nombre,
              onChange: (e) => setNombre(e.target.value),
              placeholder: "Mi integracion",
              className: "w-full px-4 py-2.5 rounded-lg bg-superficie-800 border border-white/[0.08] text-white placeholder-superficie-600 focus:outline-none focus:border-acento-500/50"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-2", children: "Permisos" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: PERMISOS_API_DISPONIBLES.map((p) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "label",
            {
              className: "flex items-center gap-3 p-3 rounded-lg bg-superficie-800/50 border border-white/[0.04] hover:border-white/[0.08] cursor-pointer transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "input",
                  {
                    type: "checkbox",
                    checked: permisosSeleccionados.includes(p.id),
                    onChange: () => togglePermiso(p.id),
                    className: "rounded border-superficie-600 text-acento-500 focus:ring-acento-500/50"
                  }
                ),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-white", children: p.nombre }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: p.descripcion })
                ] })
              ]
            },
            p.id
          )) })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-6 border-t border-white/[0.06] flex justify-end gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setModalAbierto(false),
            className: "px-4 py-2.5 rounded-lg text-sm text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: crearKey,
            disabled: !nombre.trim() || permisosSeleccionados.length === 0,
            className: "px-4 py-2.5 bg-acento-500 hover:bg-acento-600 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors",
            children: "Crear API key"
          }
        )
      ] })
    ] }) })
  ] });
}
export {
  PaginaApiKeys
};
