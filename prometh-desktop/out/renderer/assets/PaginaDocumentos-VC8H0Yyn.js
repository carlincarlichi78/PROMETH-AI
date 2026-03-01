import { d as apiClient, J as BASE_URL, r as reactExports, j as jsxRuntimeExports, L as Lock, X, q as FileText, D as Download, H as obtenerPerfilApi, P as Plus, f as CircleCheckBig } from "./index-DMbE3NR1.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { l as listarCertificadosApi } from "./certificadosServicio-DtEVLLjT.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { F as FileCheck } from "./file-check-CGZ00Z_g.js";
async function obtenerPlantillasApi() {
  const respuesta = await apiClient.get("/documentos/plantillas");
  return respuesta.datos ?? [];
}
async function generarDocumentoApi(datos) {
  const respuesta = await apiClient.post("/documentos/generar", datos);
  return respuesta.datos;
}
async function listarDocumentosApi(params) {
  const query = new URLSearchParams();
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params.limite));
  const queryStr = query.toString();
  const ruta = queryStr ? `/documentos?${queryStr}` : "/documentos";
  const respuesta = await apiClient.get(ruta);
  return {
    documentos: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 10, totalPaginas: 0 }
  };
}
function descargarDocumentoUrl(id) {
  return `${BASE_URL}/documentos/${id}/descargar`;
}
function PaginaDocumentos() {
  const [plantillas, setPlantillas] = reactExports.useState([]);
  const [documentos, setDocumentos] = reactExports.useState([]);
  const [certificados, setCertificados] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [planActual, setPlanActual] = reactExports.useState("basico");
  const [generarModal, setGenerarModal] = reactExports.useState(null);
  const [generando, setGenerando] = reactExports.useState(false);
  const [exito, setExito] = reactExports.useState(false);
  reactExports.useEffect(() => {
    const cargar = async () => {
      try {
        const [plantillasRes, docsRes, perfilRes] = await Promise.all([
          obtenerPlantillasApi(),
          listarDocumentosApi({ limite: 20 }),
          obtenerPerfilApi()
        ]);
        setPlantillas(plantillasRes);
        setDocumentos(docsRes.documentos);
        setPlanActual(perfilRes.organizacion.plan);
        const certsRes = await listarCertificadosApi({ limite: 50 });
        setCertificados(certsRes.certificados);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar");
      } finally {
        setCargando(false);
      }
    };
    cargar();
  }, []);
  const manejarGenerar = async (tipo, certificadoId) => {
    setGenerando(true);
    setError(null);
    try {
      const doc = await generarDocumentoApi({
        tipo,
        certificadoId
      });
      setDocumentos((prev) => [doc, ...prev]);
      setExito(true);
      setTimeout(() => {
        setExito(false);
        setGenerarModal(null);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al generar");
    } finally {
      setGenerando(false);
    }
  };
  const descargar = (id) => {
    const token = localStorage.getItem("accessToken");
    const url = descargarDocumentoUrl(id);
    const a = document.createElement("a");
    a.href = `${url}?token=${token}`;
    a.target = "_blank";
    a.click();
  };
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin" }) });
  }
  const noDisponible = planActual === "basico";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Documentos automatizados" }),
      noDisponible && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 text-xs border border-amber-500/20", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Lock, { className: "w-3.5 h-3.5" }),
        "Disponible en plan Profesional+"
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-400 uppercase tracking-wide mb-3", children: "Plantillas disponibles" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8", children: TODAS_PLANTILLAS.map((p) => {
      const disponible = plantillas.some((pl) => pl.tipo === p.tipo);
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: `cristal rounded-xl p-4 border transition-all ${disponible ? "border-white/[0.06] hover:border-acento-500/30 cursor-pointer" : "border-white/[0.04] opacity-50"}`,
          onClick: () => disponible && setGenerarModal(p),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between mb-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-acento-500/10 border border-acento-500/20 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-5 h-5 text-acento-400" }) }),
              !disponible && /* @__PURE__ */ jsxRuntimeExports.jsx(Lock, { className: "w-4 h-4 text-superficie-500" })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-medium text-white mb-1", children: p.nombre }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 line-clamp-2", children: p.descripcion })
          ]
        },
        p.tipo
      );
    }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-superficie-400 uppercase tracking-wide mb-3", children: "Historial de documentos" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: documentos.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-12 px-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(FileCheck, { className: "w-8 h-8 text-superficie-500 mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "No has generado documentos aún" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Documento" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tipo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Acción" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: documentos.map((doc) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 font-medium text-superficie-100", children: doc.nombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: doc.tipo.replace(/_/g, " ") }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap", children: formatearFecha(doc.creadoEn) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => descargar(doc.id),
            className: "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium\n                          bg-acento-500/10 text-acento-400 border border-acento-500/20\n                          hover:bg-acento-500/20 transition-all",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-3.5 h-3.5" }),
              "Descargar"
            ]
          }
        ) })
      ] }, doc.id)) })
    ] }) }) }),
    generarModal && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalGenerarDocumento,
      {
        plantilla: generarModal,
        certificados,
        generando,
        exito,
        onGenerar: manejarGenerar,
        onCerrar: () => setGenerarModal(null)
      }
    )
  ] });
}
const TODAS_PLANTILLAS = [
  { tipo: "certificado_deudas_aeat", nombre: "Certificado deudas AEAT", descripcion: "Certificado de estar al corriente de obligaciones tributarias", requiereCertificado: true, planesDisponibles: ["profesional", "plus"] },
  { tipo: "certificado_ss", nombre: "Certificado Seguridad Social", descripcion: "Certificado de estar al corriente con la Seguridad Social", requiereCertificado: true, planesDisponibles: ["profesional", "plus"] },
  { tipo: "modelo_036", nombre: "Modelo 036", descripcion: "Declaración censal de alta, modificación o baja", requiereCertificado: true, planesDisponibles: ["profesional", "plus"] },
  { tipo: "apoderamiento", nombre: "Apoderamiento AAPP", descripcion: "Documento de apoderamiento ante Administraciones Públicas", requiereCertificado: true, planesDisponibles: ["profesional", "plus"] },
  { tipo: "recurso_alzada", nombre: "Recurso de alzada", descripcion: "Modelo de recurso de alzada ante la Administración", requiereCertificado: false, planesDisponibles: ["plus"] },
  { tipo: "escrito_alegaciones", nombre: "Escrito de alegaciones", descripcion: "Escrito de alegaciones frente a requerimiento o sanción", requiereCertificado: false, planesDisponibles: ["plus"] },
  { tipo: "solicitud_aplazamiento", nombre: "Solicitud aplazamiento", descripcion: "Solicitud de aplazamiento de deuda tributaria", requiereCertificado: true, planesDisponibles: ["plus"] },
  { tipo: "mandato_representacion", nombre: "Mandato representación", descripcion: "Mandato de representación profesional ante organismos", requiereCertificado: true, planesDisponibles: ["plus"] }
];
function ModalGenerarDocumento({
  plantilla,
  certificados,
  generando,
  exito,
  onGenerar,
  onCerrar
}) {
  const [certificadoId, setCertificadoId] = reactExports.useState("");
  useEscapeKey(true, onCerrar);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-2xl w-full max-w-md", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Generar documento" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-6 space-y-4", children: exito ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center py-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-12 h-12 text-green-400 mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-white font-medium", children: "Documento generado" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-medium text-white", children: plantilla.nombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-1", children: plantilla.descripcion })
      ] }),
      plantilla.requiereCertificado && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1.5", children: "Certificado asociado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: certificadoId,
            onChange: (e) => setCertificadoId(e.target.value),
            className: "w-full px-3 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                      focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Seleccionar certificado..." }),
              certificados.map((c) => /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: c.id, children: [
                c.nombreTitular,
                " — ",
                c.dniCif
              ] }, c.id))
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => onGenerar(plantilla.tipo, certificadoId || void 0),
          disabled: generando || plantilla.requiereCertificado && !certificadoId,
          className: "w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-acento-500 hover:bg-acento-400\n                  disabled:opacity-50 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
          children: [
            generando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4" }),
            generando ? "Generando..." : "Generar PDF"
          ]
        }
      )
    ] }) })
  ] }) });
}
export {
  PaginaDocumentos
};
