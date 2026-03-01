import { r as reactExports, j as jsxRuntimeExports } from "./index-DMbE3NR1.js";
import { S as Send } from "./send-mu2rTZak.js";
import { M as Mail } from "./mail-BDEpMyrm.js";
import { P as Phone } from "./phone-GsPdPFZ6.js";
import { C as Clock } from "./clock-BgWzJTcD.js";
const CAMPOS_INICIALES = {
  nombre: "",
  email: "",
  empresa: "",
  mensaje: ""
};
function PaginaContacto() {
  const [campos, setCampos] = reactExports.useState(CAMPOS_INICIALES);
  const [enviado, setEnviado] = reactExports.useState(false);
  const [enviando, setEnviando] = reactExports.useState(false);
  function actualizarCampo(campo) {
    return (e) => {
      setCampos((prev) => ({ ...prev, [campo]: e.target.value }));
    };
  }
  async function manejarEnvio(e) {
    e.preventDefault();
    setEnviando(true);
    await new Promise((resolve) => setTimeout(resolve, 1e3));
    setEnviando(false);
    setEnviado(true);
    setCampos(CAMPOS_INICIALES);
  }
  const estiloInput = "w-full px-4 py-2.5 text-sm text-superficie-100 bg-superficie-800/60 border border-white/[0.06] rounded-xl focus:outline-none focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 transition placeholder:text-superficie-600";
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "py-20 px-4 sm:px-6 lg:px-8", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-5xl mx-auto", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center mb-14", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-semibold text-acento-400 uppercase tracking-widest mb-3 block", children: "Contacto" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-3xl sm:text-4xl font-display text-white mb-4", children: "Contacta con nosotros" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg text-superficie-400", children: "Resolvemos tus dudas en menos de 24 horas" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid md:grid-cols-5 gap-10", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "md:col-span-3", children: enviado ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center justify-center h-64 text-center cristal rounded-2xl p-8", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-12 h-12 bg-acento-500/10 border border-acento-500/20 rounded-full flex items-center justify-center mb-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { size: 20, className: "text-acento-400" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-lg font-semibold text-white mb-2", children: "Mensaje enviado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Nos pondremos en contacto contigo en breve." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setEnviado(false),
            className: "mt-5 text-sm text-acento-400 hover:text-acento-300 transition-colors",
            children: "Enviar otro mensaje"
          }
        )
      ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarEnvio, className: "space-y-5", noValidate: true, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid sm:grid-cols-2 gap-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "label",
              {
                htmlFor: "nombre",
                className: "block text-sm font-medium text-superficie-300 mb-1.5",
                children: "Nombre"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                id: "nombre",
                type: "text",
                required: true,
                value: campos.nombre,
                onChange: actualizarCampo("nombre"),
                placeholder: "Tu nombre",
                className: estiloInput
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "label",
              {
                htmlFor: "email",
                className: "block text-sm font-medium text-superficie-300 mb-1.5",
                children: "Email"
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "input",
              {
                id: "email",
                type: "email",
                required: true,
                value: campos.email,
                onChange: actualizarCampo("email"),
                placeholder: "tu@empresa.com",
                className: estiloInput
              }
            )
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "label",
            {
              htmlFor: "empresa",
              className: "block text-sm font-medium text-superficie-300 mb-1.5",
              children: "Empresa"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              id: "empresa",
              type: "text",
              value: campos.empresa,
              onChange: actualizarCampo("empresa"),
              placeholder: "Nombre de tu empresa o asesoría",
              className: estiloInput
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "label",
            {
              htmlFor: "mensaje",
              className: "block text-sm font-medium text-superficie-300 mb-1.5",
              children: "Mensaje"
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "textarea",
            {
              id: "mensaje",
              required: true,
              rows: 5,
              value: campos.mensaje,
              onChange: actualizarCampo("mensaje"),
              placeholder: "Cuéntanos en qué podemos ayudarte...",
              className: `${estiloInput} resize-none`
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            type: "submit",
            disabled: enviando,
            className: "flex items-center gap-2 px-6 py-3 text-sm font-semibold text-superficie-950 bg-acento-500 rounded-xl hover:bg-acento-400 disabled:opacity-60 disabled:cursor-not-allowed transition-all",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Send, { size: 15 }),
              enviando ? "Enviando..." : "Enviar mensaje"
            ]
          }
        )
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "md:col-span-2 space-y-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl p-6", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-sm font-semibold text-white mb-5", children: "Información de contacto" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-9 h-9 shrink-0 bg-acento-500/10 border border-acento-500/20 rounded-lg flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Mail, { size: 16, className: "text-acento-400" }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-semibold text-superficie-500 uppercase tracking-wide mb-0.5", children: "Email" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "a",
                  {
                    href: "mailto:hola@certigestor.com",
                    className: "text-sm text-superficie-200 hover:text-acento-400 transition-colors",
                    children: "hola@certigestor.com"
                  }
                )
              ] })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-9 h-9 shrink-0 bg-acento-500/10 border border-acento-500/20 rounded-lg flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Phone, { size: 16, className: "text-acento-400" }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-semibold text-superficie-500 uppercase tracking-wide mb-0.5", children: "Teléfono" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx(
                  "a",
                  {
                    href: "tel:+34900000000",
                    className: "text-sm text-superficie-200 hover:text-acento-400 transition-colors",
                    children: "+34 900 000 000"
                  }
                )
              ] })
            ] })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl p-6 bg-acento-500/5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 mb-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { size: 14, className: "text-acento-400" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-semibold text-white", children: "Horario de atención" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Lunes a viernes, de 9:00 a 18:00 (hora peninsular)" })
        ] })
      ] })
    ] })
  ] }) });
}
export {
  PaginaContacto
};
