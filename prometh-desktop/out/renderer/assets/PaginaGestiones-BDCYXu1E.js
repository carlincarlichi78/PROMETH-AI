import { r as reactExports, j as jsxRuntimeExports, X, B as Bell, P as Plus, e as SquareCheckBig, m as Search, H as obtenerPerfilApi, L as Lock, F as FolderOpen } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { a as actualizarGestionApi, c as crearGestionApi, l as listarGestionesApi, o as obtenerGestionApi, e as eliminarGestionApi, b as asignarNotificacionesGestionApi } from "./gestionesServicio-z25W8jIF.js";
import { l as listarUsuariosApi } from "./usuariosServicio-jACWWnfy.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { l as listarNotificacionesApi } from "./notificacionesServicio-B3Srptx0.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
function ModalGestion({ gestion, onCerrar, onGuardado }) {
  useEscapeKey(true, onCerrar);
  const esEdicion = gestion !== null;
  const [nombre, setNombre] = reactExports.useState(gestion?.nombre ?? "");
  const [descripcion, setDescripcion] = reactExports.useState(gestion?.descripcion ?? "");
  const [cliente, setCliente] = reactExports.useState(gestion?.cliente ?? "");
  const [tipo, setTipo] = reactExports.useState(gestion?.tipo ?? "fiscal");
  const [estado, setEstado] = reactExports.useState(gestion?.estado ?? "activa");
  const [responsableId, setResponsableId] = reactExports.useState(gestion?.responsableId ?? "");
  const [usuarios, setUsuarios] = reactExports.useState([]);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  reactExports.useEffect(() => {
    listarUsuariosApi({ limite: 100 }).then((r) => setUsuarios(r.usuarios)).catch(() => {
    });
  }, []);
  const manejarSubmit = async (e) => {
    e.preventDefault();
    if (!nombre.trim()) {
      setError("El nombre es obligatorio");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      if (esEdicion && gestion) {
        await actualizarGestionApi(gestion.id, {
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || null,
          cliente: cliente.trim() || null,
          tipo,
          estado,
          responsableId: responsableId || null
        });
      } else {
        await crearGestionApi({
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || void 0,
          cliente: cliente.trim() || void 0,
          tipo,
          responsableId: responsableId || void 0
        });
      }
      onGuardado();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar la gestión");
    } finally {
      setGuardando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl w-full max-w-lg", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-white", children: esEdicion ? "Editar gestión" : "Nueva gestión" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-500 hover:text-white transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "p-6 space-y-4", children: [
      error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
        error
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: [
          "Nombre ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-red-400", children: "*" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: nombre,
            onChange: (e) => setNombre(e.target.value),
            placeholder: "Nombre de la gestión",
            className: "w-full px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                outline-none focus:ring-2 focus:ring-acento-500/40 placeholder:text-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Descripción" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "textarea",
          {
            value: descripcion,
            onChange: (e) => setDescripcion(e.target.value),
            placeholder: "Descripción opcional",
            rows: 3,
            className: "w-full px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                outline-none focus:ring-2 focus:ring-acento-500/40 placeholder:text-superficie-600 resize-none"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Cliente" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: cliente,
            onChange: (e) => setCliente(e.target.value),
            placeholder: "Nombre del cliente",
            className: "w-full px-3 py-2 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                outline-none focus:ring-2 focus:ring-acento-500/40 placeholder:text-superficie-600"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Tipo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: tipo,
              onChange: (e) => setTipo(e.target.value),
              className: "w-full px-3 py-2 text-sm bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                  text-superficie-200 outline-none focus:ring-2 focus:ring-acento-500/40",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "fiscal", children: "Fiscal" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "laboral", children: "Laboral" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "mercantil", children: "Mercantil" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "administrativo", children: "Administrativo" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "otro", children: "Otro" })
              ]
            }
          )
        ] }),
        esEdicion && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Estado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: estado,
              onChange: (e) => setEstado(e.target.value),
              className: "w-full px-3 py-2 text-sm bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                    text-superficie-200 outline-none focus:ring-2 focus:ring-acento-500/40",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "activa", children: "Activa" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "completada", children: "Completada" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "archivada", children: "Archivada" })
              ]
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Responsable" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: responsableId,
            onChange: (e) => setResponsableId(e.target.value),
            className: "w-full px-3 py-2 text-sm bg-superficie-800/60 border border-white/[0.06] rounded-lg\n                text-superficie-200 outline-none focus:ring-2 focus:ring-acento-500/40",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Sin asignar" }),
              usuarios.map((u) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: u.id, children: u.nombre }, u.id))
            ]
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3 pt-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "button",
            onClick: onCerrar,
            className: "px-4 py-2 text-sm text-superficie-300 hover:text-white border border-white/[0.06] rounded-lg transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "submit",
            disabled: guardando,
            className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400 disabled:opacity-50\n                text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
            children: [
              guardando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
              esEdicion ? "Guardar cambios" : "Crear gestión"
            ]
          }
        )
      ] })
    ] })
  ] }) });
}
const COLORES_TIPO$1 = {
  fiscal: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  laboral: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  mercantil: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  administrativo: "bg-green-500/20 text-green-400 border-green-500/30",
  otro: "bg-superficie-700/50 text-superficie-400 border-white/[0.06]"
};
const ETIQUETAS_TIPO$1 = {
  fiscal: "Fiscal",
  laboral: "Laboral",
  mercantil: "Mercantil",
  administrativo: "Administrativo",
  otro: "Otro"
};
const COLORES_ESTADO = {
  activa: "bg-green-500/20 text-green-400",
  completada: "bg-blue-500/20 text-blue-400",
  archivada: "bg-superficie-700/50 text-superficie-500"
};
const ETIQUETAS_ESTADO$1 = {
  activa: "Activa",
  completada: "Completada",
  archivada: "Archivada"
};
function ModalDetalleGestion({
  gestion,
  esAdmin,
  onCerrar,
  onEditar,
  onArchivar,
  onAsignarNotificaciones
}) {
  useEscapeKey(true, onCerrar);
  const [confirmandoArchivar, setConfirmandoArchivar] = reactExports.useState(false);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl w-full max-w-2xl max-h-[90vh] flex flex-col", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-white", children: gestion.nombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_TIPO$1[gestion.tipo]}`, children: ETIQUETAS_TIPO$1[gestion.tipo] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_ESTADO[gestion.estado]}`, children: ETIQUETAS_ESTADO$1[gestion.estado] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-500 hover:text-white transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 overflow-y-auto p-6 space-y-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Cliente" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200", children: gestion.cliente ?? "—" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Responsable" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200", children: gestion.nombreResponsable ?? "—" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Creado por" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200", children: gestion.nombreCreador ?? "—" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Fecha de creación" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200", children: formatearFecha(gestion.creadoEn) })
        ] })
      ] }),
      gestion.descripcion && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Descripción" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300", children: gestion.descripcion })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-4 h-4 text-superficie-500" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm font-medium text-superficie-300", children: [
              "Notificaciones (",
              gestion.notificaciones.length,
              ")"
            ] })
          ] }),
          esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: onAsignarNotificaciones,
              className: "flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-acento-400 border border-acento-500/20\n                    bg-acento-500/10 hover:bg-acento-500/20 rounded-lg transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-3.5 h-3.5" }),
                "Asignar"
              ]
            }
          )
        ] }),
        gestion.notificaciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 py-4 text-center", children: "No hay notificaciones asignadas" }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1", children: gestion.notificaciones.map((n) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: "flex items-center gap-3 px-3 py-2.5 rounded-lg bg-superficie-800/40 border border-white/[0.04]",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(SquareCheckBig, { className: "w-4 h-4 text-superficie-500 shrink-0" }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 truncate", children: n.administracion }),
                n.contenido && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 truncate mt-0.5", children: n.contenido })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 whitespace-nowrap", children: formatearFecha(n.fechaDeteccion) })
            ]
          },
          n.id
        )) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-t border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: esAdmin && gestion.estado !== "archivada" && (confirmandoArchivar ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-400", children: "¿Confirmar archivo?" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onArchivar,
            className: "px-3 py-1.5 text-xs font-medium text-red-400 border border-red-500/20 bg-red-500/10 hover:bg-red-500/20 rounded-lg transition-colors",
            children: "Sí, archivar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setConfirmandoArchivar(false),
            className: "px-3 py-1.5 text-xs text-superficie-400 hover:text-white transition-colors",
            children: "Cancelar"
          }
        )
      ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setConfirmandoArchivar(true),
          className: "px-3 py-1.5 text-xs font-medium text-superficie-400 hover:text-red-400 border border-white/[0.06]\n                    hover:border-red-500/20 rounded-lg transition-colors",
          children: "Archivar"
        }
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "px-4 py-2 text-sm text-superficie-300 hover:text-white border border-white/[0.06] rounded-lg transition-colors",
            children: "Cerrar"
          }
        ),
        esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onEditar,
            className: "px-4 py-2 bg-acento-500 hover:bg-acento-400 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
            children: "Editar"
          }
        )
      ] })
    ] })
  ] }) });
}
function ModalAsignarNotificaciones({
  notificacionesActuales,
  onCerrar,
  onGuardado
}) {
  useEscapeKey(true, onCerrar);
  const [notificaciones, setNotificaciones] = reactExports.useState([]);
  const [seleccionadas, setSeleccionadas] = reactExports.useState(
    new Set(notificacionesActuales.map((n) => n.id))
  );
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [cargando, setCargando] = reactExports.useState(true);
  const [guardando, setGuardando] = reactExports.useState(false);
  reactExports.useEffect(() => {
    listarNotificacionesApi({ limite: 100 }).then((r) => setNotificaciones(r.notificaciones)).catch(() => {
    }).finally(() => setCargando(false));
  }, []);
  const notifFiltradas = notificaciones.filter(
    (n) => n.administracion.toLowerCase().includes(busqueda.toLowerCase()) || (n.contenido ?? "").toLowerCase().includes(busqueda.toLowerCase())
  );
  const toggleSeleccion = (id) => {
    setSeleccionadas((prev) => {
      const nuevo = new Set(prev);
      if (nuevo.has(id)) nuevo.delete(id);
      else nuevo.add(id);
      return nuevo;
    });
  };
  const manejarGuardar = async () => {
    setGuardando(true);
    await onGuardado(Array.from(seleccionadas));
    setGuardando(false);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.06] rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-white", children: "Asignar notificaciones" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "text-superficie-500 hover:text-white transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "px-6 py-3 border-b border-white/[0.04]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "text",
          value: busqueda,
          onChange: (e) => setBusqueda(e.target.value),
          placeholder: "Buscar notificaciones...",
          className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
        }
      )
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex-1 overflow-y-auto p-4 space-y-1", children: cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center py-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-5 h-5 text-superficie-500 animate-spin" }) }) : notifFiltradas.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 text-center py-8", children: "Sin notificaciones" }) : notifFiltradas.map((n) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => toggleSeleccion(n.id),
        className: `w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${seleccionadas.has(n.id) ? "bg-acento-500/10 border border-acento-500/20" : "border border-transparent hover:bg-white/[0.03]"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: `w-4 h-4 mt-0.5 rounded border flex items-center justify-center shrink-0 transition-colors ${seleccionadas.has(n.id) ? "bg-acento-500 border-acento-500" : "border-white/20"}`,
              children: seleccionadas.has(n.id) && /* @__PURE__ */ jsxRuntimeExports.jsx("svg", { className: "w-2.5 h-2.5 text-superficie-950", fill: "currentColor", viewBox: "0 0 12 12", children: /* @__PURE__ */ jsxRuntimeExports.jsx("path", { d: "M10 3L5 8.5 2 5.5", stroke: "currentColor", strokeWidth: "1.5", fill: "none", strokeLinecap: "round", strokeLinejoin: "round" }) })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-200 truncate", children: n.administracion }),
            n.contenido && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 truncate mt-0.5", children: n.contenido })
          ] })
        ]
      },
      n.id
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-6 py-4 border-t border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs text-superficie-500", children: [
        seleccionadas.size,
        " seleccionadas"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            className: "px-4 py-2 text-sm text-superficie-300 hover:text-white border border-white/[0.06] rounded-lg transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarGuardar,
            disabled: guardando,
            className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400 disabled:opacity-50\n                text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
            children: [
              guardando && /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }),
              "Guardar"
            ]
          }
        )
      ] })
    ] })
  ] }) });
}
const COLORES_TIPO = {
  fiscal: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  laboral: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  mercantil: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  administrativo: "bg-green-500/20 text-green-400 border-green-500/30",
  otro: "bg-superficie-700/50 text-superficie-400 border-white/[0.06]"
};
const ETIQUETAS_TIPO = {
  fiscal: "Fiscal",
  laboral: "Laboral",
  mercantil: "Mercantil",
  administrativo: "Administrativo",
  otro: "Otro"
};
const COLORES_ESTADO_GESTION = {
  activa: "bg-green-500/20 text-green-400",
  completada: "bg-blue-500/20 text-blue-400",
  archivada: "bg-superficie-700/50 text-superficie-500"
};
const ETIQUETAS_ESTADO = {
  activa: "Activa",
  completada: "Completada",
  archivada: "Archivada"
};
const FILTROS_TIPO = [
  { valor: "", etiqueta: "Todas" },
  { valor: "fiscal", etiqueta: "Fiscal" },
  { valor: "laboral", etiqueta: "Laboral" },
  { valor: "mercantil", etiqueta: "Mercantil" },
  { valor: "administrativo", etiqueta: "Administrativo" },
  { valor: "otro", etiqueta: "Otro" }
];
const FILTROS_ESTADO = [
  { valor: "", etiqueta: "Todos" },
  { valor: "activa", etiqueta: "Activas" },
  { valor: "completada", etiqueta: "Completadas" },
  { valor: "archivada", etiqueta: "Archivadas" }
];
function PaginaGestiones() {
  const [gestiones, setGestiones] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [filtroTipo, setFiltroTipo] = reactExports.useState("");
  const [filtroEstado, setFiltroEstado] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const [plan, setPlan] = reactExports.useState("basico");
  const [rol, setRol] = reactExports.useState("asesor");
  const [modalFormAbierto, setModalFormAbierto] = reactExports.useState(false);
  const [gestionEditar, setGestionEditar] = reactExports.useState(null);
  const [gestionDetalle, setGestionDetalle] = reactExports.useState(null);
  const [modalDetalleAbierto, setModalDetalleAbierto] = reactExports.useState(false);
  const [modalAsignarAbierto, setModalAsignarAbierto] = reactExports.useState(false);
  reactExports.useEffect(() => {
    obtenerPerfilApi().then((perfil) => {
      setPlan(perfil.organizacion.plan);
      setRol(perfil.rol);
    }).catch(() => {
    });
  }, []);
  const esAdmin = rol === "admin";
  const planPermitido = plan === "profesional" || plan === "plus";
  const cargarGestiones = reactExports.useCallback(async () => {
    try {
      setError(null);
      const resultado = await listarGestionesApi({
        tipo: filtroTipo || void 0,
        estado: filtroEstado || void 0,
        busqueda: busqueda || void 0,
        pagina,
        limite: 20
      });
      setGestiones(resultado.gestiones);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar gestiones");
    }
  }, [filtroTipo, filtroEstado, busqueda, pagina]);
  reactExports.useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      await cargarGestiones();
      setCargando(false);
    };
    cargar();
  }, [cargarGestiones]);
  const manejarBuscar = () => {
    setPagina(1);
    cargarGestiones();
  };
  const manejarAbrirCrear = () => {
    setGestionEditar(null);
    setModalFormAbierto(true);
  };
  const manejarAbrirEditar = (gestion) => {
    setGestionEditar(gestion);
    setModalDetalleAbierto(false);
    setModalFormAbierto(true);
  };
  const manejarVerDetalle = async (gestion) => {
    try {
      const detalle = await obtenerGestionApi(gestion.id);
      setGestionDetalle(detalle);
      setModalDetalleAbierto(true);
    } catch {
      setError("Error al cargar el detalle de la gestión");
    }
  };
  const manejarGuardado = () => {
    setModalFormAbierto(false);
    setGestionEditar(null);
    cargarGestiones();
  };
  const manejarArchivar = async (id) => {
    try {
      await eliminarGestionApi(id);
      setModalDetalleAbierto(false);
      setGestionDetalle(null);
      cargarGestiones();
    } catch {
      setError("Error al archivar la gestión");
    }
  };
  const manejarAsignarNotificaciones = async (ids) => {
    if (!gestionDetalle) return;
    try {
      await asignarNotificacionesGestionApi(gestionDetalle.id, ids);
      const detalle = await obtenerGestionApi(gestionDetalle.id);
      setGestionDetalle(detalle);
      setModalAsignarAbierto(false);
      cargarGestiones();
    } catch {
      setError("Error al asignar notificaciones");
    }
  };
  const manejarCambioTipo = (valor) => {
    setFiltroTipo(valor);
    setPagina(1);
  };
  const manejarCambioEstado = (valor) => {
    setFiltroEstado(valor);
    setPagina(1);
  };
  if (!planPermitido && !cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6", children: /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Gestiones" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-20 px-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-16 h-16 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-5", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Lock, { className: "w-8 h-8 text-superficie-500" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-superficie-200 mb-2", children: "Funcionalidad exclusiva" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 text-center max-w-md mb-6", children: "El módulo de Gestiones está disponible en los planes Profesional y Plus. Organiza tus expedientes, asigna notificaciones y lleva el seguimiento de cada caso." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "a",
          {
            href: "/app/suscripcion",
            className: "px-5 py-2.5 bg-acento-500 hover:bg-acento-400 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
            children: "Ver planes"
          }
        )
      ] })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Gestiones" }),
      esAdmin && planPermitido && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarAbrirCrear,
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n              text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Nueva gestión"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-3 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: FILTROS_TIPO.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => manejarCambioTipo(f.valor),
          className: `px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${filtroTipo === f.valor ? "bg-acento-500/10 text-acento-400 border-acento-500/20" : "text-superficie-400 border-white/[0.06] hover:bg-white/[0.05] hover:text-superficie-200"}`,
          children: f.etiqueta
        },
        f.valor
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "select",
          {
            value: filtroEstado,
            onChange: (e) => manejarCambioEstado(e.target.value),
            className: "px-3 py-2 text-sm bg-superficie-800/60 border border-white/[0.06] rounded-lg\n              text-superficie-200 outline-none focus:ring-2 focus:ring-acento-500/40",
            children: FILTROS_ESTADO.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: f.valor, children: [
              "Estado: ",
              f.etiqueta
            ] }, f.valor))
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: busqueda,
              onChange: (e) => setBusqueda(e.target.value),
              onKeyDown: (e) => e.key === "Enter" && manejarBuscar(),
              placeholder: "Buscar gestiones...",
              className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-3 py-2 cristal-sutil rounded-lg text-sm text-superficie-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(FolderOpen, { className: "w-4 h-4 text-superficie-500" }),
          total,
          " gestiones"
        ] })
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: cargando ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Cargando gestiones..." })
    ] }) : gestiones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(FolderOpen, { className: "w-7 h-7 text-superficie-500" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "No hay gestiones" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Crea una nueva gestión para empezar a organizar tus expedientes" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Nombre" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Cliente" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Tipo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Responsable" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Notificaciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: gestiones.map((gestion) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "tr",
        {
          className: "hover:bg-white/[0.02] transition-colors cursor-pointer",
          onClick: () => manejarVerDetalle(gestion),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-5 py-4", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium text-superficie-100", children: gestion.nombre }),
              gestion.descripcion && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5 line-clamp-1", children: gestion.descripcion })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: gestion.cliente ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${COLORES_TIPO[gestion.tipo]}`, children: ETIQUETAS_TIPO[gestion.tipo] }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_ESTADO_GESTION[gestion.estado]}`, children: ETIQUETAS_ESTADO[gestion.estado] }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: gestion.nombreResponsable ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 text-superficie-400", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "w-3.5 h-3.5 text-superficie-500" }),
              gestion.totalNotificaciones ?? 0
            ] }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap", children: formatearFecha(gestion.creadoEn) })
          ]
        },
        gestion.id
      )) })
    ] }) }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mt-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Pagina ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " gestiones)"
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
    modalFormAbierto && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalGestion,
      {
        gestion: gestionEditar,
        onCerrar: () => {
          setModalFormAbierto(false);
          setGestionEditar(null);
        },
        onGuardado: manejarGuardado
      }
    ),
    modalDetalleAbierto && gestionDetalle && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalDetalleGestion,
      {
        gestion: gestionDetalle,
        esAdmin,
        onCerrar: () => {
          setModalDetalleAbierto(false);
          setGestionDetalle(null);
        },
        onEditar: () => manejarAbrirEditar(gestionDetalle),
        onArchivar: () => manejarArchivar(gestionDetalle.id),
        onAsignarNotificaciones: () => setModalAsignarAbierto(true)
      }
    ),
    modalAsignarAbierto && gestionDetalle && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalAsignarNotificaciones,
      {
        notificacionesActuales: gestionDetalle.notificaciones,
        onCerrar: () => setModalAsignarAbierto(false),
        onGuardado: manejarAsignarNotificaciones
      }
    )
  ] });
}
export {
  PaginaGestiones
};
