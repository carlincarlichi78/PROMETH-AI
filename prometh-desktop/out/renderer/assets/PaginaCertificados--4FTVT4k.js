import { c as createLucideIcon, r as reactExports, j as jsxRuntimeExports, X, h as COLORES_ETIQUETA, i as esquemaActualizarCertificado, k as esquemaCrearCertificado, g as ErrorApiCliente, u as useNavigate, l as useEsDesktop, m as Search, n as ChevronDown, o as Upload, P as Plus } from "./index-DMbE3NR1.js";
import { e as estaCaducado, a as estaPorCaducar, f as formatearFecha } from "./index-BvWBIJCO.js";
import { a as actualizarCertificadoApi, c as crearCertificadoApi, i as importarCertificadoP12Api, l as listarCertificadosApi, e as eliminarCertificadoApi } from "./certificadosServicio-DtEVLLjT.js";
import { c as crearEtiquetaApi, a as actualizarEtiquetaApi, e as eliminarEtiquetaApi, b as asignarEtiquetasApi, l as listarEtiquetasApi } from "./etiquetasServicio-dQOn1U3c.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { T as Tag } from "./tag-wvcc-Qrp.js";
import { P as Play } from "./play-B9P3AzSW.js";
import { E as EllipsisVertical } from "./ellipsis-vertical-D4mt2YF7.js";
import { P as Pencil } from "./pencil-BuwvL_tU.js";
import { C as Copy } from "./copy-BxtWXfxP.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Folder = createLucideIcon("Folder", [
  [
    "path",
    {
      d: "M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z",
      key: "1kt360"
    }
  ]
]);
function ModalGestionEtiquetas({
  onCerrar,
  etiquetas,
  onCambio
}) {
  const [nombre, setNombre] = reactExports.useState("");
  const [colorSeleccionado, setColorSeleccionado] = reactExports.useState("#6B7280");
  const [cargando, setCargando] = reactExports.useState(false);
  const [editandoId, setEditandoId] = reactExports.useState(null);
  const [nombreEdicion, setNombreEdicion] = reactExports.useState("");
  const [colorEdicion, setColorEdicion] = reactExports.useState("");
  const [error, setError] = reactExports.useState(null);
  const crearEtiqueta = async () => {
    if (!nombre.trim()) return;
    setCargando(true);
    setError(null);
    try {
      await crearEtiquetaApi({ nombre: nombre.trim(), color: colorSeleccionado });
      setNombre("");
      onCambio();
    } catch {
      setError("Error al crear etiqueta");
    } finally {
      setCargando(false);
    }
  };
  const guardarEdicion = async (id) => {
    if (!nombreEdicion.trim()) return;
    setCargando(true);
    setError(null);
    try {
      await actualizarEtiquetaApi(id, {
        nombre: nombreEdicion.trim(),
        color: colorEdicion
      });
      setEditandoId(null);
      onCambio();
    } catch {
      setError("Error al actualizar etiqueta");
    } finally {
      setCargando(false);
    }
  };
  const eliminar = async (id) => {
    setCargando(true);
    setError(null);
    try {
      await eliminarEtiquetaApi(id);
      onCambio();
    } catch {
      setError("Error al eliminar etiqueta");
    } finally {
      setCargando(false);
    }
  };
  const iniciarEdicion = (et) => {
    setEditandoId(et.id);
    setNombreEdicion(et.nombre);
    setColorEdicion(et.color);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-md mx-4 p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Gestionar etiquetas" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "p-1 text-superficie-400 hover:text-white rounded-lg hover:bg-white/[0.05]",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" })
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-3 p-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400", children: error }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-2", children: "Nueva etiqueta" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2 mb-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            value: nombre,
            onChange: (e) => setNombre(e.target.value),
            onKeyDown: (e) => e.key === "Enter" && crearEtiqueta(),
            placeholder: "Nombre de etiqueta...",
            className: "flex-1 px-3 py-2 rounded-lg border border-white/[0.06] text-sm text-superficie-100\n                outline-none focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: crearEtiqueta,
            disabled: cargando || !nombre.trim(),
            className: "px-4 py-2 bg-acento-500 text-superficie-950 rounded-lg text-sm font-semibold\n                hover:bg-acento-400 disabled:opacity-50 transition-colors whitespace-nowrap",
            children: "Crear"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2 flex-wrap", children: COLORES_ETIQUETA.map((color) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setColorSeleccionado(color),
          className: `w-6 h-6 rounded-full border-2 transition-all ${colorSeleccionado === color ? "border-white scale-110" : "border-transparent hover:scale-105"}`,
          style: { backgroundColor: color },
          title: color
        },
        color
      )) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1.5 max-h-64 overflow-y-auto", children: [
      etiquetas.length === 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-500 text-center py-4", children: "No hay etiquetas creadas" }),
      etiquetas.map((et) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: "flex items-center justify-between p-2.5 rounded-lg bg-white/[0.03] hover:bg-white/[0.05] transition-colors",
          children: editandoId === et.id ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                value: nombreEdicion,
                onChange: (e) => setNombreEdicion(e.target.value),
                onKeyDown: (e) => e.key === "Enter" && guardarEdicion(et.id),
                className: "flex-1 px-2 py-1 rounded border border-white/[0.06] text-sm text-superficie-100\n                      bg-superficie-800/60 outline-none focus:ring-1 focus:ring-acento-500/40"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1", children: COLORES_ETIQUETA.map((c) => /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => setColorEdicion(c),
                className: `w-4 h-4 rounded-full border ${colorEdicion === c ? "border-white" : "border-transparent"}`,
                style: { backgroundColor: c }
              },
              c
            )) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => guardarEdicion(et.id),
                disabled: cargando,
                className: "text-acento-400 hover:text-acento-300 text-xs font-medium",
                children: "Guardar"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => setEditandoId(null),
                className: "text-superficie-500 hover:text-superficie-300 text-xs",
                children: "Cancelar"
              }
            )
          ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "span",
                {
                  className: "w-3 h-3 rounded-full flex-shrink-0",
                  style: { backgroundColor: et.color }
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-200", children: et.nombre })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => iniciarEdicion(et),
                  className: "text-superficie-500 hover:text-superficie-300 text-xs px-1.5 py-0.5",
                  children: "Editar"
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => eliminar(et.id),
                  disabled: cargando,
                  className: "text-red-400 hover:text-red-300 text-xs px-1.5 py-0.5",
                  children: "Eliminar"
                }
              )
            ] })
          ] })
        },
        et.id
      ))
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-400 animate-spin" }) })
  ] }) });
}
const FORMULARIO_VACIO = {
  nombreTitular: "",
  dniCif: "",
  numeroSerie: "",
  emisor: "",
  organizacion: "",
  fechaExpedicion: "",
  fechaVencimiento: ""
};
function crearFormularioDesde(cert) {
  return {
    nombreTitular: cert.nombreTitular,
    dniCif: cert.dniCif,
    numeroSerie: cert.numeroSerie ?? "",
    emisor: cert.emisor ?? "",
    organizacion: cert.organizacion ?? "",
    fechaExpedicion: cert.fechaExpedicion ? cert.fechaExpedicion.slice(0, 10) : "",
    fechaVencimiento: cert.fechaVencimiento ? cert.fechaVencimiento.slice(0, 10) : ""
  };
}
const estiloInput = (conError) => `w-full px-3 py-2 rounded-lg border text-sm text-superficie-100 outline-none transition-colors
  focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 placeholder:text-superficie-600
  ${conError ? "border-red-500/50 bg-red-500/5" : "border-white/[0.06] bg-superficie-800/60 hover:border-white/10"}`;
function ModalCertificado({
  certificado,
  etiquetasDisponibles,
  onCerrar,
  onGuardado
}) {
  const modoEditar = !!certificado;
  const [formulario, setFormulario] = reactExports.useState(
    certificado ? crearFormularioDesde(certificado) : FORMULARIO_VACIO
  );
  const [errores, setErrores] = reactExports.useState({});
  const [errorGeneral, setErrorGeneral] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(false);
  const [etiquetasSeleccionadas, setEtiquetasSeleccionadas] = reactExports.useState(
    certificado?.etiquetas?.map((e) => e.id) ?? []
  );
  useEscapeKey(true, onCerrar);
  const toggleEtiqueta = (id) => {
    setEtiquetasSeleccionadas(
      (prev) => prev.includes(id) ? prev.filter((e) => e !== id) : [...prev, id]
    );
  };
  const actualizarCampo = (campo, valor) => {
    setFormulario((prev) => ({ ...prev, [campo]: valor }));
    setErrores((prev) => ({ ...prev, [campo]: "" }));
    setErrorGeneral(null);
  };
  const manejarSubmit = async (e) => {
    e.preventDefault();
    const datosBase = {
      nombreTitular: formulario.nombreTitular,
      dniCif: formulario.dniCif,
      ...formulario.numeroSerie ? { numeroSerie: formulario.numeroSerie } : {},
      ...formulario.emisor ? { emisor: formulario.emisor } : {},
      ...formulario.organizacion ? { organizacion: formulario.organizacion } : {},
      ...formulario.fechaExpedicion ? { fechaExpedicion: new Date(formulario.fechaExpedicion).toISOString() } : {}
    };
    const datosParaValidar = modoEditar ? {
      ...datosBase,
      fechaVencimiento: formulario.fechaVencimiento ? new Date(formulario.fechaVencimiento).toISOString() : void 0
    } : {
      ...datosBase,
      fechaVencimiento: formulario.fechaVencimiento ? new Date(formulario.fechaVencimiento).toISOString() : ""
    };
    const esquema = modoEditar ? esquemaActualizarCertificado : esquemaCrearCertificado;
    const resultado = esquema.safeParse(datosParaValidar);
    if (!resultado.success) {
      const erroresZod = {};
      resultado.error.errors.forEach((err) => {
        erroresZod[err.path[0]] = err.message;
      });
      setErrores(erroresZod);
      return;
    }
    setCargando(true);
    setErrorGeneral(null);
    try {
      if (modoEditar && certificado) {
        await actualizarCertificadoApi(certificado.id, resultado.data);
        await asignarEtiquetasApi(certificado.id, etiquetasSeleccionadas);
      } else {
        const certCreado = await crearCertificadoApi(resultado.data);
        if (etiquetasSeleccionadas.length > 0) {
          await asignarEtiquetasApi(certCreado.id, etiquetasSeleccionadas);
        }
      }
      onGuardado();
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setErrorGeneral(err.message);
      } else {
        setErrorGeneral(modoEditar ? "Error al actualizar certificado" : "Error al crear certificado");
      }
    } finally {
      setCargando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-lg mx-4 p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: modoEditar ? "Editar Certificado" : "Nuevo Certificado" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "p-1 text-superficie-400 hover:text-white rounded-lg hover:bg-white/[0.05]",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" })
        }
      )
    ] }),
    errorGeneral && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: errorGeneral }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CampoModal,
        {
          etiqueta: "Nombre del titular *",
          valor: formulario.nombreTitular,
          onChange: (v) => actualizarCampo("nombreTitular", v),
          placeholder: "Empresa Ejemplo S.L.",
          error: errores.nombreTitular
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CampoModal,
        {
          etiqueta: "DNI / CIF *",
          valor: formulario.dniCif,
          onChange: (v) => actualizarCampo("dniCif", v),
          placeholder: "B12345678",
          error: errores.dniCif
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          CampoModal,
          {
            etiqueta: "Emisor",
            valor: formulario.emisor,
            onChange: (v) => actualizarCampo("emisor", v),
            placeholder: "FNMT",
            error: errores.emisor
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          CampoModal,
          {
            etiqueta: "N.º Serie",
            valor: formulario.numeroSerie,
            onChange: (v) => actualizarCampo("numeroSerie", v),
            placeholder: "SN-2025-001",
            error: errores.numeroSerie
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CampoModal,
        {
          etiqueta: "Organización emisora",
          valor: formulario.organizacion,
          onChange: (v) => actualizarCampo("organizacion", v),
          placeholder: "Fábrica Nacional de Moneda y Timbre",
          error: errores.organizacion
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          CampoModal,
          {
            etiqueta: "Fecha expedición",
            valor: formulario.fechaExpedicion,
            onChange: (v) => actualizarCampo("fechaExpedicion", v),
            tipo: "date",
            error: errores.fechaExpedicion
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          CampoModal,
          {
            etiqueta: "Fecha vencimiento *",
            valor: formulario.fechaVencimiento,
            onChange: (v) => actualizarCampo("fechaVencimiento", v),
            tipo: "date",
            error: errores.fechaVencimiento
          }
        )
      ] }),
      etiquetasDisponibles.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx(
        SeccionEtiquetas,
        {
          etiquetasDisponibles,
          etiquetasSeleccionadas,
          onToggle: toggleEtiqueta
        }
      ),
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
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "submit",
            disabled: cargando,
            className: "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500\n                hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
            children: [
              cargando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
              cargando ? modoEditar ? "Guardando..." : "Creando..." : modoEditar ? "Guardar cambios" : "Crear certificado"
            ]
          }
        )
      ] })
    ] })
  ] }) });
}
function CampoModal({
  etiqueta,
  valor,
  onChange,
  placeholder,
  error,
  tipo = "text"
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: etiqueta }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "input",
      {
        type: tipo,
        value: valor,
        onChange: (e) => onChange(e.target.value),
        placeholder,
        className: estiloInput(!!error)
      }
    ),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-xs text-red-400", children: error })
  ] });
}
function SeccionEtiquetas({
  etiquetasDisponibles,
  etiquetasSeleccionadas,
  onToggle
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1.5", children: "Etiquetas" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: etiquetasDisponibles.map((et) => {
      const seleccionada = etiquetasSeleccionadas.includes(et.id);
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          type: "button",
          onClick: () => onToggle(et.id),
          className: `inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium border transition-all ${seleccionada ? "ring-1 ring-white/30" : "opacity-60 hover:opacity-100"}`,
          style: {
            backgroundColor: seleccionada ? `${et.color}25` : `${et.color}10`,
            color: et.color,
            borderColor: seleccionada ? `${et.color}50` : `${et.color}20`
          },
          children: et.nombre
        },
        et.id
      );
    }) })
  ] });
}
function ModalImportarP12({ onCerrar, onImportado }) {
  const [archivo, setArchivo] = reactExports.useState(null);
  const [password, setPassword] = reactExports.useState("");
  const [cargando, setCargando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  useEscapeKey(true, onCerrar);
  const manejarSubmit = async (e) => {
    e.preventDefault();
    if (!archivo) {
      setError("Selecciona un archivo .p12 o .pfx");
      return;
    }
    setCargando(true);
    setError(null);
    try {
      await importarCertificadoP12Api(archivo, password);
      onImportado();
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al importar certificado");
      }
    } finally {
      setCargando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-md mx-4 p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Importar Certificado P12/PFX" }),
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
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-2", children: "Archivo certificado *" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "file",
            accept: ".p12,.pfx",
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
          (archivo.size / 1024).toFixed(1),
          " KB)"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: "Contraseña del certificado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "password",
            value: password,
            onChange: (e) => setPassword(e.target.value),
            placeholder: "Contraseña del archivo P12/PFX",
            className: "w-full px-3 py-2 rounded-lg border border-white/[0.06] text-sm\n                text-superficie-100 outline-none focus:ring-2 focus:ring-acento-500/40\n                bg-superficie-800/60 placeholder:text-superficie-600"
          }
        )
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
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "submit",
            disabled: cargando || !archivo,
            className: "flex items-center gap-2 px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500\n                hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
            children: [
              cargando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
              cargando ? "Importando..." : "Importar certificado"
            ]
          }
        )
      ] })
    ] })
  ] }) });
}
const FILTROS = ["Todos", "Activos", "Caducados", "Por caducar"];
function etiquetaVencimiento(fechaVencimiento) {
  if (estaCaducado(fechaVencimiento)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20", children: formatearFecha(fechaVencimiento) });
  }
  if (estaPorCaducar(fechaVencimiento)) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20", children: formatearFecha(fechaVencimiento) });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-superficie-300", children: formatearFecha(fechaVencimiento) });
}
function PaginaCertificados() {
  const [certificados, setCertificados] = reactExports.useState([]);
  const [total, setTotal] = reactExports.useState(0);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [filtroActivo, setFiltroActivo] = reactExports.useState("Todos");
  const [filtroEtiqueta, setFiltroEtiqueta] = reactExports.useState(null);
  const [menuAbierto, setMenuAbierto] = reactExports.useState(null);
  const [modalAbierto, setModalAbierto] = reactExports.useState(null);
  const [certificadoEditar, setCertificadoEditar] = reactExports.useState(null);
  const [etiquetasDisponibles, setEtiquetasDisponibles] = reactExports.useState([]);
  const navegar = useNavigate();
  const esDesktop = useEsDesktop();
  const cargarEtiquetas = reactExports.useCallback(async () => {
    try {
      const resultado = await listarEtiquetasApi();
      setEtiquetasDisponibles(resultado.etiquetas);
    } catch {
    }
  }, []);
  const cargarCertificados = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarCertificadosApi({
        busqueda: busqueda || void 0,
        etiquetaId: filtroEtiqueta ?? void 0,
        limite: 50
      });
      setCertificados(resultado.certificados);
      setTotal(resultado.meta.total);
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al cargar certificados");
      }
    } finally {
      setCargando(false);
    }
  }, [busqueda, filtroEtiqueta]);
  reactExports.useEffect(() => {
    cargarEtiquetas();
  }, [cargarEtiquetas]);
  reactExports.useEffect(() => {
    const timer = setTimeout(cargarCertificados, 300);
    return () => clearTimeout(timer);
  }, [cargarCertificados]);
  const manejarEliminar = async (id) => {
    setMenuAbierto(null);
    try {
      await eliminarCertificadoApi(id);
      await cargarCertificados();
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      }
    }
  };
  const manejarEditar = (cert) => {
    setMenuAbierto(null);
    setCertificadoEditar(cert);
    setModalAbierto("editar");
  };
  const manejarGuardado = () => {
    setModalAbierto(null);
    setCertificadoEditar(null);
    cargarCertificados();
  };
  const manejarDuplicar = async (cert) => {
    setMenuAbierto(null);
    try {
      const datosCopia = {
        nombreTitular: `${cert.nombreTitular} (copia)`,
        dniCif: cert.dniCif,
        fechaVencimiento: cert.fechaVencimiento,
        ...cert.numeroSerie ? { numeroSerie: cert.numeroSerie } : {},
        ...cert.emisor ? { emisor: cert.emisor } : {},
        ...cert.organizacion ? { organizacion: cert.organizacion } : {},
        ...cert.fechaExpedicion ? { fechaExpedicion: cert.fechaExpedicion } : {}
      };
      const nuevoCert = await crearCertificadoApi(datosCopia);
      if (cert.etiquetas && cert.etiquetas.length > 0) {
        await asignarEtiquetasApi(nuevoCert.id, cert.etiquetas.map((e) => e.id));
      }
      await cargarCertificados();
    } catch (err) {
      if (err instanceof ErrorApiCliente) {
        setError(err.message);
      } else {
        setError("Error al duplicar certificado");
      }
    }
  };
  const manejarIniciar = () => {
    navegar("/app/accesos");
  };
  const certificadosFiltrados = certificados.filter((cert) => {
    if (filtroActivo === "Caducados") return estaCaducado(cert.fechaVencimiento);
    if (filtroActivo === "Por caducar")
      return !estaCaducado(cert.fechaVencimiento) && estaPorCaducar(cert.fechaVencimiento);
    if (filtroActivo === "Activos") return cert.activo && !estaCaducado(cert.fechaVencimiento);
    return true;
  });
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "text-xl font-semibold text-white whitespace-nowrap", children: [
        "Mis Certificados (",
        total,
        ")"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-1 items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: busqueda,
              onChange: (e) => setBusqueda(e.target.value),
              placeholder: "Buscar por Nombre, DNI, CIF...",
              className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: filtroActivo,
              onChange: (e) => setFiltroActivo(e.target.value),
              className: "appearance-none pl-3 pr-8 py-2 text-sm text-superficie-200 border border-white/[0.06] rounded-lg\n                outline-none focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 cursor-pointer",
              children: FILTROS.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { className: "bg-superficie-800", children: f }, f))
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500 pointer-events-none" })
        ] }),
        etiquetasDisponibles.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: filtroEtiqueta ?? "",
              onChange: (e) => setFiltroEtiqueta(e.target.value || null),
              className: "appearance-none pl-3 pr-8 py-2 text-sm text-superficie-200 border border-white/[0.06] rounded-lg\n                  outline-none focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 cursor-pointer",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", className: "bg-superficie-800", children: "Todas las etiquetas" }),
                etiquetasDisponibles.map((et) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: et.id, className: "bg-superficie-800", children: et.nombre }, et.id))
              ]
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500 pointer-events-none" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setModalAbierto("etiquetas"),
            title: "Gestionar etiquetas",
            className: "p-2 text-superficie-400 hover:text-acento-400 hover:bg-white/[0.05] rounded-lg transition-colors",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(Tag, { className: "w-4 h-4" })
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalAbierto("importar"),
          className: "flex items-center gap-2 px-4 py-2 border border-white/[0.06] text-superficie-300\n            hover:bg-white/[0.05] text-sm font-medium rounded-lg transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-4 h-4" }),
            "Importar P12/PFX"
          ]
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalAbierto("crear"),
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n            text-superficie-950 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Agregar Certificado"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando certificados..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Certificado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Organización" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Expedición" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Vencimiento" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3.5" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: certificadosFiltrados.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsx("td", { colSpan: 5, className: "px-5 py-12 text-center text-superficie-500 text-sm", children: "No se encontraron certificados" }) }) : certificadosFiltrados.map((cert) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-5 py-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "font-medium text-superficie-100", children: cert.nombreTitular }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-xs text-superficie-500 mt-0.5 font-mono", children: cert.dniCif }),
          cert.etiquetas && cert.etiquetas.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1 mt-1", children: cert.etiquetas.map((et) => /* @__PURE__ */ jsxRuntimeExports.jsx(
            "span",
            {
              className: "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border",
              style: {
                backgroundColor: `${et.color}18`,
                color: et.color,
                borderColor: `${et.color}30`
              },
              children: et.nombre
            },
            et.id
          )) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: cert.emisor ?? "—" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300", children: cert.fechaExpedicion ? formatearFecha(cert.fechaExpedicion) : "—" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: etiquetaVencimiento(cert.fechaVencimiento) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              title: "Acceder a portales",
              onClick: manejarIniciar,
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-acento-400\n                              border border-acento-500/30 rounded-lg hover:bg-acento-500/10 transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Play, { className: "w-3.5 h-3.5" }),
                "Iniciar"
              ]
            }
          ),
          esDesktop && /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              title: "Archivos",
              className: "p-1.5 text-superficie-500 hover:text-superficie-200 hover:bg-white/[0.05] rounded-lg transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(Folder, { className: "w-4 h-4" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => setMenuAbierto(menuAbierto === cert.id ? null : cert.id),
                className: "p-1.5 text-superficie-500 hover:text-superficie-200 hover:bg-white/[0.05] rounded-lg transition-colors",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(EllipsisVertical, { className: "w-4 h-4" })
              }
            ),
            menuAbierto === cert.id && /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "div",
              {
                className: "absolute right-0 top-full mt-1 w-36 cristal\n                                  rounded-lg shadow-xl shadow-black/40 z-10 py-1",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsxs(
                    "button",
                    {
                      onClick: () => manejarEditar(cert),
                      className: "w-full text-left px-3 py-2 text-sm text-superficie-300 hover:bg-white/[0.05] hover:text-white flex items-center gap-2",
                      children: [
                        /* @__PURE__ */ jsxRuntimeExports.jsx(Pencil, { className: "w-3.5 h-3.5" }),
                        "Editar"
                      ]
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsxs(
                    "button",
                    {
                      onClick: () => manejarDuplicar(cert),
                      className: "w-full text-left px-3 py-2 text-sm text-superficie-300 hover:bg-white/[0.05] hover:text-white flex items-center gap-2",
                      children: [
                        /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "w-3.5 h-3.5" }),
                        "Duplicar"
                      ]
                    }
                  ),
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "button",
                    {
                      onClick: () => manejarEliminar(cert.id),
                      className: "w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/5",
                      children: "Eliminar"
                    }
                  )
                ]
              }
            )
          ] })
        ] }) })
      ] }, cert.id)) })
    ] }) }) }),
    (modalAbierto === "crear" || modalAbierto === "editar") && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalCertificado,
      {
        certificado: modalAbierto === "editar" ? certificadoEditar : null,
        etiquetasDisponibles,
        onCerrar: () => {
          setModalAbierto(null);
          setCertificadoEditar(null);
        },
        onGuardado: manejarGuardado
      }
    ),
    modalAbierto === "importar" && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalImportarP12,
      {
        onCerrar: () => setModalAbierto(null),
        onImportado: () => {
          setModalAbierto(null);
          cargarCertificados();
        }
      }
    ),
    modalAbierto === "etiquetas" && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalGestionEtiquetas,
      {
        onCerrar: () => setModalAbierto(null),
        etiquetas: etiquetasDisponibles,
        onCambio: () => {
          cargarEtiquetas();
          cargarCertificados();
        }
      }
    )
  ] });
}
export {
  PaginaCertificados
};
