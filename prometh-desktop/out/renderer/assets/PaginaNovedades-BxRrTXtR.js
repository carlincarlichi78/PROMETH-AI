import { c as createLucideIcon, ae as useNovedadesSinLeer, r as reactExports, j as jsxRuntimeExports, af as novedades, t as Sparkles } from "./index-DMbE3NR1.js";
import { T as TrendingUp } from "./trending-up-zIPd8Al1.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Wrench = createLucideIcon("Wrench", [
  [
    "path",
    {
      d: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
      key: "cbrjhi"
    }
  ]
]);
const ICONOS_TIPO = {
  feature: Sparkles,
  mejora: TrendingUp,
  fix: Wrench
};
const COLORES_TIPO = {
  feature: {
    borde: "border-l-acento-500",
    bg: "bg-acento-500/10",
    texto: "text-acento-400"
  },
  mejora: {
    borde: "border-l-blue-500",
    bg: "bg-blue-500/10",
    texto: "text-blue-400"
  },
  fix: {
    borde: "border-l-amber-500",
    bg: "bg-amber-500/10",
    texto: "text-amber-400"
  }
};
const ETIQUETAS_TIPO = {
  feature: "Nueva funcionalidad",
  mejora: "Mejora",
  fix: "Correccion"
};
function formatearFecha(iso) {
  return new Date(iso).toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric"
  });
}
function PaginaNovedades() {
  const { marcarComoLeidas } = useNovedadesSinLeer();
  reactExports.useEffect(() => {
    marcarComoLeidas();
  }, []);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Novedades" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-1", children: "Ultimas actualizaciones y mejoras de CertiGestor" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-4", children: novedades.map((novedad) => {
      const Icono = ICONOS_TIPO[novedad.tipo];
      const colores = COLORES_TIPO[novedad.tipo];
      return /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: `bg-superficie-900/50 border border-white/[0.06] rounded-xl border-l-4 ${colores.borde} p-5`,
          children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-4", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "div",
              {
                className: `w-10 h-10 rounded-lg ${colores.bg} flex items-center justify-center shrink-0`,
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: `w-5 h-5 ${colores.texto}` })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-1 flex-wrap", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "font-semibold text-white", children: novedad.titulo }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "span",
                  {
                    className: `text-xs px-2 py-0.5 rounded-full ${colores.bg} ${colores.texto}`,
                    children: ETIQUETAS_TIPO[novedad.tipo]
                  }
                ),
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs px-2 py-0.5 rounded-full bg-superficie-800 text-superficie-400", children: [
                  "v",
                  novedad.version
                ] })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-300 mb-2", children: novedad.descripcion }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: formatearFecha(novedad.fecha) })
            ] })
          ] })
        },
        novedad.id
      );
    }) })
  ] });
}
export {
  PaginaNovedades
};
