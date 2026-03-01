import { j as jsxRuntimeExports, T as TriangleAlert, b as Link } from "./index-DMbE3NR1.js";
function PaginaPortalExpirado() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "min-h-screen bg-superficie-950 flex items-center justify-center px-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-md w-full text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-6", children: /* @__PURE__ */ jsxRuntimeExports.jsx(TriangleAlert, { className: "w-8 h-8 text-amber-400" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white mb-3", children: "Enlace de acceso expirado o revocado" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mb-8 leading-relaxed", children: "Este enlace ya no es valido. Contacta con tu asesor para obtener uno nuevo." }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Link,
      {
        to: "/",
        className: "inline-flex items-center px-5 py-2.5 bg-acento-500 hover:bg-acento-400 text-superficie-950 text-sm font-semibold rounded-lg transition-colors",
        children: "Volver al inicio"
      }
    )
  ] }) });
}
export {
  PaginaPortalExpirado
};
