import { r as reactExports, j as jsxRuntimeExports, P as Plus, y as Timer, f as CircleCheckBig, T as TriangleAlert, I as CircleX } from "./index-DMbE3NR1.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
import { P as Power } from "./power-BwvIjpEF.js";
import { P as Play } from "./play-B9P3AzSW.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
const ETIQUETAS_TIPO = {
  scraping: "Scraping",
  workflow: "Workflow",
  sync_cloud: "Sync cloud",
  descarga_docs: "Descarga docs",
  consulta_notif: "Consulta notif."
};
const ETIQUETAS_FRECUENCIA = {
  cada_hora: "Cada hora",
  cada_2_horas: "Cada 2h",
  cada_4_horas: "Cada 4h",
  cada_6_horas: "Cada 6h",
  cada_12_horas: "Cada 12h",
  diaria: "Diaria",
  semanal: "Semanal",
  personalizada: "Personalizada"
};
const TIPOS_TAREA = ["scraping", "workflow", "sync_cloud", "descarga_docs", "consulta_notif"];
const FRECUENCIAS = ["cada_hora", "cada_2_horas", "cada_4_horas", "cada_6_horas", "cada_12_horas", "diaria", "semanal"];
const DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"];
function PaginaSchedulerDesktop() {
  const [tareas, setTareas] = reactExports.useState([]);
  const [historial, setHistorial] = reactExports.useState([]);
  const [estado, setEstado] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [tabActiva, setTabActiva] = reactExports.useState("tareas");
  const [mostrarFormulario, setMostrarFormulario] = reactExports.useState(false);
  const [ejecutandoId, setEjecutandoId] = reactExports.useState(null);
  const [formNombre, setFormNombre] = reactExports.useState("");
  const [formTipo, setFormTipo] = reactExports.useState("scraping");
  const [formFrecuencia, setFormFrecuencia] = reactExports.useState("diaria");
  const [formHora, setFormHora] = reactExports.useState("09:00");
  const [formDia, setFormDia] = reactExports.useState("lunes");
  const api = window.electronAPI;
  const cargar = reactExports.useCallback(async () => {
    if (!api?.scheduler) return;
    try {
      setCargando(true);
      setError(null);
      const [ts, hs, es] = await Promise.all([
        api.scheduler.listarTareas(),
        api.scheduler.historial(50),
        api.scheduler.obtenerEstado()
      ]);
      setTareas(ts);
      setHistorial(hs);
      setEstado(es);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando scheduler");
    } finally {
      setCargando(false);
    }
  }, [api]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  reactExports.useEffect(() => {
    if (!api?.scheduler) return;
    api.scheduler.onProgreso((datos) => {
      setEstado(datos);
    });
  }, [api]);
  const crearTarea = async () => {
    if (!api?.scheduler || !formNombre.trim()) return;
    try {
      setError(null);
      await api.scheduler.crearTarea({
        nombre: formNombre.trim(),
        tipo: formTipo,
        activa: true,
        frecuencia: formFrecuencia,
        horaEjecucion: formHora,
        diaSemana: formFrecuencia === "semanal" ? formDia : void 0,
        parametros: { tipo: formTipo }
      });
      setMostrarFormulario(false);
      setFormNombre("");
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error creando tarea");
    }
  };
  const toggleTarea = async (id) => {
    if (!api?.scheduler) return;
    try {
      await api.scheduler.toggleTarea(id);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cambiando estado");
    }
  };
  const ejecutarAhora = async (id) => {
    if (!api?.scheduler) return;
    try {
      setEjecutandoId(id);
      setError(null);
      await api.scheduler.ejecutarAhora(id);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error ejecutando tarea");
    } finally {
      setEjecutandoId(null);
    }
  };
  const eliminarTarea = async (id) => {
    if (!api?.scheduler) return;
    try {
      await api.scheduler.eliminarTarea(id);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error eliminando tarea");
    }
  };
  const formatearFechaRelativa = (iso) => {
    if (!iso) return "—";
    const fecha = new Date(iso);
    const ahora = Date.now();
    const diff = fecha.getTime() - ahora;
    if (diff < 0) return "pendiente";
    const min = Math.floor(diff / 6e4);
    if (min < 60) return `en ${min}min`;
    const hrs = Math.floor(min / 60);
    if (hrs < 24) return `en ${hrs}h`;
    return `en ${Math.floor(hrs / 24)}d`;
  };
  if (!api?.scheduler) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Programador de tareas" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Automatiza scraping, workflows y sincronizacion en horarios configurables" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
        estado && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${estado.activo ? "bg-emerald-500/20 text-emerald-400" : "bg-superficie-800 text-superficie-400"}`, children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full ${estado.activo ? "bg-emerald-400" : "bg-superficie-500"}` }),
          estado.activo ? `${estado.tareasActivas} activas` : "Inactivo"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setMostrarFormulario(true),
            className: "flex items-center gap-2 px-3 py-2 text-sm font-medium bg-acento-500/10 text-acento-400 border border-acento-500/20 rounded-lg hover:bg-acento-500/20 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
              "Nueva tarea"
            ]
          }
        )
      ] })
    ] }),
    estado?.ejecutandoAhora && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 cristal rounded-xl p-4 border border-acento-500/30 bg-acento-500/5", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-white", children: [
        "Ejecutando: ",
        estado.ejecutandoAhora
      ] })
    ] }) }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 mb-4 bg-red-500/10 border border-red-500/20 rounded-lg", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-red-400", children: error })
    ] }),
    mostrarFormulario && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-5 border border-acento-500/20 mb-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white mb-4", children: "Nueva tarea programada" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-400 mb-1 block", children: "Nombre" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              value: formNombre,
              onChange: (e) => setFormNombre(e.target.value),
              placeholder: "Mi tarea...",
              className: "w-full px-3 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white placeholder:text-superficie-500 focus:outline-none focus:border-acento-500/40"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-400 mb-1 block", children: "Tipo" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: formTipo,
              onChange: (e) => setFormTipo(e.target.value),
              className: "w-full px-3 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white appearance-none focus:outline-none focus:border-acento-500/40",
              children: TIPOS_TAREA.map((t) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: t, children: ETIQUETAS_TIPO[t] }, t))
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-400 mb-1 block", children: "Frecuencia" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "select",
            {
              value: formFrecuencia,
              onChange: (e) => setFormFrecuencia(e.target.value),
              className: "w-full px-3 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white appearance-none focus:outline-none focus:border-acento-500/40",
              children: FRECUENCIAS.map((f) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: f, children: ETIQUETAS_FRECUENCIA[f] }, f))
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-400 mb-1 block", children: "Hora" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "time",
              value: formHora,
              onChange: (e) => setFormHora(e.target.value),
              className: "w-full px-3 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white focus:outline-none focus:border-acento-500/40"
            }
          )
        ] })
      ] }),
      formFrecuencia === "semanal" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "text-xs text-superficie-400 mb-1 block", children: "Dia de la semana" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "select",
          {
            value: formDia,
            onChange: (e) => setFormDia(e.target.value),
            className: "px-3 py-2 text-sm bg-superficie-800 border border-white/[0.06] rounded-lg text-white appearance-none focus:outline-none focus:border-acento-500/40",
            children: DIAS_SEMANA.map((d) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: d, children: d.charAt(0).toUpperCase() + d.slice(1) }, d))
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: crearTarea,
            disabled: !formNombre.trim(),
            className: "px-4 py-2 text-sm font-medium bg-acento-500 text-white rounded-lg hover:bg-acento-600 transition-colors disabled:opacity-50",
            children: "Crear tarea"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setMostrarFormulario(false),
            className: "px-4 py-2 text-sm text-superficie-400 hover:text-white transition-colors",
            children: "Cancelar"
          }
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5 mb-4", children: [
      { id: "tareas", etiqueta: `Tareas (${tareas.length})` },
      { id: "historial", etiqueta: `Historial (${historial.length})` }
    ].map(({ id, etiqueta }) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => setTabActiva(id),
        className: `px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${tabActiva === id ? "bg-acento-500/10 text-acento-400 border border-acento-500/20" : "text-superficie-400 hover:bg-white/[0.05] border border-transparent"}`,
        children: etiqueta
      },
      id
    )) }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center py-20", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-500 animate-spin" }) }),
    !cargando && tabActiva === "tareas" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: tareas.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-14 h-14 rounded-full bg-superficie-800 flex items-center justify-center mx-auto mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Timer, { className: "w-7 h-7 text-superficie-500" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "No hay tareas programadas" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-xs mt-1", children: "Crea una tarea para automatizar procesos" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: tareas.map((tarea) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl border border-white/[0.06] px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => toggleTarea(tarea.id),
          className: `p-1 rounded-lg transition-colors ${tarea.activa ? "text-emerald-400 hover:bg-emerald-500/10" : "text-superficie-500 hover:bg-white/[0.05]"}`,
          title: tarea.activa ? "Desactivar" : "Activar",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(Power, { className: "w-4 h-4" })
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm font-medium ${tarea.activa ? "text-white" : "text-superficie-500"}`, children: tarea.nombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
          ETIQUETAS_FRECUENCIA[tarea.frecuencia],
          " a las ",
          tarea.horaEjecucion,
          tarea.diaSemana ? ` (${tarea.diaSemana})` : "",
          tarea.proximaEjecucion ? ` — proxima ${formatearFechaRelativa(tarea.proximaEjecucion)}` : ""
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-2 py-0.5 text-[10px] font-medium bg-superficie-800 text-superficie-400 rounded", children: ETIQUETAS_TIPO[tarea.tipo] }),
      tarea.ultimoResultado && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `px-2 py-0.5 text-[10px] font-medium rounded-full ${tarea.ultimoResultado === "exito" ? "bg-emerald-500/20 text-emerald-400" : tarea.ultimoResultado === "parcial" ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"}`, children: tarea.ultimoResultado === "exito" ? "OK" : tarea.ultimoResultado === "parcial" ? "Parcial" : "Error" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1 shrink-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => ejecutarAhora(tarea.id),
            disabled: ejecutandoId !== null,
            className: "p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-50",
            title: "Ejecutar ahora",
            children: ejecutandoId === tarea.id ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Play, { className: "w-4 h-4" })
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => eliminarTarea(tarea.id),
            className: "p-1.5 rounded-lg text-superficie-400 hover:text-red-400 hover:bg-red-500/10 transition-colors",
            title: "Eliminar",
            children: /* @__PURE__ */ jsxRuntimeExports.jsx(Trash2, { className: "w-4 h-4" })
          }
        )
      ] })
    ] }) }, tarea.id)) }) }),
    !cargando && tabActiva === "historial" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { children: historial.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-16", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "w-10 h-10 text-superficie-500 mx-auto mb-3" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "No hay ejecuciones registradas" })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: historial.map((ej) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl p-4 border border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
      ej.resultado === "exito" ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-5 h-5 text-emerald-400 shrink-0" }) : ej.resultado === "parcial" ? /* @__PURE__ */ jsxRuntimeExports.jsx(TriangleAlert, { className: "w-5 h-5 text-amber-400 shrink-0" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-5 h-5 text-red-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-white", children: ej.tareaNombre }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-500", children: [
          new Date(ej.ejecutadoEn).toLocaleString("es-ES"),
          " — ",
          ej.duracionMs,
          "ms"
        ] }),
        ej.mensaje && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-0.5", children: ej.mensaje })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "px-2 py-0.5 text-[10px] bg-superficie-800 text-superficie-400 rounded", children: ETIQUETAS_TIPO[ej.tipo] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-medium px-2 py-0.5 rounded-full ${ej.resultado === "exito" ? "bg-emerald-500/20 text-emerald-400" : ej.resultado === "parcial" ? "bg-amber-500/20 text-amber-400" : "bg-red-500/20 text-red-400"}`, children: ej.resultado === "exito" ? "Exito" : ej.resultado === "parcial" ? "Parcial" : "Error" })
    ] }) }, ej.id)) }) })
  ] });
}
export {
  PaginaSchedulerDesktop
};
