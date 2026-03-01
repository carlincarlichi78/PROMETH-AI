import { c as createLucideIcon, d as apiClient, j as jsxRuntimeExports, T as TriangleAlert, B as Bell, C as CalendarDays, u as useNavigate, r as reactExports, I as CircleX, q as FileText, f as CircleCheckBig, p as Brain, w as ClipboardList, x as ShieldAlert, s as ArrowRight } from "./index-DMbE3NR1.js";
import { F as FileCheck } from "./file-check-CGZ00Z_g.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
import { R as RefreshCw } from "./refresh-cw-wjNAn7st.js";
import { C as Calendar } from "./calendar-KREuhz-X.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
import { b as actualizarNotificacionApi } from "./notificacionesServicio-B3Srptx0.js";
import { a as analizarNotificacionApi } from "./aegisServicio-6JqSkwLW.js";
import { c as crearTareaApi } from "./tareasServicio-CSpOVgN6.js";
import { syncPlazosApi } from "./integracionesServicio-C-79KoQl.js";
import { C as CalendarPlus } from "./calendar-plus-DByXh6wM.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { T as Trash2 } from "./trash-2-D_KtOj8f.js";
import { E as ExternalLink } from "./external-link-Bh_6IHXn.js";
import { T as TrendingUp } from "./trending-up-zIPd8Al1.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const LayoutGrid = createLucideIcon("LayoutGrid", [
  ["rect", { width: "7", height: "7", x: "3", y: "3", rx: "1", key: "1g98yp" }],
  ["rect", { width: "7", height: "7", x: "14", y: "3", rx: "1", key: "6d4xhi" }],
  ["rect", { width: "7", height: "7", x: "14", y: "14", rx: "1", key: "nxv5o0" }],
  ["rect", { width: "7", height: "7", x: "3", y: "14", rx: "1", key: "1bb6yr" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const List = createLucideIcon("List", [
  ["path", { d: "M3 12h.01", key: "nlz23k" }],
  ["path", { d: "M3 18h.01", key: "1tta3j" }],
  ["path", { d: "M3 6h.01", key: "1rqtza" }],
  ["path", { d: "M8 12h13", key: "1za7za" }],
  ["path", { d: "M8 18h13", key: "1lx6n3" }],
  ["path", { d: "M8 6h13", key: "ik3vkj" }]
]);
async function listarEventosCalendarioUnificadoApi(filtros) {
  const params = new URLSearchParams();
  if (filtros.desde) params.set("desde", filtros.desde);
  if (filtros.hasta) params.set("hasta", filtros.hasta);
  if (filtros.tipo && filtros.tipo !== "todos") params.set("tipo", filtros.tipo);
  if (filtros.urgencia && filtros.urgencia !== "todas") params.set("urgencia", filtros.urgencia);
  if (filtros.administracion) params.set("administracion", filtros.administracion);
  if (filtros.soloPendientes) params.set("soloPendientes", "true");
  const qs = params.toString();
  const respuesta = await apiClient.get(
    `/calendario/eventos${qs ? `?${qs}` : ""}`
  );
  return respuesta.datos ?? [];
}
async function obtenerKpisCalendarioApi() {
  const respuesta = await apiClient.get("/calendario/kpis");
  return respuesta.datos;
}
function KpiCard({
  icono: Icono,
  etiqueta,
  valor,
  subvalor,
  colorIcono,
  cargando
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl p-4 flex items-start gap-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `p-2 rounded-lg ${colorIcono}`, children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-5 h-5" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 truncate", children: etiqueta }),
      cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-6 w-12 bg-superficie-800 rounded animate-pulse mt-1" }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg font-bold text-white", children: valor }),
        subvalor && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 truncate", children: subvalor })
      ] })
    ] })
  ] });
}
function KPIsCalendario({ kpis, cargando }) {
  const proximoTexto = kpis?.proximoEvento ? `${kpis.proximoEvento.titulo} (${kpis.proximoEvento.diasRestantes}d)` : "Sin eventos";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      KpiCard,
      {
        icono: TriangleAlert,
        etiqueta: "Plazos urgentes",
        valor: kpis?.plazosUrgentes ?? 0,
        colorIcono: "bg-red-500/10 text-red-400",
        cargando
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      KpiCard,
      {
        icono: FileCheck,
        etiqueta: "Vencimientos mes",
        valor: kpis?.vencimientosMes ?? 0,
        colorIcono: "bg-amber-500/10 text-amber-400",
        cargando
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      KpiCard,
      {
        icono: Bell,
        etiqueta: "Recordatorios",
        valor: kpis?.recordatoriosPendientes ?? 0,
        colorIcono: "bg-blue-500/10 text-blue-400",
        cargando
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      KpiCard,
      {
        icono: Clock,
        etiqueta: "Próximo evento",
        valor: kpis?.proximoEvento?.diasRestantes ?? "-",
        subvalor: proximoTexto,
        colorIcono: "bg-purple-500/10 text-purple-400",
        cargando
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      KpiCard,
      {
        icono: RefreshCw,
        etiqueta: "Sincronizados",
        valor: kpis?.sincronizados ?? 0,
        colorIcono: "bg-green-500/10 text-green-400",
        cargando
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      KpiCard,
      {
        icono: CalendarDays,
        etiqueta: "Total eventos",
        valor: kpis?.totalEventos ?? 0,
        colorIcono: "bg-superficie-700/50 text-superficie-300",
        cargando
      }
    )
  ] });
}
const VISTAS = [
  { valor: "mes", icono: Calendar, etiqueta: "Mes" },
  { valor: "semana", icono: LayoutGrid, etiqueta: "Semana" },
  { valor: "lista", icono: List, etiqueta: "Lista" }
];
const TIPOS = [
  { valor: "todos", etiqueta: "Todos" },
  { valor: "notificacion", etiqueta: "Notificaciones" },
  { valor: "certificado", etiqueta: "Certificados" },
  { valor: "recordatorio", etiqueta: "Recordatorios" }
];
const URGENCIAS = [
  { valor: "todas", etiqueta: "Todas" },
  { valor: "critica", etiqueta: "Crítica" },
  { valor: "alta", etiqueta: "Alta" },
  { valor: "media", etiqueta: "Media" },
  { valor: "baja", etiqueta: "Baja" }
];
function FiltrosCalendario({
  vista,
  onVistaChange,
  tipo,
  onTipoChange,
  urgencia,
  onUrgenciaChange,
  soloPendientes,
  onSoloPendientesChange,
  administraciones,
  administracion,
  onAdministracionChange
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap items-center gap-3", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex bg-superficie-900/50 border border-white/[0.06] rounded-lg p-0.5", children: VISTAS.map(({ valor, icono: Icono, etiqueta }) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        onClick: () => onVistaChange(valor),
        className: `flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${vista === valor ? "bg-acento-500 text-superficie-950" : "text-superficie-400 hover:text-white"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-3.5 h-3.5" }),
          etiqueta
        ]
      },
      valor
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "select",
      {
        value: tipo,
        onChange: (e) => onTipoChange(e.target.value),
        className: "bg-superficie-900/50 border border-white/[0.06] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-acento-500",
        children: TIPOS.map(({ valor, etiqueta }) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: valor, children: etiqueta }, valor))
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      "select",
      {
        value: urgencia,
        onChange: (e) => onUrgenciaChange(e.target.value),
        className: "bg-superficie-900/50 border border-white/[0.06] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-acento-500",
        children: URGENCIAS.map(({ valor, etiqueta }) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: valor, children: etiqueta }, valor))
      }
    ),
    administraciones.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "select",
      {
        value: administracion,
        onChange: (e) => onAdministracionChange(e.target.value),
        className: "bg-superficie-900/50 border border-white/[0.06] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-1 focus:ring-acento-500 max-w-[200px]",
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todas las admin." }),
          administraciones.map((admin) => /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: admin, children: admin }, admin))
        ]
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "flex items-center gap-2 text-xs text-superficie-400 cursor-pointer", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "checkbox",
          checked: soloPendientes,
          onChange: (e) => onSoloPendientesChange(e.target.checked),
          className: "rounded border-white/20 bg-superficie-800 text-acento-500 focus:ring-acento-500 focus:ring-offset-0"
        }
      ),
      "Solo pendientes"
    ] })
  ] });
}
const DIAS_SEMANA$1 = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const COLORES_URGENCIA$3 = {
  critica: "bg-red-500/80",
  alta: "bg-amber-500/80",
  media: "bg-green-500/80",
  baja: "bg-blue-500/80"
};
const COLORES_TIPO$2 = {
  manual: "bg-blue-500/80",
  notificacion: "bg-violet-500/80"
};
function CalendarioMes({
  mes,
  eventos,
  onMesCambiado,
  onClickEvento,
  cargando
}) {
  const anio = mes.getFullYear();
  const mesIdx = mes.getMonth();
  const primerDia = new Date(anio, mesIdx, 1);
  const diaSemanaInicio = (primerDia.getDay() + 6) % 7;
  const totalDias = new Date(anio, mesIdx + 1, 0).getDate();
  const eventosPorDia = /* @__PURE__ */ new Map();
  for (const evento of eventos) {
    const fechaEvento = new Date(evento.fecha);
    if (fechaEvento.getMonth() === mesIdx && fechaEvento.getFullYear() === anio) {
      const dia = fechaEvento.getDate();
      if (!eventosPorDia.has(dia)) eventosPorDia.set(dia, []);
      eventosPorDia.get(dia).push(evento);
    }
  }
  const hoy = /* @__PURE__ */ new Date();
  const esHoyMes = hoy.getMonth() === mesIdx && hoy.getFullYear() === anio;
  const diaHoy = hoy.getDate();
  const irMesAnterior = () => {
    onMesCambiado(new Date(anio, mesIdx - 1, 1));
  };
  const irMesSiguiente = () => {
    onMesCambiado(new Date(anio, mesIdx + 1, 1));
  };
  const nombreMes = primerDia.toLocaleDateString("es-ES", { month: "long", year: "numeric" });
  const celdas = [];
  for (let i = 0; i < diaSemanaInicio; i++) celdas.push(null);
  for (let d = 1; d <= totalDias; d++) celdas.push(d);
  function obtenerColorEvento(evento) {
    if (evento.estado === "completado") return "bg-superficie-600/60";
    if (evento.tipo === "vencimiento_certificado") {
      return COLORES_URGENCIA$3[evento.urgencia] ?? "bg-superficie-500/80";
    }
    return COLORES_TIPO$2[evento.tipo] ?? "bg-superficie-500/80";
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl overflow-hidden", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-4 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: irMesAnterior,
          className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-5 h-5" })
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white capitalize", children: nombreMes }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: irMesSiguiente,
          className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-5 h-5" })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-7 border-b border-white/[0.06]", children: DIAS_SEMANA$1.map((dia) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: "text-center text-xs font-semibold text-superficie-500 uppercase tracking-wide py-2",
        children: dia
      },
      dia
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `grid grid-cols-7 ${cargando ? "opacity-50" : ""}`, children: celdas.map((dia, idx) => {
      if (dia === null) {
        return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "min-h-[80px] border-b border-r border-white/[0.03]" }, `vacio-${idx}`);
      }
      const eventosDelDia = eventosPorDia.get(dia) ?? [];
      const esHoy = esHoyMes && dia === diaHoy;
      const maxVisibles = 3;
      const restantes = eventosDelDia.length - maxVisibles;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: `min-h-[80px] p-1.5 border-b border-r border-white/[0.03] ${esHoy ? "bg-acento-500/5" : ""}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: `inline-flex items-center justify-center w-6 h-6 text-xs rounded-full ${esHoy ? "bg-acento-500 text-superficie-950 font-bold" : "text-superficie-400"}`,
                children: dia
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-0.5 space-y-0.5", children: [
              eventosDelDia.slice(0, maxVisibles).map((evento) => /* @__PURE__ */ jsxRuntimeExports.jsx(
                "button",
                {
                  onClick: () => onClickEvento(evento),
                  className: `w-full text-left text-[10px] leading-tight text-white px-1 py-0.5 rounded truncate ${obtenerColorEvento(evento)} hover:opacity-80 transition-opacity ${evento.estado === "completado" ? "line-through opacity-50" : ""}`,
                  title: evento.titulo,
                  children: evento.titulo
                },
                evento.id
              )),
              restantes > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-[10px] text-superficie-500 px-1", children: [
                "+",
                restantes,
                " más"
              ] })
            ] })
          ]
        },
        dia
      );
    }) })
  ] });
}
const DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const COLORES_TIPO$1 = {
  plazo_notificacion: "bg-violet-500/80",
  vencimiento_certificado: "bg-amber-500/80",
  recordatorio: "bg-blue-500/80"
};
const COLORES_URGENCIA$2 = {
  critica: "border-l-red-500",
  alta: "border-l-amber-500",
  media: "border-l-green-500",
  baja: "border-l-blue-500"
};
function obtenerDiasSemana(inicio) {
  const dias = [];
  const lunes = new Date(inicio);
  const diaSemana = lunes.getDay();
  const diff = diaSemana === 0 ? -6 : 1 - diaSemana;
  lunes.setDate(lunes.getDate() + diff);
  for (let i = 0; i < 7; i++) {
    const d = new Date(lunes);
    d.setDate(lunes.getDate() + i);
    dias.push(d);
  }
  return dias;
}
function formatearImporte(evento) {
  const datos = evento.analisisIA?.datosExtraidos;
  const importe = datos?.importe;
  return importe ? String(importe) : null;
}
function CalendarioSemana({
  eventos,
  semanaInicio,
  onSemanaChange,
  onSeleccionar,
  eventoSeleccionado
}) {
  const diasSemana = obtenerDiasSemana(semanaInicio);
  const hoy = /* @__PURE__ */ new Date();
  hoy.setHours(0, 0, 0, 0);
  const eventosPorDia = /* @__PURE__ */ new Map();
  for (const evento of eventos) {
    const fecha = new Date(evento.fecha);
    const clave = `${fecha.getFullYear()}-${fecha.getMonth()}-${fecha.getDate()}`;
    if (!eventosPorDia.has(clave)) eventosPorDia.set(clave, []);
    eventosPorDia.get(clave).push(evento);
  }
  const irSemanaAnterior = () => {
    const nueva = new Date(semanaInicio);
    nueva.setDate(nueva.getDate() - 7);
    onSemanaChange(nueva);
  };
  const irSemanaSiguiente = () => {
    const nueva = new Date(semanaInicio);
    nueva.setDate(nueva.getDate() + 7);
    onSemanaChange(nueva);
  };
  const rangoTexto = `${diasSemana[0].toLocaleDateString("es-ES", { day: "numeric", month: "short" })} – ${diasSemana[6].toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" })}`;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/50 border border-white/[0.06] rounded-xl overflow-hidden", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-5 py-3 border-b border-white/[0.06]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: irSemanaAnterior,
          className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-5 h-5" })
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: rangoTexto }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: irSemanaSiguiente,
          className: "p-1.5 rounded-lg text-superficie-400 hover:text-white hover:bg-white/[0.05] transition-colors",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-5 h-5" })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-7 min-h-[300px]", children: diasSemana.map((dia, idx) => {
      const clave = `${dia.getFullYear()}-${dia.getMonth()}-${dia.getDate()}`;
      const eventosDelDia = eventosPorDia.get(clave) ?? [];
      const esHoy = dia.getTime() === hoy.getTime();
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: `border-r border-white/[0.03] last:border-r-0 ${esHoy ? "bg-acento-500/5" : ""}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center py-2 border-b border-white/[0.06]", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-superficie-500 uppercase font-semibold", children: DIAS_SEMANA[idx] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm ${esHoy ? "text-acento-400 font-bold" : "text-superficie-300"}`, children: dia.getDate() })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-1 space-y-1 max-h-[250px] overflow-y-auto", children: eventosDelDia.map((evento) => {
              const importe = formatearImporte(evento);
              const seleccionado = evento.id === eventoSeleccionado;
              return /* @__PURE__ */ jsxRuntimeExports.jsxs(
                "button",
                {
                  onClick: () => onSeleccionar(evento),
                  className: `w-full text-left p-1.5 rounded-md border-l-2 ${COLORES_URGENCIA$2[evento.urgencia] ?? "border-l-superficie-500"} transition-colors ${seleccionado ? "bg-acento-500/10 ring-1 ring-acento-500/30" : "bg-superficie-800/50 hover:bg-superficie-800"}`,
                  children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1 mb-0.5", children: [
                      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `w-1.5 h-1.5 rounded-full shrink-0 ${COLORES_TIPO$1[evento.tipo] ?? "bg-superficie-500"}` }),
                      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] text-white truncate font-medium", children: evento.titulo })
                    ] }),
                    importe && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-amber-400 font-medium truncate pl-2.5", children: importe })
                  ]
                },
                evento.id
              );
            }) })
          ]
        },
        idx
      );
    }) })
  ] });
}
const COLORES_URGENCIA$1 = {
  critica: { bg: "bg-red-500/20", text: "text-red-400" },
  alta: { bg: "bg-amber-500/20", text: "text-amber-400" },
  media: { bg: "bg-green-500/20", text: "text-green-400" },
  baja: { bg: "bg-blue-500/20", text: "text-blue-400" }
};
const COLORES_SUBTIPO$1 = {
  acceso: { bg: "bg-red-500/10", text: "text-red-400", label: "Acceso" },
  respuesta: { bg: "bg-amber-500/10", text: "text-amber-400", label: "Respuesta" },
  recurso: { bg: "bg-blue-500/10", text: "text-blue-400", label: "Recurso" },
  manual: { bg: "bg-purple-500/10", text: "text-purple-400", label: "Plazo manual" },
  notificacion: { bg: "bg-superficie-700/50", text: "text-superficie-300", label: "Fecha notificación" }
};
function formatearFecha(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" });
}
function calcularDiasRestantes$1(iso) {
  const ahora = /* @__PURE__ */ new Date();
  ahora.setHours(0, 0, 0, 0);
  const fecha = new Date(iso);
  fecha.setHours(0, 0, 0, 0);
  return Math.ceil((fecha.getTime() - ahora.getTime()) / (1e3 * 60 * 60 * 24));
}
function colorDias$1(dias) {
  if (dias <= 0) return "text-superficie-500 line-through";
  if (dias <= 3) return "text-red-400";
  if (dias <= 7) return "text-amber-400";
  return "text-emerald-400";
}
function EventoExpandido({ evento, onCerrar, onActualizado }) {
  const navigate = useNavigate();
  const [accionando, setAccionando] = reactExports.useState(null);
  const [mostrarFormPlazo, setMostrarFormPlazo] = reactExports.useState(false);
  const [fechaPlazoInput, setFechaPlazoInput] = reactExports.useState("");
  const [notaPlazoInput, setNotaPlazoInput] = reactExports.useState("");
  const diasRestantes = calcularDiasRestantes$1(evento.fecha);
  const urgenciaColor = COLORES_URGENCIA$1[evento.urgencia] ?? COLORES_URGENCIA$1.baja;
  const subtipoColor = evento.subtipo ? COLORES_SUBTIPO$1[evento.subtipo] : null;
  async function marcarEstado(estado) {
    if (evento.tipo !== "plazo_notificacion") return;
    setAccionando(`estado-${estado}`);
    try {
      await actualizarNotificacionApi(evento.referenciaId, { estado });
      onActualizado?.();
    } catch {
    }
    setAccionando(null);
  }
  async function analizarConIA() {
    if (evento.tipo !== "plazo_notificacion") return;
    setAccionando("analizar");
    try {
      await analizarNotificacionApi(evento.referenciaId);
      onActualizado?.();
    } catch {
    }
    setAccionando(null);
  }
  async function crearTarea() {
    setAccionando("tarea");
    try {
      await crearTareaApi({
        titulo: evento.titulo,
        descripcion: `Referencia: ${evento.referenciaNombre ?? ""}`,
        prioridad: evento.urgencia === "critica" ? "alta" : evento.urgencia === "alta" ? "media" : "baja",
        referenciaId: evento.referenciaId,
        referenciaTipo: evento.tipo === "plazo_notificacion" ? "notificacion" : evento.tipo === "vencimiento_certificado" ? "certificado" : void 0
      });
      onActualizado?.();
    } catch {
    }
    setAccionando(null);
  }
  async function syncCalendario() {
    if (evento.tipo !== "plazo_notificacion") return;
    setAccionando("sync");
    try {
      await syncPlazosApi(evento.referenciaId);
      onActualizado?.();
    } catch {
    }
    setAccionando(null);
  }
  async function guardarPlazoManual() {
    if (!fechaPlazoInput || evento.tipo !== "plazo_notificacion") return;
    setAccionando("plazo-manual");
    try {
      const fechaISO = (/* @__PURE__ */ new Date(fechaPlazoInput + "T12:00:00")).toISOString();
      await actualizarNotificacionApi(evento.referenciaId, {
        fechaPlazoManual: fechaISO,
        notaPlazoManual: notaPlazoInput || null
      });
      setMostrarFormPlazo(false);
      setFechaPlazoInput("");
      setNotaPlazoInput("");
      onActualizado?.();
    } catch {
    }
    setAccionando(null);
  }
  async function eliminarPlazoManual() {
    if (evento.tipo !== "plazo_notificacion") return;
    setAccionando("eliminar-plazo");
    try {
      await actualizarNotificacionApi(evento.referenciaId, {
        fechaPlazoManual: null,
        notaPlazoManual: null
      });
      onActualizado?.();
    } catch {
    }
    setAccionando(null);
  }
  function irAReferencia() {
    if (evento.tipo === "plazo_notificacion") {
      navigate("/app/notificaciones");
    } else if (evento.tipo === "vencimiento_certificado") {
      navigate("/app/certificados");
    } else {
      navigate("/app/calendario");
    }
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-superficie-900/80 border border-white/[0.08] rounded-xl p-5 space-y-4 animate-in fade-in duration-200", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0 flex-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 flex-wrap mb-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${urgenciaColor.bg} ${urgenciaColor.text}`, children: evento.urgencia.toUpperCase() }),
          subtipoColor && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium ${subtipoColor.bg} ${subtipoColor.text}`, children: subtipoColor.label }),
          evento.sincronizadoGoogle && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] bg-green-500/10 text-green-400", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: "w-3 h-3" }),
            " Sync"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white truncate", children: evento.titulo }),
        evento.referenciaNombre && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400 mt-0.5", children: evento.referenciaNombre })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 shrink-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-right", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400", children: formatearFecha(evento.fecha) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm font-bold ${colorDias$1(diasRestantes)}`, children: diasRestantes <= 0 ? "Vencido" : `${diasRestantes}d` })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "p-1 rounded hover:bg-white/[0.05] text-superficie-400 hover:text-white", children: /* @__PURE__ */ jsxRuntimeExports.jsx(CircleX, { className: "w-4 h-4" }) })
      ] })
    ] }),
    evento.tipo === "plazo_notificacion" && /* @__PURE__ */ jsxRuntimeExports.jsx(SeccionNotificacion, { evento }),
    evento.tipo === "vencimiento_certificado" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-3 bg-superficie-800/50 rounded-lg border border-white/[0.04]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-5 h-5 text-amber-400 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-400", children: "Certificado vence el" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white font-medium", children: formatearFecha(evento.fecha) })
      ] })
    ] }),
    evento.tipo === "recordatorio" && evento.contenido && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-300 bg-superficie-800/50 rounded-lg p-3 border border-white/[0.04]", children: evento.contenido }),
    evento.plazos && /* @__PURE__ */ jsxRuntimeExports.jsx(SeccionPlazos, { plazos: evento.plazos }),
    evento.tipo === "plazo_notificacion" && mostrarFormPlazo && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 bg-purple-500/5 rounded-lg border border-purple-500/10 space-y-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-[10px] font-semibold text-purple-400 uppercase flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(CalendarPlus, { className: "w-3 h-3" }),
        " Fijar plazo manual"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "date",
          value: fechaPlazoInput,
          onChange: (e) => setFechaPlazoInput(e.target.value),
          className: "flex-1 px-2 py-1.5 text-xs rounded-lg bg-superficie-800 border border-white/[0.08] text-white focus:outline-none focus:border-acento-500/40"
        }
      ) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "text",
          placeholder: "Nota (ej: Plazo recurso alzada)",
          value: notaPlazoInput,
          onChange: (e) => setNotaPlazoInput(e.target.value),
          maxLength: 500,
          className: "w-full px-2 py-1.5 text-xs rounded-lg bg-superficie-800 border border-white/[0.08] text-white placeholder:text-superficie-500 focus:outline-none focus:border-acento-500/40"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: guardarPlazoManual,
            disabled: !fechaPlazoInput || accionando === "plazo-manual",
            className: "flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-acento-500/20 text-acento-400 border border-acento-500/20 hover:bg-acento-500/30 transition-colors disabled:opacity-50",
            children: [
              accionando === "plazo-manual" ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3 h-3 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "w-3 h-3" }),
              "Guardar"
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => {
              setMostrarFormPlazo(false);
              setFechaPlazoInput("");
              setNotaPlazoInput("");
            },
            className: "px-3 py-1.5 rounded-lg text-xs font-medium text-superficie-400 border border-white/[0.06] hover:bg-superficie-800 transition-colors",
            children: "Cancelar"
          }
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-2 pt-2 border-t border-white/[0.06]", children: [
      evento.tipo === "plazo_notificacion" && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          BotonAccion,
          {
            icono: CircleCheckBig,
            etiqueta: "Gestionar",
            onClick: () => marcarEstado("gestionada"),
            cargando: accionando === "estado-gestionada",
            color: "text-acento-400"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          BotonAccion,
          {
            icono: Brain,
            etiqueta: "Analizar IA",
            onClick: analizarConIA,
            cargando: accionando === "analizar",
            color: "text-purple-400"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          BotonAccion,
          {
            icono: RefreshCw,
            etiqueta: "Sync Cal.",
            onClick: syncCalendario,
            cargando: accionando === "sync",
            color: "text-green-400"
          }
        ),
        !mostrarFormPlazo && /* @__PURE__ */ jsxRuntimeExports.jsx(
          BotonAccion,
          {
            icono: CalendarPlus,
            etiqueta: "Fijar plazo",
            onClick: () => setMostrarFormPlazo(true),
            cargando: false,
            color: "text-purple-400"
          }
        ),
        evento.subtipo === "manual" && /* @__PURE__ */ jsxRuntimeExports.jsx(
          BotonAccion,
          {
            icono: Trash2,
            etiqueta: "Quitar plazo",
            onClick: eliminarPlazoManual,
            cargando: accionando === "eliminar-plazo",
            color: "text-red-400"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        BotonAccion,
        {
          icono: ClipboardList,
          etiqueta: "Crear tarea",
          onClick: crearTarea,
          cargando: accionando === "tarea",
          color: "text-blue-400"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        BotonAccion,
        {
          icono: ExternalLink,
          etiqueta: "Ir a detalle",
          onClick: irAReferencia,
          cargando: false,
          color: "text-superficie-300"
        }
      )
    ] })
  ] });
}
function SeccionNotificacion({ evento }) {
  const ia = evento.analisisIA;
  if (!ia) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 italic", children: "Sin análisis IA disponible" });
  }
  const datos = ia.datosExtraidos;
  const importe = datos?.importe;
  const datosVisibles = datos ? Object.entries(datos).filter(([k]) => k !== "importe" && k !== "plazoRecurso").slice(0, 6) : [];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
    ia.resumen ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-3 bg-purple-500/5 rounded-lg border border-purple-500/10", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1.5 mb-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Brain, { className: "w-3.5 h-3.5 text-purple-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-semibold text-purple-400 uppercase", children: "Análisis IA" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-200 leading-relaxed", children: ia.resumen })
    ] }) : null,
    importe ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 p-2 bg-superficie-800/50 rounded-lg border border-white/[0.04]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(TrendingUp, { className: "w-4 h-4 text-amber-400" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-400", children: "Importe:" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-bold text-amber-300", children: importe })
    ] }) : null,
    datosVisibles.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-2", children: datosVisibles.map(([campo, valor], i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "p-2 bg-superficie-800/30 rounded border border-white/[0.03]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-superficie-500 uppercase", children: campo }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-200 truncate", children: String(valor) })
    ] }, i)) }) : null,
    ia.accionesRequeridas && ia.accionesRequeridas.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-[10px] font-semibold text-superficie-400 uppercase flex items-center gap-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(ShieldAlert, { className: "w-3 h-3" }),
        " Acciones requeridas"
      ] }),
      ia.accionesRequeridas.map((accion, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-2 text-xs", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowRight, { className: "w-3 h-3 text-acento-400 mt-0.5 shrink-0" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-300", children: accion.accion }),
        accion.plazo && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-superficie-500 shrink-0", children: [
          "(",
          accion.plazo,
          ")"
        ] })
      ] }, i))
    ] })
  ] });
}
function SeccionPlazos({ plazos }) {
  const items = [
    { label: "Acceso", fecha: plazos.fechaLimiteAcceso, dias: plazos.diasRestantesAcceso },
    { label: "Respuesta", fecha: plazos.fechaLimiteRespuesta, dias: plazos.diasRestantesRespuesta },
    { label: "Recurso", fecha: plazos.fechaLimiteRecurso, dias: plazos.diasRestantesRecurso }
  ].filter((p) => p.fecha);
  if (items.length === 0) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-3", children: items.map((p) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 p-2 bg-superficie-800/50 rounded-lg border border-white/[0.04] text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-superficie-500 uppercase", children: p.label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-300", children: formatearFechaCorta(p.fecha) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm font-bold ${colorDiasPlazos(p.dias)}`, children: p.dias != null ? p.dias <= 0 ? "Vencido" : `${p.dias}d` : "—" })
  ] }, p.label)) });
}
function formatearFechaCorta(iso) {
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}
function colorDiasPlazos(dias) {
  if (dias == null) return "text-superficie-500";
  if (dias <= 0) return "text-superficie-500";
  if (dias <= 3) return "text-red-400";
  if (dias <= 7) return "text-amber-400";
  return "text-emerald-400";
}
function BotonAccion({
  icono: Icono,
  etiqueta,
  onClick,
  cargando,
  color
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "button",
    {
      onClick,
      disabled: cargando,
      className: `flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border border-white/[0.06] bg-superficie-800/50 hover:bg-superficie-800 transition-colors disabled:opacity-50 ${color}`,
      children: [
        cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-3.5 h-3.5 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-3.5 h-3.5" }),
        etiqueta
      ]
    }
  );
}
const COLORES_URGENCIA = {
  critica: "bg-red-500/20 text-red-400 border-red-500/30",
  alta: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  media: "bg-green-500/20 text-green-400 border-green-500/30",
  baja: "bg-blue-500/20 text-blue-400 border-blue-500/30"
};
const ICONOS_TIPO = {
  plazo_notificacion: Bell,
  vencimiento_certificado: FileText,
  recordatorio: Calendar
};
const ETIQUETAS_TIPO = {
  plazo_notificacion: "Notificación",
  vencimiento_certificado: "Certificado",
  recordatorio: "Recordatorio"
};
const COLORES_TIPO = {
  plazo_notificacion: "text-violet-400",
  vencimiento_certificado: "text-amber-400",
  recordatorio: "text-blue-400"
};
const COLORES_SUBTIPO = {
  acceso: "bg-red-500/10 text-red-400 border-red-500/20",
  respuesta: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  recurso: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  manual: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  notificacion: "bg-superficie-800 text-superficie-400 border-white/[0.04]"
};
const ETIQUETAS_SUBTIPO = {
  acceso: "Acceso",
  respuesta: "Respuesta",
  recurso: "Recurso",
  manual: "Plazo manual",
  notificacion: "Fecha notif."
};
function formatearFechaGrupo(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
}
function formatearHora(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" });
}
function calcularDiasRestantes(iso) {
  const ahora = /* @__PURE__ */ new Date();
  ahora.setHours(0, 0, 0, 0);
  const fecha = new Date(iso);
  fecha.setHours(0, 0, 0, 0);
  return Math.ceil((fecha.getTime() - ahora.getTime()) / (1e3 * 60 * 60 * 24));
}
function colorDias(dias) {
  if (dias <= 0) return "text-superficie-500";
  if (dias <= 3) return "text-red-400";
  if (dias <= 7) return "text-amber-400";
  return "text-emerald-400";
}
function agruparPorDia(eventos) {
  const grupos = /* @__PURE__ */ new Map();
  for (const evento of eventos) {
    const d = new Date(evento.fecha);
    const clave = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    if (!grupos.has(clave)) grupos.set(clave, []);
    grupos.get(clave).push(evento);
  }
  return grupos;
}
function ListaEventos({ eventos, eventoExpandido, onExpandir, onActualizado }) {
  const grupos = agruparPorDia(eventos);
  if (eventos.length === 0) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center py-12 text-superficie-500", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Calendar, { className: "w-10 h-10 mb-3 opacity-40" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm", children: "Sin eventos en este período" })
    ] });
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-4", children: Array.from(grupos.entries()).map(([clave, eventosGrupo]) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-px flex-1 bg-white/[0.06]" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-semibold text-superficie-400 capitalize whitespace-nowrap", children: formatearFechaGrupo(eventosGrupo[0].fecha) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-px flex-1 bg-white/[0.06]" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: eventosGrupo.map((evento) => {
      const expandido = eventoExpandido === evento.id;
      const Icono = ICONOS_TIPO[evento.tipo] ?? Calendar;
      const dias = calcularDiasRestantes(evento.fecha);
      return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => onExpandir(expandido ? null : evento.id),
            className: `w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-colors text-left ${expandido ? "bg-superficie-800/80 border-acento-500/20" : "bg-superficie-900/50 border-white/[0.06] hover:bg-superficie-800/50"}`,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-4 h-4 shrink-0 ${COLORES_TIPO[evento.tipo] ?? "text-superficie-400"}` }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500 w-12 shrink-0", children: formatearHora(evento.fecha) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm text-white truncate flex-1", children: evento.titulo }),
              evento.subtipo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${COLORES_SUBTIPO[evento.subtipo] ?? "bg-superficie-800 text-superficie-400 border-white/[0.04]"}`, children: ETIQUETAS_SUBTIPO[evento.subtipo] ?? evento.subtipo }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border shrink-0 ${COLORES_URGENCIA[evento.urgencia]}`, children: evento.urgencia }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] text-superficie-500 shrink-0 hidden sm:block", children: ETIQUETAS_TIPO[evento.tipo] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-bold shrink-0 w-10 text-right ${colorDias(dias)}`, children: dias <= 0 ? "—" : `${dias}d` })
            ]
          }
        ),
        expandido && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-2 ml-7", children: /* @__PURE__ */ jsxRuntimeExports.jsx(
          EventoExpandido,
          {
            evento,
            onCerrar: () => onExpandir(null),
            onActualizado
          }
        ) })
      ] }, evento.id);
    }) })
  ] }, clave)) });
}
function adaptarParaCalendarioMes(eventos) {
  return eventos.map((e) => ({
    id: e.id,
    titulo: e.titulo,
    fecha: e.fecha,
    tipo: e.tipo === "plazo_notificacion" ? "notificacion" : e.tipo === "vencimiento_certificado" ? "vencimiento_certificado" : "manual",
    estado: e.estado === "completado" ? "completado" : e.estado === "descartado" ? "descartado" : "pendiente",
    urgencia: e.urgencia,
    referenciaId: e.referenciaId,
    nombreReferencia: e.referenciaNombre,
    esRecordatorioManual: e.tipo === "recordatorio"
  }));
}
function PaginaCalendarioUnificado() {
  const [vista, setVista] = reactExports.useState("mes");
  const [mesActual, setMesActual] = reactExports.useState(() => {
    const ahora = /* @__PURE__ */ new Date();
    return new Date(ahora.getFullYear(), ahora.getMonth(), 1);
  });
  const [semanaActual, setSemanaActual] = reactExports.useState(() => /* @__PURE__ */ new Date());
  const [tipo, setTipo] = reactExports.useState("todos");
  const [urgencia, setUrgencia] = reactExports.useState("todas");
  const [soloPendientes, setSoloPendientes] = reactExports.useState(false);
  const [administracion, setAdministracion] = reactExports.useState("");
  const [eventoExpandido, setEventoExpandido] = reactExports.useState(null);
  const [diaSeleccionado, setDiaSeleccionado] = reactExports.useState(null);
  const [eventos, setEventos] = reactExports.useState([]);
  const [kpis, setKpis] = reactExports.useState(null);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const calcularRango = reactExports.useCallback(() => {
    if (vista === "mes" || vista === "lista") {
      const desde = new Date(mesActual.getFullYear(), mesActual.getMonth(), 1);
      const hasta = new Date(mesActual.getFullYear(), mesActual.getMonth() + 1, 0, 23, 59, 59);
      return { desde: desde.toISOString(), hasta: hasta.toISOString() };
    }
    const lunes = new Date(semanaActual);
    const diaSemana = lunes.getDay();
    const diff = diaSemana === 0 ? -6 : 1 - diaSemana;
    lunes.setDate(lunes.getDate() + diff);
    lunes.setHours(0, 0, 0, 0);
    const domingo = new Date(lunes);
    domingo.setDate(lunes.getDate() + 6);
    domingo.setHours(23, 59, 59, 999);
    return { desde: lunes.toISOString(), hasta: domingo.toISOString() };
  }, [vista, mesActual, semanaActual]);
  const cargarDatos = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const rango = calcularRango();
      const [eventosRes, kpisRes] = await Promise.all([
        listarEventosCalendarioUnificadoApi({
          ...rango,
          tipo,
          urgencia,
          administracion: administracion || void 0,
          soloPendientes
        }),
        obtenerKpisCalendarioApi()
      ]);
      setEventos(eventosRes);
      setKpis(kpisRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar calendario");
    } finally {
      setCargando(false);
    }
  }, [calcularRango, tipo, urgencia, administracion, soloPendientes]);
  reactExports.useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);
  const administraciones = reactExports.useMemo(() => {
    const set = /* @__PURE__ */ new Set();
    for (const e of eventos) {
      if (e.administracion) set.add(e.administracion);
    }
    return Array.from(set).sort();
  }, [eventos]);
  const eventosVisibles = reactExports.useMemo(() => {
    if (vista === "mes" && diaSeleccionado != null) {
      return eventos.filter((e) => {
        const d = new Date(e.fecha);
        return d.getDate() === diaSeleccionado && d.getMonth() === mesActual.getMonth() && d.getFullYear() === mesActual.getFullYear();
      });
    }
    return eventos;
  }, [eventos, vista, diaSeleccionado, mesActual]);
  const eventoSeleccionadoSemana = reactExports.useMemo(
    () => eventos.find((e) => e.id === eventoExpandido) ?? null,
    [eventos, eventoExpandido]
  );
  function handleClickEventoMes(evento) {
    const match = eventos.find((e) => e.id === evento.id);
    if (match) {
      setEventoExpandido(match.id);
      const d = new Date(match.fecha);
      setDiaSeleccionado(d.getDate());
    }
  }
  function handleMesCambiado(nuevoMes) {
    setMesActual(nuevoMes);
    setDiaSeleccionado(null);
    setEventoExpandido(null);
  }
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-bold text-white", children: "Calendario" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: cargarDatos,
          disabled: cargando,
          className: "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-superficie-300 border border-white/[0.06] bg-superficie-900/50 hover:bg-superficie-800 transition-colors disabled:opacity-50",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(RefreshCw, { className: `w-3.5 h-3.5 ${cargando ? "animate-spin" : ""}` }),
            "Actualizar"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      FiltrosCalendario,
      {
        vista,
        onVistaChange: setVista,
        tipo,
        onTipoChange: setTipo,
        urgencia,
        onUrgenciaChange: setUrgencia,
        soloPendientes,
        onSoloPendientesChange: setSoloPendientes,
        administraciones,
        administracion,
        onAdministracionChange: setAdministracion
      }
    ),
    /* @__PURE__ */ jsxRuntimeExports.jsx(KPIsCalendario, { kpis, cargando }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      error
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center py-8", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }) }),
    !cargando && vista === "mes" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CalendarioMes,
        {
          mes: mesActual,
          eventos: adaptarParaCalendarioMes(eventos),
          onMesCambiado: handleMesCambiado,
          onClickEvento: handleClickEventoMes,
          cargando: false
        }
      ),
      diaSeleccionado != null && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-superficie-400", children: [
            "Eventos del ",
            diaSeleccionado,
            " de ",
            mesActual.toLocaleDateString("es-ES", { month: "long" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => {
                setDiaSeleccionado(null);
                setEventoExpandido(null);
              },
              className: "text-xs text-superficie-500 hover:text-white",
              children: "Ver todos"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          ListaEventos,
          {
            eventos: eventosVisibles,
            eventoExpandido,
            onExpandir: setEventoExpandido,
            onActualizado: cargarDatos
          }
        )
      ] })
    ] }),
    !cargando && vista === "semana" && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        CalendarioSemana,
        {
          eventos,
          semanaInicio: semanaActual,
          onSemanaChange: setSemanaActual,
          onSeleccionar: (e) => setEventoExpandido(e.id),
          eventoSeleccionado: eventoExpandido ?? void 0
        }
      ),
      eventoSeleccionadoSemana && /* @__PURE__ */ jsxRuntimeExports.jsx(
        EventoExpandido,
        {
          evento: eventoSeleccionadoSemana,
          onCerrar: () => setEventoExpandido(null),
          onActualizado: cargarDatos
        }
      )
    ] }),
    !cargando && vista === "lista" && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ListaEventos,
      {
        eventos,
        eventoExpandido,
        onExpandir: setEventoExpandido,
        onActualizado: cargarDatos
      }
    )
  ] });
}
export {
  PaginaCalendarioUnificado
};
