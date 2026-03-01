import { d as apiClient, r as reactExports, j as jsxRuntimeExports, X, P as Plus, H as obtenerPerfilApi, L as Lock, W as Workflow } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { u as useEscapeKey } from "./useEscapeKey-vhUEoHpe.js";
import { l as listarEtiquetasApi } from "./etiquetasServicio-dQOn1U3c.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { P as Play } from "./play-B9P3AzSW.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
async function listarWorkflowsApi(params) {
  const query = new URLSearchParams();
  if (params?.activo) query.set("activo", params.activo);
  if (params?.disparador) query.set("disparador", params.disparador);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const ruta = `/workflows?${query}`;
  const respuesta = await apiClient.get(ruta);
  return {
    workflows: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
async function crearWorkflowApi(datos) {
  const respuesta = await apiClient.post("/workflows", datos);
  return respuesta.datos;
}
async function actualizarWorkflowApi(id, datos) {
  const respuesta = await apiClient.put(`/workflows/${id}`, datos);
  return respuesta.datos;
}
async function eliminarWorkflowApi(id) {
  await apiClient.del(`/workflows/${id}`);
}
async function ejecutarWorkflowApi(id) {
  const respuesta = await apiClient.post(`/workflows/${id}/ejecutar`, {});
  return respuesta.datos;
}
async function listarEjecucionesApi(params) {
  const query = new URLSearchParams();
  if (params?.workflowId) query.set("workflowId", params.workflowId);
  if (params?.resultado) query.set("resultado", params.resultado);
  if (params?.pagina) query.set("pagina", String(params.pagina));
  query.set("limite", String(params?.limite));
  const ruta = `/workflows/ejecuciones?${query}`;
  const respuesta = await apiClient.get(ruta);
  return {
    ejecuciones: respuesta.datos ?? [],
    meta: respuesta.meta ?? { total: 0, pagina: 1, limite: 20, totalPaginas: 0 }
  };
}
const OPCIONES_DISPARADOR = [
  { valor: "certificado_vence", etiqueta: "Certificado vence" },
  { valor: "notificacion_recibida", etiqueta: "Notificacion recibida" },
  { valor: "tarea_creada", etiqueta: "Tarea creada" },
  { valor: "tarea_completada", etiqueta: "Tarea completada" },
  { valor: "manual", etiqueta: "Manual" }
];
const CAMPOS_POR_DISPARADOR = {
  certificado_vence: [
    { valor: "diasParaVencer", etiqueta: "Dias para vencer" },
    { valor: "emisor", etiqueta: "Emisor" },
    { valor: "nombreTitular", etiqueta: "Nombre titular" },
    { valor: "dniCif", etiqueta: "DNI/CIF" }
  ],
  notificacion_recibida: [
    { valor: "administracion", etiqueta: "Administracion" },
    { valor: "tipo", etiqueta: "Tipo" },
    { valor: "contenido", etiqueta: "Contenido" }
  ],
  tarea_creada: [
    { valor: "titulo", etiqueta: "Titulo" },
    { valor: "prioridad", etiqueta: "Prioridad" },
    { valor: "referenciaTipo", etiqueta: "Tipo de referencia" }
  ],
  tarea_completada: [
    { valor: "titulo", etiqueta: "Titulo" },
    { valor: "prioridad", etiqueta: "Prioridad" },
    { valor: "referenciaTipo", etiqueta: "Tipo de referencia" }
  ],
  manual: []
};
const OPCIONES_OPERADOR = [
  { valor: "igual", etiqueta: "es igual a" },
  { valor: "distinto", etiqueta: "es distinto de" },
  { valor: "contiene", etiqueta: "contiene" },
  { valor: "no_contiene", etiqueta: "no contiene" },
  { valor: "mayor_que", etiqueta: "mayor que" },
  { valor: "menor_que", etiqueta: "menor que" },
  { valor: "mayor_igual", etiqueta: "mayor o igual" },
  { valor: "menor_igual", etiqueta: "menor o igual" }
];
const OPCIONES_TIPO_ACCION = [
  { valor: "crear_tarea", etiqueta: "Crear tarea" },
  { valor: "crear_recordatorio", etiqueta: "Crear recordatorio" },
  { valor: "cambiar_etiqueta", etiqueta: "Cambiar etiqueta" }
];
function ModalCrearWorkflow({ abierto, onCerrar, onGuardado, workflow }) {
  useEscapeKey(abierto, onCerrar);
  const esEdicion = !!workflow;
  const [tabActivo, setTabActivo] = reactExports.useState(0);
  const [nombre, setNombre] = reactExports.useState("");
  const [descripcion, setDescripcion] = reactExports.useState("");
  const [disparador, setDisparador] = reactExports.useState("manual");
  const [condiciones, setCondiciones] = reactExports.useState([]);
  const [acciones, setAcciones] = reactExports.useState([{ tipo: "crear_tarea", config: {} }]);
  const [etiquetas, setEtiquetas] = reactExports.useState([]);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  reactExports.useEffect(() => {
    if (!abierto) return;
    listarEtiquetasApi().then((r) => setEtiquetas(r.etiquetas)).catch(() => {
    });
  }, [abierto]);
  reactExports.useEffect(() => {
    if (!abierto) return;
    if (workflow) {
      setNombre(workflow.nombre);
      setDescripcion(workflow.descripcion ?? "");
      setDisparador(workflow.disparador);
      setCondiciones(
        workflow.condiciones.map((c) => ({
          campo: c.campo,
          operador: c.operador,
          valor: String(c.valor)
        }))
      );
      setAcciones(
        workflow.acciones.map((a) => ({
          tipo: a.tipo,
          config: { ...a.config }
        }))
      );
    } else {
      setNombre("");
      setDescripcion("");
      setDisparador("manual");
      setCondiciones([]);
      setAcciones([{ tipo: "crear_tarea", config: {} }]);
    }
    setTabActivo(0);
    setError(null);
  }, [workflow, abierto]);
  if (!abierto) return null;
  const camposDisponibles = CAMPOS_POR_DISPARADOR[disparador];
  const agregarCondicion = () => {
    if (condiciones.length >= 10) return;
    const primerCampo = camposDisponibles[0]?.valor ?? "";
    setCondiciones([...condiciones, { campo: primerCampo, operador: "igual", valor: "" }]);
  };
  const actualizarCondicion = (indice, datos) => {
    setCondiciones(condiciones.map((c, i) => i === indice ? { ...c, ...datos } : c));
  };
  const eliminarCondicion = (indice) => {
    setCondiciones(condiciones.filter((_, i) => i !== indice));
  };
  const agregarAccion = () => {
    if (acciones.length >= 5) return;
    setAcciones([...acciones, { tipo: "crear_tarea", config: {} }]);
  };
  const actualizarAccion = (indice, datos) => {
    setAcciones(acciones.map((a, i) => i === indice ? { ...a, ...datos } : a));
  };
  const actualizarConfigAccion = (indice, clave, valor) => {
    setAcciones(
      acciones.map(
        (a, i) => i === indice ? { ...a, config: { ...a.config, [clave]: valor } } : a
      )
    );
  };
  const eliminarAccion = (indice) => {
    if (acciones.length <= 1) return;
    setAcciones(acciones.filter((_, i) => i !== indice));
  };
  const manejarGuardar = async () => {
    if (!nombre.trim()) {
      setError("El nombre es obligatorio");
      return;
    }
    if (acciones.length === 0) {
      setError("Se requiere al menos una accion");
      return;
    }
    setGuardando(true);
    setError(null);
    try {
      const datos = {
        nombre: nombre.trim(),
        descripcion: descripcion.trim() || void 0,
        disparador,
        condiciones: condiciones.map((c) => ({
          campo: c.campo,
          operador: c.operador,
          valor: c.valor
        })),
        acciones: acciones.map((a) => ({
          tipo: a.tipo,
          config: a.config
        }))
      };
      if (esEdicion) {
        await actualizarWorkflowApi(workflow.id, datos);
      } else {
        await crearWorkflowApi(datos);
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
      await eliminarWorkflowApi(workflow.id);
      onGuardado();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setGuardando(false);
    }
  };
  const TABS = ["General", "Condiciones", "Acciones"];
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4", onClick: onCerrar, children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900 border border-white/[0.08] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto", onClick: (e) => e.stopPropagation(), children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: esEdicion ? "Editar workflow" : "Nuevo workflow" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: onCerrar,
          className: "p-1 rounded-md text-superficie-400 hover:text-white hover:bg-white/[0.05]",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex border-b border-white/[0.06]", children: TABS.map((tab, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => setTabActivo(i),
        className: `flex-1 px-4 py-2.5 text-xs font-medium transition-colors ${tabActivo === i ? "text-acento-400 border-b-2 border-acento-500" : "text-superficie-500 hover:text-superficie-300"}`,
        children: tab
      },
      tab
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "px-5 py-4 space-y-4 min-h-[280px]", children: [
      error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: error }),
      tabActivo === 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Nombre *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: nombre,
              onChange: (e) => setNombre(e.target.value),
              maxLength: 200,
              className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50",
              placeholder: "Ej: Alerta certificados proximos a vencer"
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
              maxLength: 1e3,
              rows: 3,
              className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50 resize-none",
              placeholder: "Descripcion del workflow (opcional)"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs font-medium text-superficie-400 mb-1.5", children: "Disparador" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: disparador,
              onChange: (e) => {
                setDisparador(e.target.value);
                setCondiciones([]);
              },
              className: "w-full px-3 py-2 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: OPCIONES_DISPARADOR.map((op) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: op.valor, children: op.etiqueta }, op.valor))
            }
          )
        ] })
      ] }),
      tabActivo === 1 && /* @__PURE__ */ jsxRuntimeExports.jsx(jsxRuntimeExports.Fragment, { children: disparador === "manual" ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col items-center justify-center py-8 text-superficie-500 text-sm", children: "Sin condiciones para ejecucion manual" }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        condiciones.map((cond, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-2 p-3 bg-superficie-800/50 border border-white/[0.06] rounded-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs font-medium text-superficie-400", children: [
              "Condicion ",
              i + 1
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => eliminarCondicion(i),
                className: "p-1 rounded text-superficie-500 hover:text-red-400 hover:bg-red-500/10",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3.5 h-3.5" })
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: cond.campo,
              onChange: (e) => actualizarCondicion(i, { campo: e.target.value }),
              className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: camposDisponibles.map((c) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: c.valor, children: c.etiqueta }, c.valor))
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: cond.operador,
              onChange: (e) => actualizarCondicion(i, { operador: e.target.value }),
              className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: OPCIONES_OPERADOR.map((op) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: op.valor, children: op.etiqueta }, op.valor))
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: cond.valor,
              onChange: (e) => actualizarCondicion(i, { valor: e.target.value }),
              className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50",
              placeholder: "Valor"
            }
          )
        ] }, i)),
        condiciones.length < 10 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: agregarCondicion,
            className: "flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-acento-400 hover:bg-acento-500/10 rounded-lg transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-3.5 h-3.5" }),
              "Anadir condicion"
            ]
          }
        )
      ] }) }),
      tabActivo === 2 && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        acciones.map((accion, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-2 p-3 bg-superficie-800/50 border border-white/[0.06] rounded-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs font-medium text-superficie-400", children: [
              "Accion ",
              i + 1
            ] }),
            acciones.length > 1 && /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => eliminarAccion(i),
                className: "p-1 rounded text-superficie-500 hover:text-red-400 hover:bg-red-500/10",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3.5 h-3.5" })
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: accion.tipo,
              onChange: (e) => actualizarAccion(i, { tipo: e.target.value, config: {} }),
              className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: OPCIONES_TIPO_ACCION.map((op) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: op.valor, children: op.etiqueta }, op.valor))
            }
          ),
          accion.tipo === "crear_tarea" && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "text",
                value: accion.config.titulo ?? "",
                onChange: (e) => actualizarConfigAccion(i, "titulo", e.target.value),
                className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50",
                placeholder: "Titulo de la tarea"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "select",
              {
                value: accion.config.prioridad ?? "media",
                onChange: (e) => actualizarConfigAccion(i, "prioridad", e.target.value),
                className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "baja", children: "Baja" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "media", children: "Media" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "alta", children: "Alta" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "critica", children: "Critica" })
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: "Usa {variable} para valores dinamicos" })
          ] }),
          accion.tipo === "crear_recordatorio" && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                type: "text",
                value: accion.config.titulo ?? "",
                onChange: (e) => actualizarConfigAccion(i, "titulo", e.target.value),
                className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white placeholder-superficie-500 focus:outline-none focus:border-acento-500/50",
                placeholder: "Titulo del recordatorio"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-xs text-superficie-400 mb-1", children: "Dias antes" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                "input",
                {
                  type: "number",
                  value: accion.config.diasAntes ?? 7,
                  onChange: (e) => actualizarConfigAccion(i, "diasAntes", Number(e.target.value)),
                  min: 1,
                  max: 365,
                  className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50"
                }
              )
            ] })
          ] }),
          accion.tipo === "cambiar_etiqueta" && /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: accion.config.etiquetaId ?? "",
              onChange: (e) => actualizarConfigAccion(i, "etiquetaId", e.target.value),
              className: "w-full px-3 py-1.5 bg-superficie-800 border border-white/[0.08] rounded-lg text-sm text-white focus:outline-none focus:border-acento-500/50",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Seleccionar etiqueta" }),
                etiquetas.map((et) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: et.id, children: et.nombre }, et.id))
              ]
            }
          )
        ] }, i)),
        acciones.length < 5 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: agregarAccion,
            className: "flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-acento-400 hover:bg-acento-500/10 rounded-lg transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-3.5 h-3.5" }),
              "Anadir accion"
            ]
          }
        )
      ] })
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
            disabled: guardando || !nombre.trim(),
            className: "px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500 hover:bg-acento-400 rounded-lg transition-colors disabled:opacity-50",
            children: guardando ? "Guardando..." : esEdicion ? "Actualizar" : "Crear"
          }
        )
      ] })
    ] })
  ] }) });
}
const COLORES_DISPARADOR = {
  certificado_vence: "bg-orange-500/20 text-orange-400",
  notificacion_recibida: "bg-blue-500/20 text-blue-400",
  tarea_creada: "bg-emerald-500/20 text-emerald-400",
  tarea_completada: "bg-purple-500/20 text-purple-400",
  manual: "bg-zinc-500/20 text-zinc-400"
};
const ETIQUETAS_DISPARADOR = {
  certificado_vence: "Certificado vence",
  notificacion_recibida: "Notificacion recibida",
  tarea_creada: "Tarea creada",
  tarea_completada: "Tarea completada",
  manual: "Manual"
};
const COLORES_RESULTADO = {
  exito: "bg-emerald-500/20 text-emerald-400",
  error: "bg-red-500/20 text-red-400"
};
function PaginaWorkflows() {
  const [workflows, setWorkflows] = reactExports.useState([]);
  const [ejecuciones, setEjecuciones] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [total, setTotal] = reactExports.useState(0);
  const [paginaEjec, setPaginaEjec] = reactExports.useState(1);
  const [totalPaginasEjec, setTotalPaginasEjec] = reactExports.useState(1);
  const [modalAbierto, setModalAbierto] = reactExports.useState(false);
  const [workflowEditar, setWorkflowEditar] = reactExports.useState(null);
  const [plan, setPlan] = reactExports.useState("basico");
  const [rol, setRol] = reactExports.useState("asesor");
  const [ejecutando, setEjecutando] = reactExports.useState(null);
  reactExports.useEffect(() => {
    obtenerPerfilApi().then((perfil) => {
      setPlan(perfil.organizacion.plan);
      setRol(perfil.rol);
    }).catch(() => {
    });
  }, []);
  const esAdmin = rol === "admin";
  const planPermitido = plan === "profesional" || plan === "plus";
  const cargarWorkflows = reactExports.useCallback(async () => {
    try {
      setError(null);
      const resultado = await listarWorkflowsApi({ pagina, limite: 20 });
      setWorkflows(resultado.workflows);
      setTotal(resultado.meta.total);
      setTotalPaginas(resultado.meta.totalPaginas);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar workflows");
    }
  }, [pagina]);
  const cargarEjecuciones = reactExports.useCallback(async () => {
    try {
      const resultado = await listarEjecucionesApi({ pagina: paginaEjec, limite: 10 });
      setEjecuciones(resultado.ejecuciones);
      setTotalPaginasEjec(resultado.meta.totalPaginas);
    } catch {
    }
  }, [paginaEjec]);
  reactExports.useEffect(() => {
    const cargar = async () => {
      setCargando(true);
      await cargarWorkflows();
      setCargando(false);
    };
    cargar();
  }, [cargarWorkflows]);
  reactExports.useEffect(() => {
    if (planPermitido) cargarEjecuciones();
  }, [cargarEjecuciones, planPermitido]);
  const manejarAbrirCrear = () => {
    setWorkflowEditar(null);
    setModalAbierto(true);
  };
  const manejarAbrirEditar = (workflow) => {
    setWorkflowEditar(workflow);
    setModalAbierto(true);
  };
  const manejarGuardado = () => {
    setModalAbierto(false);
    setWorkflowEditar(null);
    cargarWorkflows();
    cargarEjecuciones();
  };
  const manejarCerrarModal = () => {
    setModalAbierto(false);
    setWorkflowEditar(null);
  };
  const manejarToggleActivo = async (workflow, e) => {
    e.stopPropagation();
    try {
      await actualizarWorkflowApi(workflow.id, { activo: !workflow.activo });
      cargarWorkflows();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al actualizar workflow");
    }
  };
  const manejarEjecutar = async (workflow, e) => {
    e.stopPropagation();
    setEjecutando(workflow.id);
    try {
      await ejecutarWorkflowApi(workflow.id);
      cargarEjecuciones();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al ejecutar workflow");
    } finally {
      setEjecutando(null);
    }
  };
  if (!planPermitido) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-4 mb-6", children: /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Workflows" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-12 flex flex-col items-center justify-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Lock, { className: "w-7 h-7 text-superficie-500" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "Funcionalidad disponible en plan Profesional" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Actualiza tu plan para automatizar flujos de trabajo" })
      ] })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Workflows" }),
      esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: manejarAbrirCrear,
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n              text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Nuevo workflow"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-4 py-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error,
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setError(null), className: "ml-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-4 h-4" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 px-3 py-2 cristal-sutil rounded-lg text-sm text-superficie-400 mb-4 w-fit", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Workflow, { className: "w-4 h-4 text-superficie-500" }),
      total,
      " workflows"
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden mb-8", children: cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(EstadoCargando, {}) : workflows.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx(EstadoVacio, {}) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Nombre" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Disparador" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Condiciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Acciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Estado" }),
        esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Ejecutar" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: workflows.map((wf) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "tr",
        {
          className: "hover:bg-white/[0.02] transition-colors cursor-pointer",
          onClick: () => manejarAbrirEditar(wf),
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { className: "px-5 py-4", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium text-superficie-100", children: wf.nombre }),
              wf.descripcion && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-0.5 line-clamp-1", children: wf.descripcion })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_DISPARADOR[wf.disparador]}`,
                children: ETIQUETAS_DISPARADOR[wf.disparador]
              }
            ) }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: wf.condiciones.length }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: wf.acciones.length }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: (e) => manejarToggleActivo(wf, e),
                className: `relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${wf.activo ? "bg-acento-500" : "bg-superficie-700"}`,
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "span",
                  {
                    className: `inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${wf.activo ? "translate-x-4.5" : "translate-x-0.5"}`
                  }
                )
              }
            ) }),
            esAdmin && /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: (e) => manejarEjecutar(wf, e),
                disabled: ejecutando === wf.id,
                className: "p-1.5 rounded-lg text-superficie-400 hover:text-acento-400 hover:bg-acento-500/10 disabled:opacity-30 transition-colors",
                title: "Ejecutar workflow",
                children: ejecutando === wf.id ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Play, { className: "w-4 h-4" })
              }
            ) })
          ]
        },
        wf.id
      )) })
    ] }) }) }),
    totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
        "Pagina ",
        pagina,
        " de ",
        totalPaginas,
        " (",
        total,
        " workflows)"
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
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-white mb-3", children: "Historial de ejecuciones" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: ejecuciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-col items-center justify-center py-10 px-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm", children: "Sin ejecuciones registradas" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Workflow" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Resultado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide", children: "Fecha" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: ejecuciones.map((ejec) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 font-medium text-superficie-100", children: ejec.nombreWorkflow ?? "—" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            "span",
            {
              className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${COLORES_RESULTADO[ejec.resultado] ?? ""}`,
              children: ejec.resultado === "exito" ? "Exito" : "Error"
            }
          ) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400 whitespace-nowrap", children: formatearFecha(ejec.ejecutadoEn) })
        ] }, ejec.id)) })
      ] }) }) }),
      totalPaginasEjec > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mt-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
          "Pagina ",
          paginaEjec,
          " de ",
          totalPaginasEjec
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPaginaEjec((p) => Math.max(1, p - 1)),
              disabled: paginaEjec <= 1,
              className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPaginaEjec((p) => Math.min(totalPaginasEjec, p + 1)),
              disabled: paginaEjec >= totalPaginasEjec,
              className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] disabled:opacity-30 transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
            }
          )
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalCrearWorkflow,
      {
        abierto: modalAbierto,
        onCerrar: manejarCerrarModal,
        onGuardado: manejarGuardado,
        workflow: workflowEditar
      }
    )
  ] });
}
function EstadoCargando() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-superficie-500 animate-spin mb-3" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Cargando workflows..." })
  ] });
}
function EstadoVacio() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-16 px-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 border border-white/[0.06] flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Workflow, { className: "w-7 h-7 text-superficie-500" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-300 text-sm font-medium", children: "No hay workflows" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Crea un nuevo workflow para automatizar tus procesos" })
  ] });
}
export {
  PaginaWorkflows
};
