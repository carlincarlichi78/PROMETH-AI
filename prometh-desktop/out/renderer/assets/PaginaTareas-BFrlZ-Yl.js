import { r as reactExports, j as jsxRuntimeExports, X, P as Plus, m as Search, e as SquareCheckBig } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { a as agregarComentarioApi, o as obtenerTareaApi, e as eliminarTareaApi, b as actualizarTareaApi, c as crearTareaApi, l as listarTareasApi } from "./tareasServicio-CSpOVgN6.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { l as listarEtiquetasApi } from "./etiquetasServicio-dQOn1U3c.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { S as Send } from "./send-mu2rTZak.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
function formatearFechaRelativa(fechaStr) {
  const fecha = new Date(fechaStr);
  const ahora = /* @__PURE__ */ new Date();
  const diffMs = ahora.getTime() - fecha.getTime();
  const diffMin = Math.floor(diffMs / 6e4);
  const diffHoras = Math.floor(diffMs / 36e5);
  const diffDias = Math.floor(diffMs / 864e5);
  if (diffMin < 1) return "ahora";
  if (diffMin < 60) return `hace ${diffMin}min`;
  if (diffHoras < 24) return `hace ${diffHoras}h`;
  if (diffDias < 30) return `hace ${diffDias}d`;
  return fecha.toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}
function obtenerIniciales(nombre) {
  if (!nombre) return "?";
  const partes = nombre.trim().split(/\s+/);
  if (partes.length >= 2) return (partes[0][0] + partes[1][0]).toUpperCase();
  return nombre.slice(0, 2).toUpperCase();
}
const COLORES_AVATAR = [
  "bg-blue-500/20 text-blue-400",
  "bg-emerald-500/20 text-emerald-400",
  "bg-amber-500/20 text-amber-400",
  "bg-purple-500/20 text-purple-400",
  "bg-rose-500/20 text-rose-400",
  "bg-cyan-500/20 text-cyan-400"
];
function colorAvatar(nombre) {
  if (!nombre) return COLORES_AVATAR[0];
  let hash = 0;
  for (const char of nombre) hash = (hash << 5) - hash + char.charCodeAt(0) | 0;
  return COLORES_AVATAR[Math.abs(hash) % COLORES_AVATAR.length];
}
function PanelComentarios({
  tareaId,
  comentarios,
  onComentarioAgregado
}) {
  const [nuevoComentario, setNuevoComentario] = reactExports.useState("");
  const [enviando, setEnviando] = reactExports.useState(false);
  const [errorEnvio, setErrorEnvio] = reactExports.useState(null);
  const listaRef = reactExports.useRef(null);
  reactExports.useEffect(() => {
    if (listaRef.current) {
      listaRef.current.scrollTop = listaRef.current.scrollHeight;
    }
  }, [comentarios.length]);
  const manejarEnviar = async () => {
    const contenido = nuevoComentario.trim();
    if (!contenido) return;
    setEnviando(true);
    setErrorEnvio(null);
    try {
      await agregarComentarioApi(tareaId, { contenido });
      setNuevoComentario("");
      onComentarioAgregado();
    } catch (err) {
      setErrorEnvio(err instanceof Error ? err.message : "Error al enviar comentario");
    } finally {
      setEnviando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("h4", { className: "text-xs font-semibold text-superficie-400 uppercase tracking-wide mb-3", children: [
      "Comentarios (",
      comentarios.length,
      ")"
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        ref: listaRef,
        className: "max-h-48 overflow-y-auto space-y-3 mb-3",
        children: comentarios.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 text-center py-4", children: "Sin comentarios todavia" }) : comentarios.map((c) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2.5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "div",
            {
              className: `w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-[10px] font-semibold ${colorAvatar(c.nombreUsuario)}`,
              children: obtenerIniciales(c.nombreUsuario)
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-baseline gap-2", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium text-superficie-200", children: c.nombreUsuario ?? "Usuario" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] text-superficie-600", children: formatearFechaRelativa(c.creadoEn) })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-300 mt-0.5 leading-relaxed whitespace-pre-wrap", children: c.contenido })
          ] })
        ] }, c.id))
      }
    ),
    errorEnvio && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-red-400 mb-2", children: errorEnvio }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "text",
          value: nuevoComentario,
          onChange: (e) => setNuevoComentario(e.target.value),
          onKeyDown: (e) => e.key === "Enter" && !e.shiftKey && manejarEnviar(),
          placeholder: "Escribe un comentario...",
          className: "flex-1 px-3 py-1.5 text-xs text-superficie-100 border border-white/[0.08] rounded-lg\n            bg-superficie-800 placeholder:text-superficie-600 focus:outline-none focus:border-acento-500/50"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: manejarEnviar,
          disabled: enviando || !nuevoComentario.trim(),
          className: "p-1.5 rounded-lg bg-acento-500/10 text-acento-400 hover:bg-acento-500/20\n            disabled:opacity-30 transition-colors",
          children: enviando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3.5 h-3.5 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { className: "w-3.5 h-3.5" })
        }
      )
    ] })
  ] });
}
function ModalCrearTarea({
  abierto,
  onCerrar,
  onGuardado,
  tarea
}) {
  useEscapeKey(abierto, onCerrar);
  const esEdicion = !!tarea;
  const [titulo, setTitulo] = reactExports.useState("");
  const [descripcion, setDescripcion] = reactExports.useState("");
  const [prioridad, setPrioridad] = reactExports.useState("media");
  const [estado, setEstado] = reactExports.useState("pendiente");
  const [fechaLimite, setFechaLimite] = reactExports.useState("");
  const [etiquetaId, setEtiquetaId] = reactExports.useState("");
  const [etiquetas, setEtiquetas] = reactExports.useState([]);
  const [comentarios, setComentarios] = reactExports.useState([]);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  reactExports.useEffect(() => {
    if (!abierto) return;
    listarEtiquetasApi().then((r) => setEtiquetas(r.etiquetas)).catch(() => {
    });
  }, [abierto]);
  reactExports.useEffect(() => {
    if (!abierto) return;
    if (tarea) {
      setTitulo(tarea.titulo);
      setDescripcion(tarea.descripcion ?? "");
      setPrioridad(tarea.prioridad);
      setEstado(tarea.estado);
      setFechaLimite(tarea.fechaLimite ? tarea.fechaLimite.slice(0, 16) : "");
      setEtiquetaId(tarea.etiquetaId ?? "");
      obtenerTareaApi(tarea.id).then((t) => setComentarios(t.comentarios ?? [])).catch(() => setComentarios([]));
    } else {
      setTitulo("");
      setDescripcion("");
      setPrioridad("media");
      setEstado("pendiente");
      setFechaLimite("");
      setEtiquetaId("");
      setComentarios([]);
    }
    setError(null);
  }, [tarea, abierto]);
  if (!abierto) return null;
  const manejarGuardar = async () => {
    if (!titulo.trim()) {
      setError("El titulo es obligatorio");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      if (esEdicion) {
        await actualizarTareaApi(tarea.id, {
          titulo: titulo.trim(),
          descripcion: descripcion.trim() || null,
          estado,
          prioridad,
          fechaLimite: fechaLimite ? new Date(fechaLimite).toISOString() : null,
          etiquetaId: etiquetaId || null
        });
      } else {
        await crearTareaApi({
          titulo: titulo.trim(),
          descripcion: descripcion.trim() || void 0,
          prioridad,
          fechaLimite: fechaLimite ? new Date(fechaLimite).toISOString() : void 0,
          etiquetaId: etiquetaId || void 0
        });
      }
      onGuardado();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setGuardando(false);
    }
  };
  const manejarEliminar = async () => {
    if (!esEdicion) return;
    setGuardando(true);
    try {
      await eliminarTareaApi(tarea.id);
      onGuardado();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setGuardando(false);
    }
  };
  const recargarComentarios = () => {
    if (!tarea) return;
    obtenerTareaApi(tarea.id).then((t) => setComentarios(t.comentarios ?? [])).catch(() => {
    });
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.08] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: esEdicion ? "Editar tarea" : "Nueva tarea" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "p-1 rounded-md text-superficie-400 hover:text-white hover:bg-white/[0.05]",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-5 py-4 space-y-4", children: [
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Titulo *" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: titulo,
            onChange: (e) => setTitulo(e.target.value),
            maxLength: 200,
            className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50",
            placeholder: "Ej: Renovar certificado, Revisar notificacion..."
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Descripcion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "textarea",
          {
            value: descripcion,
            onChange: (e) => setDescripcion(e.target.value),
            maxLength: 2e3,
            rows: 3,
            className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50 resize-none",
            placeholder: "Detalles de la tarea (opcional)"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Prioridad" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: prioridad,
              onChange: (e) => setPrioridad(e.target.value),
              className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "baja", children: "Baja" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "media", children: "Media" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "alta", children: "Alta" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "critica", children: "Critica" })
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
              className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "pendiente", children: "Pendiente" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "en_progreso", children: "En progreso" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "completada", children: "Completada" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "cancelada", children: "Cancelada" })
              ]
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Fecha limite" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "datetime-local",
            value: fechaLimite,
            onChange: (e) => setFechaLimite(e.target.value),
            className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Etiqueta" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: etiquetaId,
            onChange: (e) => setEtiquetaId(e.target.value),
            className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Sin etiqueta" }),
              etiquetas.map((et) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: et.id, children: et.nombre }, et.id))
            ]
          }
        )
      ] }),
      esEdicion && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pt-3 border-t border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        PanelComentarios,
        {
          tareaId: tarea.id,
          comentarios,
          onComentarioAgregado: recargarComentarios
        }
      ) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-4 border-t border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: esEdicion && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarEliminar,
          disabled: guardando,
          className: "flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-3.5 h-3.5" }),
            "Eliminar"
          ]
        }
      ) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: onCerrar,
            disabled: guardando,
            className: "px-4 py-2 text-sm text-superficie-400 hover:text-white hover:bg-white/[0.05] rounded-lg transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: manejarGuardar,
            disabled: guardando || !titulo.trim(),
            className: "px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500 hover:bg-acento-400 rounded-lg transition-colors disabled:opacity-50",
            children: guardando ? "Guardando..." : esEdicion ? "Actualizar" : "Crear"
          }
        )
      ] })
    ] })
  ] }) });
}
const COLORES_ESTADO = {
  pendiente: "bg-amber-500/20 text-amber-400",
  en_progreso: "bg-blue-500/20 text-blue-400",
  completada: "bg-emerald-500/20 text-emerald-400",
  cancelada: "bg-zinc-500/20 text-zinc-400"
};
const ETIQUETAS_ESTADO = {
  pendiente: "Pendiente",
  en_progreso: "En progreso",
  completada: "Completada",
  cancelada: "Cancelada"
};
const COLORES_PRIORIDAD = {
  critica: "bg-red-500/20 text-red-400",
  alta: "bg-amber-500/20 text-amber-400",
  media: "bg-emerald-500/20 text-emerald-400",
  baja: "bg-blue-500/20 text-blue-400"
};
const ETIQUETAS_PRIORIDAD = {
  critica: "Critica",
  alta: "Alta",
  media: "Media",
  baja: "Baja"
};
const FILTROS_ESTADO = [
  { valor: "", etiqueta: "Todas" },
  { valor: "pendiente", etiqueta: "Pendientes" },
  { valor: "en_progreso", etiqueta: "En progreso" },
  { valor: "completada", etiqueta: "Completadas" },
  { valor: "cancelada", etiqueta: "Canceladas" }
];
const FILTROS_PRIORIDAD = [
  { valor: "", etiqueta: "Todas" },
  { valor: "baja", etiqueta: "Baja" },
  { valor: "media", etiqueta: "Media" },
  { valor: "alta", etiqueta: "Alta" },
  { valor: "critica", etiqueta: "Critica" }
];
function PaginaTareas() {
  const [tareas, setTareas] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [filtroEstado, setFiltroEstado] = reactExports.useState("");
  const [filtroPrioridad, setFiltroPrioridad] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const [modalAbierto, setModalAbierto] = reactExports.useState(false);
  const [tareaEditar, setTareaEditar] = reactExports.useState(null);
  const cargarTareas = reactExports.useCallback(async () => {
    try {
      setError(null);
      const resultado = await listarTareasApi({
        estado: filtroEstado || void 0,
        prioridad: filtroPrioridad || void 0,
        busqueda: busqueda || void 0,
        pagina,
        limite: 20
      });
      setTareas(resultado.tareas);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar tareas");
    }
  }, [filtroEstado, filtroPrioridad, busqueda, pagina]);
  reactExports.useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      await cargarTareas();
      setCargando(false);
    };
    cargar();
  }, [cargarTareas]);
  const manejarBuscar = () => {
    setPagina(1);
    cargarTareas();
  };
  const manejarAbrirCrear = () => {
    setTareaEditar(null);
    setModalAbierto(true);
  };
  const manejarAbrirEditar = (tarea) => {
    setTareaEditar(tarea);
    setModalAbierto(true);
  };
  const manejarGuardado = () => {
    setModalAbierto(false);
    setTareaEditar(null);
    cargarTareas();
  };
  const manejarCerrarModal = () => {
    setModalAbierto(false);
    setTareaEditar(null);
  };
  const manejarCambioEstado = (valor) => {
    setFiltroEstado(valor);
    setPagina(1);
  };
  const manejarCambioPrioridad = (valor) => {
    setFiltroPrioridad(valor);
    setPagina(1);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Tareas" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarAbrirCrear,
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n            text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Nueva tarea"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-3 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: FILTROS_ESTADO.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => manejarCambioEstado(f.valor),
          className: `px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${filtroEstado === f.valor ? "bg-acento-500/10 text-acento-400 border-acento-500/20" : "text-superficie-400 border-white/[0.06] hover:bg-white/[0.05] hover:text-superficie-200"}`,
          children: f.etiqueta
        },
        f.valor
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "select",
          {
            value: filtroPrioridad,
            onChange: (e) => manejarCambioPrioridad(e.target.value),
            className: "px-3 py-2 text-sm bg-superficie-800/60 border border-white/[0.06] rounded-lg\n              text-superficie-200 outline-none focus:ring-2 focus:ring-acento-500/40",
            children: FILTROS_PRIORIDAD.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsxs("option", { value: f.valor, children: [
              "Prioridad: ",
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
              placeholder: "Buscar tareas...",
              className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-3 py-2 cristal-sutil rounded-lg text-sm text-superficie-400", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(SquareCheckBig, { className: "w-4 h-4 text-superficie-500" }),
          total,
          " tareas"
        ] })
      ] })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(EstadoCargando, {}) : tareas.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(EstadoVacio, {}) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Titulo" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Prioridad" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Asignado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha limite" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Etiqueta" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: tareas.map((tarea) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "tr",
        {
          className: "hover:bg-white/[0.02] transition-colors cursor-pointer",
          onClick: () => manejarAbrirEditar(tarea),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-5 py-4", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium text-superficie-100", children: tarea.titulo }),
              tarea.descripcion && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5 line-clamp-1", children: tarea.descripcion })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_ESTADO[tarea.estado]}`,
                children: ETIQUETAS_ESTADO[tarea.estado]
              }
            ) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_PRIORIDAD[tarea.prioridad]}`,
                children: ETIQUETAS_PRIORIDAD[tarea.prioridad]
              }
            ) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: tarea.nombreAsignado ?? "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap", children: tarea.fechaLimite ? formatearFecha(tarea.fechaLimite) : "—" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: tarea.nombreEtiqueta ? /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "span",
              {
                className: "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-superficie-800 border border-white/[0.06]",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(
                    "span",
                    {
                      className: "w-2 h-2 rounded-full",
                      style: { backgroundColor: tarea.colorEtiqueta ?? "#6b7280" }
                    }
                  ),
                  tarea.nombreEtiqueta
                ]
              }
            ) : /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-500", children: "—" }) })
          ]
        },
        tarea.id
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
        " tareas)"
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
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalCrearTarea,
      {
        abierto: modalAbierto,
        onCerrar: manejarCerrarModal,
        onGuardado: manejarGuardado,
        tarea: tareaEditar
      }
    )
  ] });
}
function EstadoCargando() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin mb-3" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Cargando tareas..." })
  ] });
}
function EstadoVacio() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(SquareCheckBig, { className: "w-7 h-7 text-superficie-500" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "No hay tareas" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Crea una nueva tarea para empezar" })
  ] });
}
export {
  PaginaTareas
};
