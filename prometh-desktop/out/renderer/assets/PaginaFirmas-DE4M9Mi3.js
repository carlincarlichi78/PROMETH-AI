import { d as apiClient, J as BASE_URL, g as ErrorApiCliente, r as reactExports, j as jsxRuntimeExports, aa as PenLine, q as FileText, D as Download, X, n as ChevronDown, E as Eye } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { l as listarCertificadosApi } from "./certificadosServicio-DtEVLLjT.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
async function listarFirmasApi(params) {
  const query = new URLSearchParams();
  if (params?.certificadoId) query.set("certificadoId", params.certificadoId);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  const queryStr = query.toString();
  const ruta = queryStr ? `/firmas?${queryStr}` : "/firmas";
  const respuesta = await apiClient.get(ruta);
  return {
    documentos: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function firmarPdfApi(archivo, certificadoId, firmaVisible, opcionesStamp) {
  const token = localStorage.getItem("accessToken");
  const formData = new FormData();
  formData.append("archivo", archivo);
  formData.append("certificadoId", certificadoId);
  if (firmaVisible) {
    formData.append("firmaVisible", "true");
    if (opcionesStamp) {
      formData.append("opcionesStamp", JSON.stringify(opcionesStamp));
    }
  }
  const respuesta = await fetch(`${BASE_URL}/firmas`, {
    method: "POST",
    headers: {
      ...token ? { Authorization: `Bearer ${token}` } : {}
    },
    body: formData
  });
  const datos = await respuesta.json();
  if (!respuesta.ok) {
    throw new ErrorApiCliente(respuesta.status, datos.error ?? "Error al firmar PDF");
  }
  return datos.datos;
}
async function descargarPdfFirmadoApi(id, nombreArchivo) {
  const token = localStorage.getItem("accessToken");
  const respuesta = await fetch(`${BASE_URL}/firmas/${id}/descargar`, {
    headers: {
      ...token ? { Authorization: `Bearer ${token}` } : {}
    }
  });
  if (!respuesta.ok) {
    throw new ErrorApiCliente(respuesta.status, "Error al descargar PDF firmado");
  }
  const blob = await respuesta.blob();
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombreArchivo;
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
}
function formatearTamano(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function PaginaFirmas() {
  const [documentos, setDocumentos] = reactExports.useState([]);
  const [total, setTotal] = reactExports.useState(0);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [modalFirmar, setModalFirmar] = reactExports.useState(false);
  const cargarDocumentos = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarFirmasApi({ limite: 50 });
      setDocumentos(resultado.documentos);
      setTotal(resultado.meta.total);
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al cargar documentos firmados");
      }
    } finally {
      setCargando(false);
    }
  }, []);
  reactExports.useEffect(() => {
    cargarDocumentos();
  }, [cargarDocumentos]);
  const manejarDescargar = async (doc) => {
    try {
      await descargarPdfFirmadoApi(doc.id, doc.nombreArchivoFirmado);
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      }
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "text-xl font-semibold text-white whitespace-nowrap", children: [
        "Firmas Digitales (",
        total,
        ")"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalFirmar(true),
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n            text-superficie-950 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(PenLine, { className: "w-4 h-4" }),
            "Firmar PDF"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando documentos..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Documento" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tamaño" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3.5" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: documentos.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 5, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No hay documentos firmados todavía" }) }) : documentos.map((doc) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-5 h-5 text-acento-400 flex-shrink-0" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "font-medium text-superficie-100", children: doc.nombreArchivoOriginal }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-superficie-500 mt-0.5", children: doc.nombreArchivoFirmado })
          ] })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: formatearTamano(doc.tamanoBytes) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          "span",
          {
            className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${doc.estado === "completado" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`,
            children: doc.estado === "completado" ? "Firmado" : "Error"
          }
        ) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300", children: formatearFecha(doc.creadoEn) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => manejarDescargar(doc),
            title: "Descargar PDF firmado",
            className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-acento-400\n                            border border-acento-500/30 rounded-lg hover:bg-acento-500/10 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-3.5 h-3.5" }),
              "Descargar"
            ]
          }
        ) })
      ] }, doc.id)) })
    ] }) }) }),
    modalFirmar && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalFirmarPdf,
      {
        onCerrar: () => setModalFirmar(false),
        onFirmado: () => {
          setModalFirmar(false);
          cargarDocumentos();
        }
      }
    )
  ] });
}
function ModalFirmarPdf({
  onCerrar,
  onFirmado
}) {
  const [archivo, setArchivo] = reactExports.useState(null);
  const [certificadoId, setCertificadoId] = reactExports.useState("");
  const [certificados, setCertificados] = reactExports.useState([]);
  const [cargandoCerts, setCargandoCerts] = reactExports.useState(true);
  const [cargando, setCargando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  const [firmaVisible, setFirmaVisible] = reactExports.useState(false);
  const [nombreFirmante, setNombreFirmante] = reactExports.useState("");
  const [razonFirma, setRazonFirma] = reactExports.useState("Conforme");
  const [posicionStamp, setPosicionStamp] = reactExports.useState("inferior-derecha");
  reactExports.useEffect(() => {
    const cargar = async () => {
      try {
        const resultado = await listarCertificadosApi({ limite: 100 });
        setCertificados(resultado.certificados.filter((c) => c.activo));
      } catch {
        setError("Error al cargar certificados");
      } finally {
        setCargandoCerts(false);
      }
    };
    cargar();
  }, []);
  const manejarSubmit = async (e) => {
    e.preventDefault();
    if (!archivo) {
      setError("Selecciona un archivo PDF");
      return;
    }
    if (!certificadoId) {
      setError("Selecciona un certificado");
      return;
    }
    setCargando(true);
    setError(null);
    try {
      await firmarPdfApi(
        archivo,
        certificadoId,
        firmaVisible,
        firmaVisible ? { nombreFirmante, razon: razonFirma, posicion: posicionStamp } : void 0
      );
      onFirmado();
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al firmar el PDF");
      }
    } finally {
      setCargando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-md mx-4 p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Firmar PDF" }),
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
    /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-2", children: "Archivo PDF *" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "file",
            accept: ".pdf",
            onChange: (e) => {
              setArchivo(e.target.files?.[0] ?? null);
              setError(null);
            },
            className: "w-full text-sm text-superficie-300 file:mr-4 file:py-2 file:px-4\n                file:rounded-lg file:border-0 file:text-sm file:font-medium\n                file:bg-acento-500/10 file:text-acento-400 hover:file:bg-acento-500/20\n                cursor-pointer border border-white/[0.06] rounded-lg bg-superficie-800/60 p-2"
          }
        ),
        archivo && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "mt-1 text-xs text-superficie-500", children: [
          archivo.name,
          " (",
          formatearTamano(archivo.size),
          ")"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-2", children: "Certificado para firmar *" }),
        cargandoCerts ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 py-2 text-sm text-superficie-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
          "Cargando certificados..."
        ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: certificadoId,
              onChange: (e) => {
                setCertificadoId(e.target.value);
                setError(null);
              },
              className: "w-full appearance-none px-3 py-2 pr-8 rounded-lg border border-white/[0.06] text-sm\n                    text-superficie-100 outline-none focus:ring-2 focus:ring-acento-500/40\n                    bg-superficie-800/60 cursor-pointer",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", className: "bg-superficie-800", children: "Seleccionar certificado..." }),
                certificados.map((cert) => /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: cert.id, className: "bg-superficie-800", children: [
                  cert.nombreTitular,
                  " — ",
                  cert.dniCif,
                  cert.emisor ? ` (${cert.emisor})` : ""
                ] }, cert.id))
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500 pointer-events-none" })
        ] }),
        certificados.length === 0 && !cargandoCerts && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-xs text-amber-400", children: "No hay certificados disponibles. Importa un P12/PFX primero." })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-white/[0.06] pt-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-3 cursor-pointer", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "checkbox",
              checked: firmaVisible,
              onChange: (e) => setFirmaVisible(e.target.checked),
              className: "w-4 h-4 rounded border-white/20 bg-superficie-800 text-acento-500\n                  focus:ring-acento-500/40 focus:ring-offset-0"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Eye, { className: "w-4 h-4 text-superficie-400" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-superficie-200", children: "Firma visible" })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1 ml-7", children: "Agrega un sello visual con tu nombre y fecha en el PDF" }),
        firmaVisible && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 space-y-3 pl-7", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: "Nombre del firmante *" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "text",
                value: nombreFirmante,
                onChange: (e) => setNombreFirmante(e.target.value),
                placeholder: "Tu nombre completo",
                className: "w-full px-3 py-1.5 rounded-lg border border-white/[0.06] text-sm\n                      text-superficie-100 bg-superficie-800/60 outline-none\n                      focus:ring-2 focus:ring-acento-500/40"
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: "Razón de firma" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "text",
                value: razonFirma,
                onChange: (e) => setRazonFirma(e.target.value),
                placeholder: "Conforme",
                className: "w-full px-3 py-1.5 rounded-lg border border-white/[0.06] text-sm\n                      text-superficie-100 bg-superficie-800/60 outline-none\n                      focus:ring-2 focus:ring-acento-500/40"
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1", children: "Posición del sello" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs(
                "select",
                {
                  value: posicionStamp,
                  onChange: (e) => setPosicionStamp(e.target.value),
                  className: "w-full appearance-none px-3 py-1.5 pr-8 rounded-lg border border-white/[0.06]\n                        text-sm text-superficie-100 bg-superficie-800/60 outline-none\n                        focus:ring-2 focus:ring-acento-500/40 cursor-pointer",
                  children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "inferior-derecha", className: "bg-superficie-800", children: "Inferior derecha" }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "inferior-izquierda", className: "bg-superficie-800", children: "Inferior izquierda" }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "superior-derecha", className: "bg-superficie-800", children: "Superior derecha" }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "superior-izquierda", className: "bg-superficie-800", children: "Superior izquierda" })
                  ]
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-superficie-500 pointer-events-none" })
            ] })
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3 pt-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "button",
            onClick: onCerrar,
            className: "px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06]\n                rounded-lg hover:bg-white/[0.05] transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "submit",
            disabled: cargando || !archivo || !certificadoId || firmaVisible && !nombreFirmante.trim(),
            className: "px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500\n                hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
            children: cargando ? "Firmando..." : "Firmar PDF"
          }
        )
      ] })
    ] })
  ] }) });
}
export {
  PaginaFirmas
};
