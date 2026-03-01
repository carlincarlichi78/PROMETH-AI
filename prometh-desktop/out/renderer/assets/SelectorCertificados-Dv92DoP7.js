import { c as createLucideIcon, r as reactExports, j as jsxRuntimeExports, n as ChevronDown, X, m as Search } from "./index-DMbE3NR1.js";
import { b as listarResumenCertificadosApi } from "./certificadosServicio-DtEVLLjT.js";
import { A as Award } from "./award-CLV5ctGj.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const CalendarCheck = createLucideIcon("CalendarCheck", [
  ["path", { d: "M8 2v4", key: "1cmpym" }],
  ["path", { d: "M16 2v4", key: "4m81vk" }],
  ["rect", { width: "18", height: "18", x: "3", y: "4", rx: "2", key: "1hopcy" }],
  ["path", { d: "M3 10h18", key: "8toen8" }],
  ["path", { d: "m9 16 2 2 4-4", key: "19s6y9" }]
]);
function SelectorCertificados({ seleccionados, onChange }) {
  const [abierto, setAbierto] = reactExports.useState(false);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [certificados, setCertificados] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(false);
  const refContenedor = reactExports.useRef(null);
  reactExports.useEffect(() => {
    let cancelado = false;
    setCargando(true);
    listarResumenCertificadosApi().then((datos) => {
      if (!cancelado) setCertificados(datos);
    }).catch(() => {
    }).finally(() => {
      if (!cancelado) setCargando(false);
    });
    return () => {
      cancelado = true;
    };
  }, []);
  reactExports.useEffect(() => {
    function manejarClickFuera(e) {
      if (refContenedor.current && !refContenedor.current.contains(e.target)) {
        setAbierto(false);
      }
    }
    if (abierto) {
      document.addEventListener("mousedown", manejarClickFuera);
      return () => document.removeEventListener("mousedown", manejarClickFuera);
    }
  }, [abierto]);
  const filtrados = certificados.filter((cert) => {
    if (!busqueda) return true;
    const termino = busqueda.toLowerCase();
    return cert.nombreTitular.toLowerCase().includes(termino) || cert.dniCif.toLowerCase().includes(termino);
  });
  const toggleCertificado = reactExports.useCallback((id) => {
    const nuevos = seleccionados.includes(id) ? seleccionados.filter((s) => s !== id) : [...seleccionados, id];
    onChange(nuevos);
  }, [seleccionados, onChange]);
  const limpiarSeleccion = reactExports.useCallback(() => {
    onChange([]);
  }, [onChange]);
  const seleccionadosInfo = certificados.filter((c) => seleccionados.includes(c.id));
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { ref: refContenedor, className: "relative", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs(
      "button",
      {
        type: "button",
        onClick: () => setAbierto(!abierto),
        className: `flex items-center gap-2 px-3 py-2 text-sm rounded-lg border transition-colors ${seleccionados.length > 0 ? "bg-acento-500/10 text-acento-400 border-acento-500/30 hover:bg-acento-500/20" : "bg-superficie-800/60 text-superficie-400 border-white/[0.06] hover:border-white/[0.12]"}`,
        children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Award, { className: "w-3.5 h-3.5" }),
          seleccionados.length === 0 ? "Certificados" : `${seleccionados.length} certificado${seleccionados.length > 1 ? "s" : ""}`,
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: `w-3.5 h-3.5 transition-transform ${abierto ? "rotate-180" : ""}` })
        ]
      }
    ),
    seleccionadosInfo.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-1.5 mt-2", children: [
      seleccionadosInfo.map((cert) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "span",
        {
          className: "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs\n                bg-acento-500/10 text-acento-400 border border-acento-500/20",
          children: [
            cert.nombreTitular.length > 25 ? cert.nombreTitular.substring(0, 23) + "…" : cert.nombreTitular,
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: (e) => {
                  e.stopPropagation();
                  toggleCertificado(cert.id);
                },
                className: "ml-0.5 hover:text-white transition-colors",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-3 h-3" })
              }
            )
          ]
        },
        cert.id
      )),
      seleccionadosInfo.length > 1 && /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: limpiarSeleccion,
          className: "text-xs text-superficie-500 hover:text-red-400 transition-colors px-1",
          children: "Limpiar"
        }
      )
    ] }),
    abierto && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "absolute z-50 mt-1 w-80 max-h-72 rounded-xl border border-white/[0.08]\n          bg-superficie-900 shadow-xl shadow-black/30 overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "px-3 py-2 border-b border-white/[0.06]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-superficie-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            value: busqueda,
            onChange: (e) => setBusqueda(e.target.value),
            placeholder: "Buscar titular o DNI/CIF...",
            autoFocus: true,
            className: "w-full pl-8 pr-3 py-1.5 text-xs text-superficie-100 border border-white/[0.06]\n                  rounded-lg outline-none focus:ring-1 focus:ring-acento-500/40 bg-superficie-800/60\n                  placeholder:text-superficie-600"
          }
        )
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-y-auto max-h-52", children: cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "px-4 py-6 text-center text-xs text-superficie-500", children: "Cargando certificados..." }) : filtrados.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "px-4 py-6 text-center text-xs text-superficie-500", children: busqueda ? "Sin resultados" : "No hay certificados" }) : filtrados.map((cert) => {
        const marcado = seleccionados.includes(cert.id);
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "button",
            onClick: () => toggleCertificado(cert.id),
            className: `w-full flex items-center gap-3 px-3 py-2 text-left text-xs
                      hover:bg-white/[0.04] transition-colors ${marcado ? "bg-acento-500/5" : ""}`,
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors ${marcado ? "bg-acento-500 border-acento-500" : "border-white/[0.12] bg-transparent"}`, children: marcado && /* @__PURE__ */ jsxRuntimeExports.jsx("svg", { className: "w-3 h-3 text-superficie-950", viewBox: "0 0 12 12", fill: "none", children: /* @__PURE__ */ jsxRuntimeExports.jsx("path", { d: "M2.5 6L5 8.5L9.5 3.5", stroke: "currentColor", strokeWidth: "1.5", strokeLinecap: "round", strokeLinejoin: "round" }) }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0 flex-1", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-superficie-100 font-medium truncate", children: cert.nombreTitular }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-superficie-500 truncate", children: cert.dniCif })
              ] })
            ]
          },
          cert.id
        );
      }) })
    ] })
  ] });
}
export {
  CalendarCheck as C,
  SelectorCertificados as S
};
