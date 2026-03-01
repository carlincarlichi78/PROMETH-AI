import { c as createLucideIcon, r as reactExports, g as ErrorApiCliente, j as jsxRuntimeExports, m as Search, P as Plus, a as Shield, X, a0 as esquemaCrearUsuario } from "./index-DMbE3NR1.js";
import { f as formatearFecha } from "./index-BvWBIJCO.js";
import { l as listarUsuariosApi, a as actualizarUsuarioApi, d as desactivarUsuarioApi, c as crearUsuarioApi } from "./usuariosServicio-jACWWnfy.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { E as EllipsisVertical } from "./ellipsis-vertical-D4mt2YF7.js";
import { U as User } from "./user-Cs3upA-3.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const UserPlus = createLucideIcon("UserPlus", [
  ["path", { d: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2", key: "1yyitq" }],
  ["circle", { cx: "9", cy: "7", r: "4", key: "nufk8" }],
  ["line", { x1: "19", x2: "19", y1: "8", y2: "14", key: "1bvyxn" }],
  ["line", { x1: "22", x2: "16", y1: "11", y2: "11", key: "1shjgl" }]
]);
const TH = "text-left px-5 py-3.5 text-xs font-semibold text-superficie-500 uppercase tracking-wide";
function BadgeRol({ rol }) {
  const clases = {
    superadmin: "bg-red-500/15 text-red-400 border-red-500/20",
    admin: "bg-acento-500/15 text-acento-400 border-acento-500/20",
    asesor: "bg-superficie-700/60 text-superficie-400 border-white/[0.06]"
  };
  const etiquetas = {
    superadmin: "Superadmin",
    admin: "Admin",
    asesor: "Asesor"
  };
  const clase = clases[rol] ?? clases.asesor;
  const esAdmin = rol === "admin" || rol === "superadmin";
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${clase}`, children: [
    esAdmin ? /* @__PURE__ */ jsxRuntimeExports.jsx(Shield, { className: "w-3 h-3" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(User, { className: "w-3 h-3" }),
    etiquetas[rol] ?? rol
  ] });
}
function BadgeEstado({ activo }) {
  const clase = activo ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20";
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${clase}`, children: activo ? "Activo" : "Inactivo" });
}
function PaginaUsuarios() {
  const [usuarios, setUsuarios] = reactExports.useState([]);
  const [total, setTotal] = reactExports.useState(0);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [menuAbierto, setMenuAbierto] = reactExports.useState(null);
  const [modalCrear, setModalCrear] = reactExports.useState(false);
  const [confirmDesactivar, setConfirmDesactivar] = reactExports.useState(null);
  const cargarUsuarios = reactExports.useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const resultado = await listarUsuariosApi({
        busqueda: busqueda || void 0,
        limite: 50
      });
      setUsuarios(resultado.usuarios);
      setTotal(resultado.meta.total);
    } catch (err) {
      setError(err instanceof ErrorApiCliente ? err.message : "Error al cargar usuarios");
    } finally {
      setCargando(false);
    }
  }, [busqueda]);
  reactExports.useEffect(() => {
    const timer = setTimeout(cargarUsuarios, 300);
    return () => clearTimeout(timer);
  }, [cargarUsuarios]);
  const manejarCambiarRol = async (usuario) => {
    setMenuAbierto(null);
    try {
      await actualizarUsuarioApi(usuario.id, { rol: usuario.rol === "admin" ? "asesor" : "admin" });
      await cargarUsuarios();
    } catch (err) {
      if (err instanceof ErrorApiCliente) setError(err.message);
    }
  };
  const manejarDesactivar = async (id) => {
    setConfirmDesactivar(null);
    setMenuAbierto(null);
    try {
      await desactivarUsuarioApi(id);
      await cargarUsuarios();
    } catch (err) {
      if (err instanceof ErrorApiCliente) setError(err.message);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center gap-4 mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-shrink-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white whitespace-nowrap", children: "Usuarios" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-0.5", children: "Gestión de asesores y usuarios de tu organización" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-1 items-center gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1 max-w-md", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-superficie-500" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: busqueda,
              onChange: (e) => setBusqueda(e.target.value),
              placeholder: "Buscar por nombre o email...",
              className: "w-full pl-9 pr-4 py-2 text-sm text-superficie-100 border border-white/[0.06] rounded-lg outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 bg-superficie-800/60 placeholder:text-superficie-600"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-superficie-500 whitespace-nowrap", children: [
          total,
          " usuarios"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalCrear(true),
          className: "flex items-center gap-2 px-4 py-2 bg-acento-500 hover:bg-acento-400\n            text-superficie-950 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(UserPlus, { className: "w-4 h-4" }),
            "Agregar usuario"
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400 flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: error }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: cargarUsuarios, className: "ml-3 text-xs font-medium text-red-300 hover:text-white underline", children: "Reintentar" })
    ] }),
    cargando && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-center py-12", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-6 h-6 text-acento-400 animate-spin" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-sm text-superficie-400", children: "Cargando usuarios..." })
    ] }),
    !cargando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "cristal rounded-xl overflow-hidden", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-white/[0.06] bg-superficie-800/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: TH, children: "Nombre" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: TH, children: "Email" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: TH, children: "Rol" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: TH, children: "Estado" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: TH, children: "Fecha" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "px-5 py-3.5" })
      ] }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-white/[0.04]", children: usuarios.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { colSpan: 6, className: "px-5 py-12 text-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-500 text-sm mb-3", children: "No hay usuarios" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setModalCrear(true),
            className: "inline-flex items-center gap-1.5 text-sm text-acento-400 hover:text-acento-300 transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
              "Agregar el primer usuario"
            ]
          }
        )
      ] }) }) : usuarios.map((u) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-white/[0.02] transition-colors", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center w-8 h-8 rounded-full bg-acento-500/15 text-acento-400 text-sm font-semibold shrink-0", children: u.nombre.charAt(0).toUpperCase() }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium text-superficie-100", children: u.nombre })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-400", children: u.email }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeRol, { rol: u.rol }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx(BadgeEstado, { activo: u.activo }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4 text-superficie-300", children: formatearFecha(u.creadoEn) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-5 py-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex justify-end", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setMenuAbierto(menuAbierto === u.id ? null : u.id),
              className: "p-1.5 text-superficie-500 hover:text-superficie-200 hover:bg-white/[0.05] rounded-lg transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(EllipsisVertical, { className: "w-4 h-4" })
            }
          ),
          menuAbierto === u.id && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "absolute right-0 top-full mt-1 w-44 cristal rounded-lg shadow-xl shadow-black/40 z-10 py-1", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                onClick: () => manejarCambiarRol(u),
                className: "w-full text-left px-3 py-2 text-sm text-superficie-300 hover:bg-white/[0.05] hover:text-white",
                children: [
                  "Cambiar a ",
                  u.rol === "admin" ? "asesor" : "admin"
                ]
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => {
                  setMenuAbierto(null);
                  setConfirmDesactivar(u.id);
                },
                className: "w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/5",
                children: "Desactivar"
              }
            )
          ] })
        ] }) })
      ] }, u.id)) })
    ] }) }) }),
    modalCrear && /* @__PURE__ */ jsxRuntimeExports.jsx(
      ModalCrearUsuario,
      {
        onCerrar: () => setModalCrear(false),
        onCreado: () => {
          setModalCrear(false);
          cargarUsuarios();
        }
      }
    ),
    confirmDesactivar && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-sm mx-4 p-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-lg font-semibold text-white mb-2", children: "Desactivar usuario" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mb-5", children: "El usuario no podra acceder al sistema. Puedes reactivarlo despues." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex justify-end gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setConfirmDesactivar(null),
            className: "px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.05] transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => manejarDesactivar(confirmDesactivar),
            className: "px-4 py-2 text-sm font-semibold text-white bg-red-500 hover:bg-red-400 rounded-lg transition-colors",
            children: "Desactivar"
          }
        )
      ] })
    ] }) })
  ] });
}
const FORM_INIT = { nombre: "", email: "", password: "", rol: "asesor" };
const claseInput = (err) => `w-full px-3 py-2 rounded-lg border text-sm text-superficie-100 outline-none transition-colors
  focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 placeholder:text-superficie-600
  ${err ? "border-red-500/50 bg-red-500/5" : "border-white/[0.06] bg-superficie-800/60 hover:border-white/10"}`;
function ModalCrearUsuario({ onCerrar, onCreado }) {
  const [form, setForm] = reactExports.useState(FORM_INIT);
  const [errores, setErrores] = reactExports.useState({});
  const [errorGral, setErrorGral] = reactExports.useState(null);
  const [creando, setCreando] = reactExports.useState(false);
  const set = (campo, valor) => {
    setForm((p) => ({ ...p, [campo]: valor }));
    setErrores((p) => ({ ...p, [campo]: "" }));
    setErrorGral(null);
  };
  const manejarSubmit = async (e) => {
    e.preventDefault();
    const datos = { nombre: form.nombre, email: form.email, password: form.password, rol: form.rol };
    const res = esquemaCrearUsuario.safeParse(datos);
    if (!res.success) {
      const errs = {};
      res.error.errors.forEach((err) => {
        errs[err.path[0]] = err.message;
      });
      setErrores(errs);
      return;
    }
    setCreando(true);
    setErrorGral(null);
    try {
      await crearUsuarioApi(res.data);
      onCreado();
    } catch (err) {
      setErrorGral(err instanceof ErrorApiCliente ? err.message : "Error al crear usuario");
    } finally {
      setCreando(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal rounded-2xl shadow-2xl shadow-black/40 w-full max-w-lg mx-4 p-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Nuevo Usuario" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onCerrar, className: "p-1 text-superficie-400 hover:text-white rounded-lg hover:bg-white/[0.05]", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
    ] }),
    errorGral && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400", children: errorGral }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("form", { onSubmit: manejarSubmit, className: "space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(Campo, { etiqueta: "Nombre *", valor: form.nombre, onChange: (v) => set("nombre", v), placeholder: "Juan Perez", error: errores.nombre }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Campo, { etiqueta: "Email *", valor: form.email, onChange: (v) => set("email", v), placeholder: "juan@empresa.com", tipo: "email", error: errores.email }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Campo, { etiqueta: "Contrasena *", valor: form.password, onChange: (v) => set("password", v), placeholder: "Minimo 8 caracteres", tipo: "password", error: errores.password }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: "Rol" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "select",
          {
            value: form.rol,
            onChange: (e) => set("rol", e.target.value),
            className: "w-full px-3 py-2 rounded-lg border border-white/[0.06] bg-superficie-800/60 text-sm text-superficie-100 outline-none\n                focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40 cursor-pointer",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "asesor", className: "bg-superficie-800", children: "Asesor" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "admin", className: "bg-superficie-800", children: "Administrador" })
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
            className: "px-4 py-2 text-sm font-medium text-superficie-300 border border-white/[0.06] rounded-lg hover:bg-white/[0.05] transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            type: "submit",
            disabled: creando,
            className: "px-4 py-2 text-sm font-semibold text-superficie-950 bg-acento-500 hover:bg-acento-400 disabled:opacity-50 rounded-lg transition-colors",
            children: creando ? "Creando..." : "Crear usuario"
          }
        )
      ] })
    ] })
  ] }) });
}
function Campo({ etiqueta, valor, onChange, placeholder, error, tipo = "text" }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-superficie-300 mb-1", children: etiqueta }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("input", { type: tipo, value: valor, onChange: (e) => onChange(e.target.value), placeholder, className: claseInput(!!error) }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-xs text-red-400", children: error })
  ] });
}
export {
  PaginaUsuarios
};
