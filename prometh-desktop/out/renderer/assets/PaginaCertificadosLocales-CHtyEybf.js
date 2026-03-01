import { r as reactExports, j as jsxRuntimeExports, P as Plus, a as Shield, f as CircleCheckBig, K as Key, am as Monitor, D as Download, o as Upload } from "./index-DMbE3NR1.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
function PaginaCertificadosLocales() {
  const [certificados, setCertificados] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [certActivo, setCertActivo] = reactExports.useState(null);
  const [accionEnCurso, setAccionEnCurso] = reactExports.useState(null);
  const api = window.electronAPI;
  const cargarCertificados = reactExports.useCallback(async () => {
    if (!api) return;
    try {
      setCargando(true);
      setError(null);
      const [instalados, activo] = await Promise.all([
        api.certs.listarInstalados(),
        api.certs.obtenerActivo()
      ]);
      setCertificados(instalados);
      setCertActivo(activo);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando certificados");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargarCertificados();
  }, [cargarCertificados]);
  const activarCert = async (serial) => {
    if (!api) return;
    try {
      setAccionEnCurso(serial);
      await api.certs.activar(serial);
      setCertActivo(serial);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error activando certificado");
    } finally {
      setAccionEnCurso(null);
    }
  };
  const desinstalarCert = async (thumbprint) => {
    if (!api) return;
    try {
      setAccionEnCurso(thumbprint);
      await api.certs.desinstalarDeWindows(thumbprint);
      await cargarCertificados();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desinstalando certificado");
    } finally {
      setAccionEnCurso(null);
    }
  };
  const importarCertificado = async () => {
    if (!api) return;
    try {
      setAccionEnCurso("importar");
      await api.certs.seleccionarArchivo("");
      await cargarCertificados();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error importando certificado");
    } finally {
      setAccionEnCurso(null);
    }
  };
  const exportarCert = async (thumbprint) => {
    if (!api) return;
    try {
      setAccionEnCurso(thumbprint);
      await api.certs.exportarPfx(thumbprint, "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error exportando certificado");
    } finally {
      setAccionEnCurso(null);
    }
  };
  const esCaducado = (validTo) => {
    return new Date(validTo) < /* @__PURE__ */ new Date();
  };
  if (!api) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Certificados locales" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Certificados instalados en el almacen de Windows" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: cargarCertificados,
            disabled: cargando,
            className: "flex items-center gap-2 px-3 py-2 text-sm font-medium text-superficie-300 bg-superficie-800 hover:bg-superficie-700 rounded-lg border border-white/[0.06] transition-colors disabled:opacity-50",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: `w-4 h-4 ${cargando ? "animate-spin" : ""}` }),
              "Actualizar"
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: importarCertificado,
            disabled: accionEnCurso === "importar",
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-acento-500 hover:bg-acento-600 rounded-lg transition-colors disabled:opacity-50",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
              "Importar P12/PFX"
            ]
          }
        )
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto text-red-400 hover:text-red-300", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4" }) })
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-500 animate-spin" }) }),
    !cargando && certificados.length === 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-20", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 flex items-center justify-center mx-auto mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Shield, { className: "w-7 h-7 text-superficie-500" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "No hay certificados instalados" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Importa un archivo P12/PFX para empezar" })
    ] }),
    !cargando && certificados.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid gap-3", children: certificados.map((cert) => {
      const esActivo = cert.serialNumber === certActivo;
      const caducado = esCaducado(cert.validTo);
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: `cristal rounded-xl p-5 border transition-all ${esActivo ? "border-acento-500/30 bg-acento-500/5" : "border-white/[0.06] hover:border-white/[0.1]"}`,
          children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-4", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${esActivo ? "bg-acento-500/20" : "bg-superficie-800"}`, children: esActivo ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-5 h-5 text-acento-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Key, { className: "w-5 h-5 text-superficie-400" }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-1", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white truncate", children: cert.subject }),
                esActivo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-acento-500/20 text-acento-400", children: "Activo" }),
                caducado && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400", children: "Caducado" })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500 truncate", children: [
                "Emisor: ",
                cert.issuer
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4 mt-2 text-xs text-superficie-400", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
                  "N/S: ",
                  cert.serialNumber
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
                  "Valido: ",
                  new Date(cert.validFrom).toLocaleDateString("es-ES"),
                  " — ",
                  new Date(cert.validTo).toLocaleDateString("es-ES")
                ] }),
                cert.hasPrivateKey && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1 text-emerald-400", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(Key, { className: "w-3 h-3" }),
                  " Clave privada"
                ] })
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1 shrink-0", children: [
              !esActivo && /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => activarCert(cert.serialNumber),
                  disabled: accionEnCurso === cert.serialNumber,
                  className: "p-2 rounded-lg text-superficie-400 hover:text-acento-400 hover:bg-acento-500/10 transition-colors disabled:opacity-50",
                  title: "Activar como certificado principal",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Monitor, { className: "w-4 h-4" })
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => exportarCert(cert.thumbprint),
                  disabled: accionEnCurso === cert.thumbprint,
                  className: "p-2 rounded-lg text-superficie-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors disabled:opacity-50",
                  title: "Exportar PFX",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "w-4 h-4" })
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => desinstalarCert(cert.thumbprint),
                  disabled: accionEnCurso === cert.thumbprint,
                  className: "p-2 rounded-lg text-superficie-400 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50",
                  title: "Desinstalar del almacen",
                  children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" })
                }
              )
            ] })
          ] })
        },
        cert.thumbprint
      );
    }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-6 flex items-center gap-2 text-xs text-superficie-500", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-3.5 h-3.5" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "Los certificados se leen del almacen de Windows (certutil). La importacion instala el PFX directamente." })
    ] })
  ] });
}
export {
  PaginaCertificadosLocales
};
