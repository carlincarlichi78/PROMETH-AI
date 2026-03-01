import { c as createLucideIcon, d as apiClient, r as reactExports, j as jsxRuntimeExports, U as Users, m as Search, X, v as Check } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { C as Copy } from "./copy-BxtWXfxP.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Link = createLucideIcon("Link", [
  ["path", { d: "M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71", key: "1cjeqo" }],
  ["path", { d: "M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71", key: "19qd67" }]
]);
async function listarAccesosPortalApi(params) {
  const query = new URLSearchParams();
  if (params?.busqueda) query.set("busqueda", params.busqueda);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const respuesta = await apiClient.get(`/accesos-portal?${query}`);
  return {
    accesos: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function crearAccesoPortalApi(datos) {
  const respuesta = await apiClient.post("/accesos-portal", datos);
  return respuesta.datos;
}
async function revocarAccesoPortalApi(id) {
  await apiClient.del(`/accesos-portal/${id}`);
}
function calcularEstadoAcceso(acceso) {
  if (!acceso.activo) {
    return {
      texto: "Revocado",
      clase: "bg-red-500/10 text-red-400 border-red-500/20"
    };
  }
  if (new Date(acceso.expiraEn) < /* @__PURE__ */ new Date()) {
    return {
      texto: "Expirado",
      clase: "bg-amber-500/10 text-amber-400 border-amber-500/20"
    };
  }
  return {
    texto: "Activo",
    clase: "bg-green-500/10 text-green-400 border-green-500/20"
  };
}
function PaginaAccesosPortal() {
  const [accesos, setAccesos] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const [modalAbierto, setModalAbierto] = reactExports.useState(false);
  const cargar = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarAccesosPortalApi({
        busqueda: busqueda || void 0,
        pagina,
        limite: 20
      });
      setAccesos(resultado.accesos);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar accesos");
    } finally {
      setCargando(false);
    }
  }, [busqueda, pagina]);
  reactExports.useEffect(() => {
    const timer = setTimeout(cargar, 300);
    return () => clearTimeout(timer);
  }, [cargar]);
  const manejarRevocar = async (id) => {
    if (!window.confirm("Revocar este acceso? El cliente ya no podra acceder al portal.")) return;
    try {
      await revocarAccesoPortalApi(id);
      cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al revocar acceso");
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Users, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Portal de Cliente" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-superficie-500", children: [
          "(",
          total,
          ")"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalAbierto(true),
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n            text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Link, { className: "w-4 h-4" }),
            "Generar enlace"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative max-w-md", children: [
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
          placeholder: "Buscar por nombre, DNI, email...",
          className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n              focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
        }
      )
    ] }) }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando accesos..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Nombre cliente" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "DNI/CIF" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Email" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Expiracion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Ultimo acceso" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Acciones" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: accesos.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 7, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No hay accesos al portal" }) }) : accesos.map((acceso) => {
        const estado = calcularEstadoAcceso(acceso);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 font-medium text-superficie-100", children: acceso.nombreCliente }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 font-mono text-xs", children: acceso.dniCif }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: acceso.emailCliente ?? "---" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300 whitespace-nowrap", children: formatearFecha(acceso.expiraEn) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap", children: acceso.ultimoAcceso ? formatearFecha(acceso.ultimoAcceso) : "Nunca" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${estado.clase}`, children: estado.texto }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-center", children: acceso.activo && new Date(acceso.expiraEn) >= /* @__PURE__ */ new Date() && /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => manejarRevocar(acceso.id),
              className: "px-3 py-1.5 text-xs font-medium text-red-400 border border-red-500/20 bg-red-500/10\n                                hover:bg-red-500/20 rounded-lg transition-colors",
              children: "Revocar"
            }
          ) })
        ] }, acceso.id);
      }) })
    ] }) }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mt-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Pagina ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " accesos)"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setPagina((p) => Math.max(1, p - 1)),
            disabled: pagina <= 1,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
            disabled: pagina >= totalPaginas,
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
          }
        )
      ] })
    ] }),
    modalAbierto && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalGenerarEnlace,
      {
        onCerrar: () => setModalAbierto(false),
        onGenerado: () => {
          cargar();
        }
      }
    )
  ] });
}
const OPCIONES_EXPIRACION = [
  { valor: 7, etiqueta: "7 dias" },
  { valor: 30, etiqueta: "30 dias" },
  { valor: 90, etiqueta: "90 dias" }
];
function ModalGenerarEnlace({
  onCerrar,
  onGenerado
}) {
  const [dniCif, setDniCif] = reactExports.useState("");
  const [nombreCliente, setNombreCliente] = reactExports.useState("");
  const [emailCliente, setEmailCliente] = reactExports.useState("");
  const [diasExpiracion, setDiasExpiracion] = reactExports.useState(30);
  const [generando, setGenerando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  const [enlaceGenerado, setEnlaceGenerado] = reactExports.useState(null);
  const [copiado, setCopiado] = reactExports.useState(false);
  const manejarGenerar = async (e) => {
    e.preventDefault();
    if (!dniCif.trim() || !nombreCliente.trim()) {
      setError("DNI/CIF y nombre del cliente son obligatorios");
      return;
    }
    setGenerando(true);
    setError(null);
    try {
      const resultado = await crearAccesoPortalApi({
        dniCif: dniCif.trim(),
        nombreCliente: nombreCliente.trim(),
        emailCliente: emailCliente.trim() || void 0,
        diasExpiracion
      });
      setEnlaceGenerado(resultado.enlace);
      onGenerado();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al generar enlace");
    } finally {
      setGenerando(false);
    }
  };
  const manejarCopiar = async () => {
    if (!enlaceGenerado) return;
    try {
      await navigator.clipboard.writeText(enlaceGenerado);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2e3);
    } catch {
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-lg mx-4 p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: enlaceGenerado ? "Enlace generado" : "Generar enlace de portal" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "p-1 text-superficie-400 hover:text-white rounded-lg hover:bg-white/[0.05]",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" })
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
    enlaceGenerado ? (
      /* Estado: enlace generado */
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300", children: "Comparte este enlace con tu cliente para que acceda a su portal:" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              readOnly: true,
              value: enlaceGenerado,
              className: "flex-1 px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                  outline-none font-mono text-xs"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: manejarCopiar,
              className: `flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${copiado ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-acento-500 hover:bg-acento-400 text-superficie-950"}`,
              children: copiado ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4" }),
                "Copiado"
              ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "w-4 h-4" }),
                "Copiar"
              ] })
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-end pt-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06]\n                  rounded-lg hover:bg-white/[0.05] transition-colors",
            children: "Cerrar"
          }
        ) })
      ] })
    ) : (
      /* Estado: formulario */
      /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarGenerar, className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: "DNI/CIF del cliente *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: dniCif,
              onChange: (e) => setDniCif(e.target.value),
              placeholder: "B12345678",
              className: "w-full px-3 py-2 rounded-lg border border-white/[0.06] text-sm text-superficie-100 outline-none\n                  focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: "Nombre del cliente *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: nombreCliente,
              onChange: (e) => setNombreCliente(e.target.value),
              placeholder: "Empresa Ejemplo S.L.",
              className: "w-full px-3 py-2 rounded-lg border border-white/[0.06] text-sm text-superficie-100 outline-none\n                  focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: "Email (opcional)" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "email",
              value: emailCliente,
              onChange: (e) => setEmailCliente(e.target.value),
              placeholder: "cliente@empresa.com",
              className: "w-full px-3 py-2 rounded-lg border border-white/[0.06] text-sm text-superficie-100 outline-none\n                  focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: "Expiracion del enlace" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: OPCIONES_EXPIRACION.map((opcion) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              type: "button",
              onClick: () => setDiasExpiracion(opcion.valor),
              className: `flex-1 px-3 py-2 text-sm font-medium rounded-lg border transition-colors ${diasExpiracion === opcion.valor ? "bg-acento-500/10 text-acento-400 border-acento-500/20" : "text-superficie-400 border-white/[0.06] hover:bg-white/[0.05] hover:text-superficie-200"}`,
              children: opcion.etiqueta
            },
            opcion.valor
          )) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3 pt-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              type: "button",
              onClick: onCerrar,
              className: "px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06]\n                  rounded-lg hover:bg-white/[0.05] transition-colors",
              children: "Cancelar"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              type: "submit",
              disabled: generando,
              className: "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500\n                  hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
              children: [
                generando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
                "Generar"
              ]
            }
          )
        ] })
      ] })
    )
  ] }) });
}
export {
  PaginaAccesosPortal
};
