import { d as apiClient, z as useAuthStore, r as reactExports, j as jsxRuntimeExports, ac as PLANES, ad as CreditCard, v as Check, s as ArrowRight } from "./index-DMbE3NR1.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
async function obtenerSuscripcionApi() {
  const respuesta = await apiClient.get("/suscripciones");
  return respuesta.datos ?? null;
}
async function crearCheckoutApi(datos) {
  const respuesta = await apiClient.post("/suscripciones/checkout", datos);
  return respuesta.datos;
}
async function crearPortalApi() {
  const respuesta = await apiClient.post("/suscripciones/portal", {});
  return respuesta.datos;
}
async function cancelarSuscripcionApi(datos) {
  await apiClient.post("/suscripciones/cancelar", {});
}
const ORDEN_PLANES = ["basico", "profesional", "plus"];
function formatearPrecio(precio) {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" }).format(precio);
}
function PaginaSuscripcion() {
  const usuario = useAuthStore((s) => s.usuario);
  const planOrganizacion = usuario?.organizacion?.plan ?? "basico";
  const [suscripcion, setSuscripcion] = reactExports.useState(null);
  const [periodo, setPeriodo] = reactExports.useState("mensual");
  const [cargando, setCargando] = reactExports.useState(true);
  const [cargandoCheckout, setCargandoCheckout] = reactExports.useState(null);
  const [cargandoPortal, setCargandoPortal] = reactExports.useState(false);
  const [cargandoCancelar, setCargandoCancelar] = reactExports.useState(false);
  const [error, setError] = reactExports.useState(null);
  reactExports.useEffect(() => {
    cargarSuscripcion();
  }, []);
  async function cargarSuscripcion() {
    try {
      setCargando(true);
      const datos = await obtenerSuscripcionApi();
      setSuscripcion(datos);
    } catch {
      setError("Error al cargar la suscripción");
    } finally {
      setCargando(false);
    }
  }
  async function manejarCheckout(planId) {
    try {
      setCargandoCheckout(planId);
      setError(null);
      const sesion = await crearCheckoutApi({ planId, periodo });
      window.location.href = sesion.url;
    } catch {
      setError("Error al iniciar el proceso de pago");
      setCargandoCheckout(null);
    }
  }
  async function manejarPortal() {
    try {
      setCargandoPortal(true);
      setError(null);
      const sesion = await crearPortalApi();
      window.location.href = sesion.url;
    } catch {
      setError("Error al acceder al portal de facturación");
      setCargandoPortal(false);
    }
  }
  async function manejarCancelar() {
    if (!window.confirm("¿Estás seguro de que quieres cancelar tu suscripción?")) return;
    try {
      setCargandoCancelar(true);
      setError(null);
      await cancelarSuscripcionApi();
      await cargarSuscripcion();
    } catch {
      setError("Error al cancelar la suscripción");
    } finally {
      setCargandoCancelar(false);
    }
  }
  function esPlanActual(planId) {
    if (suscripcion?.estado === "activa") {
      return suscripcion.plan === planId;
    }
    return planOrganizacion === planId;
  }
  function esPlanSuperior(planId) {
    const planActual = suscripcion?.estado === "activa" ? suscripcion.plan : planOrganizacion;
    const ordenActual = ORDEN_PLANES.indexOf(planActual);
    const ordenObjetivo = ORDEN_PLANES.indexOf(planId);
    return ordenObjetivo > ordenActual;
  }
  if (cargando) {
    return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center h-64", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-8 h-8 text-acento-400 animate-spin" }) });
  }
  const ahorroAnual = {
    basico: Math.round((PLANES.basico.precioMensual * 12 - PLANES.basico.precioAnual) / (PLANES.basico.precioMensual * 12) * 100),
    profesional: Math.round((PLANES.profesional.precioMensual * 12 - PLANES.profesional.precioAnual) / (PLANES.profesional.precioMensual * 12) * 100),
    plus: Math.round((PLANES.plus.precioMensual * 12 - PLANES.plus.precioAnual) / (PLANES.plus.precioMensual * 12) * 100)
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-8", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(CreditCard, { className: "w-5 h-5 text-acento-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Suscripción" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 text-sm", children: "Gestiona tu plan y facturación" })
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 p-4 cristal rounded-xl border border-red-500/20 text-red-400", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 shrink-0" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm", children: error })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm font-medium ${periodo === "mensual" ? "text-white" : "text-superficie-400"}`, children: "Mensual" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => setPeriodo((p) => p === "mensual" ? "anual" : "mensual"),
          className: `relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${periodo === "anual" ? "bg-acento-500" : "bg-superficie-700"}`,
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(
            "span",
            {
              className: `inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${periodo === "anual" ? "translate-x-6" : "translate-x-1"}`
            }
          )
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-sm font-medium ${periodo === "anual" ? "text-white" : "text-superficie-400"}`, children: "Anual" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-acento-500/10 text-acento-400 border border-acento-500/20", children: [
          "Ahorra hasta ",
          ahorroAnual.plus,
          "%"
        ] })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-1 md:grid-cols-3 gap-6", children: ORDEN_PLANES.map((planId) => {
      const plan = PLANES[planId];
      const activo = esPlanActual(planId);
      const superior = esPlanSuperior(planId);
      const procesando = cargandoCheckout === planId;
      const precio = periodo === "mensual" ? plan.precioMensual : Math.round(plan.precioAnual / 12);
      const precioTotal = periodo === "anual" ? plan.precioAnual : null;
      return /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: `cristal rounded-xl p-6 flex flex-col gap-4 transition-all ${activo ? "border border-acento-500/30 ring-1 ring-acento-500/20" : ""}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start justify-between mb-3", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-base font-semibold text-white", children: plan.nombre }),
                activo && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-acento-500/10 text-acento-400 border border-acento-500/20", children: "Plan actual" })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-baseline gap-1", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-3xl font-bold text-white", children: formatearPrecio(precio) }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-400 text-sm", children: "/mes" })
              ] }),
              precioTotal && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-superficie-500 text-xs mt-1", children: [
                formatearPrecio(precioTotal),
                "/año · ahorras ",
                ahorroAnual[planId],
                "%"
              ] }),
              plan.maxAsesores > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-superficie-400 text-xs mt-1", children: [
                "Hasta ",
                plan.maxAsesores,
                " asesores"
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "space-y-2 flex-1", children: plan.caracteristicas.map((caracteristica) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex items-start gap-2 text-sm text-superficie-300", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "w-4 h-4 text-acento-400 shrink-0 mt-0.5" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: caracteristica })
            ] }, caracteristica)) }),
            activo ? /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                disabled: true,
                className: "w-full py-2.5 px-4 rounded-lg text-sm font-medium text-superficie-500 border border-white/[0.06] cursor-not-allowed",
                children: "Plan actual"
              }
            ) : /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => manejarCheckout(planId),
                disabled: procesando,
                className: `w-full py-2.5 px-4 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 ${superior ? "bg-acento-500 hover:bg-acento-400 text-superficie-950 font-semibold disabled:opacity-60" : "border border-white/[0.06] text-superficie-300 hover:bg-white/[0.05] disabled:opacity-60"}`,
                children: procesando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
                  superior ? "Mejorar plan" : "Cambiar plan",
                  /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowRight, { className: "w-4 h-4" })
                ] })
              }
            )
          ]
        },
        planId
      );
    }) }),
    suscripcion && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-xl p-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-base font-semibold text-white mb-4", children: "Tu suscripción" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 md:grid-cols-4 gap-4 mb-6", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Plan" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white capitalize", children: suscripcion.plan })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Período" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white capitalize", children: suscripcion.periodo })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Estado" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${suscripcion.estado === "activa" ? "bg-green-500/10 text-green-400 border border-green-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`, children: suscripcion.estado })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Inicio" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white", children: new Date(suscripcion.fechaInicio).toLocaleDateString("es-ES") })
        ] }),
        suscripcion.fechaFin && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mb-1", children: "Fin" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-white", children: new Date(suscripcion.fechaFin).toLocaleDateString("es-ES") })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 flex-wrap", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarPortal,
            disabled: cargandoPortal,
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium bg-acento-500 hover:bg-acento-400 text-superficie-950 rounded-lg transition-colors disabled:opacity-60",
            children: [
              cargandoPortal ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CreditCard, { className: "w-4 h-4" }),
              "Gestionar suscripción"
            ]
          }
        ),
        suscripcion.estado === "activa" && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarCancelar,
            disabled: cargandoCancelar,
            className: "flex items-center gap-2 px-4 py-2 text-sm font-medium border border-red-500/20 text-red-400 hover:bg-red-500/5 rounded-lg transition-colors disabled:opacity-60",
            children: [
              cargandoCancelar ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : null,
              "Cancelar suscripción"
            ]
          }
        )
      ] })
    ] })
  ] });
}
export {
  PaginaSuscripcion
};
