import { r as reactExports, ak as useSuperadminStore, j as jsxRuntimeExports, P as Plus, m as Search, R as Building2, al as UserCheck, X } from "./index-DMbE3NR1.js";
import { l as listarOrganizacionesApi, i as impersonarOrgApi, a as actualizarOrganizacionApi, c as crearOrganizacionApi } from "./superadminServicio-RgYMJlVk.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { P as Pencil } from "./pencil-BuwvL_tU.js";
import { C as ChevronLeft } from "./chevron-left-CYQ_O-IZ.js";
import { C as ChevronRight } from "./chevron-right-C62o1fXe.js";
function PaginaSuperadminOrganizaciones() {
  const [organizaciones, setOrganizaciones] = reactExports.useState([]);
  const [cargando, setCargando] = reactExports.useState(true);
  const [error, setError] = reactExports.useState(null);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [filtroPlan, setFiltroPlan] = reactExports.useState("");
  const [pagina, setPagina] = reactExports.useState(1);
  const [totalPaginas, setTotalPaginas] = reactExports.useState(1);
  const [modalEditar, setModalEditar] = reactExports.useState(false);
  const [orgEditando, setOrgEditando] = reactExports.useState(null);
  const [editNombre, setEditNombre] = reactExports.useState("");
  const [editPlan, setEditPlan] = reactExports.useState("basico");
  const [editMaxAsesores, setEditMaxAsesores] = reactExports.useState(3);
  const [guardando, setGuardando] = reactExports.useState(false);
  const [modalCrear, setModalCrear] = reactExports.useState(false);
  const [crearNombre, setCrearNombre] = reactExports.useState("");
  const [crearCif, setCrearCif] = reactExports.useState("");
  const [crearPlan, setCrearPlan] = reactExports.useState("basico");
  const [crearEmailAdmin, setCrearEmailAdmin] = reactExports.useState("");
  const [crearNombreAdmin, setCrearNombreAdmin] = reactExports.useState("");
  const [crearPasswordAdmin, setCrearPasswordAdmin] = reactExports.useState("");
  const [creando, setCreando] = reactExports.useState(false);
  const { iniciarImpersonacion } = useSuperadminStore();
  const cargar = reactExports.useCallback(async () => {
    try {
      setCargando(true);
      setError(null);
      const params = {
        pagina: String(pagina),
        limite: "20"
      };
      if (busqueda.trim()) params.busqueda = busqueda.trim();
      if (filtroPlan) params.plan = filtroPlan;
      const resp = await listarOrganizacionesApi(params);
      setOrganizaciones(resp.organizaciones);
      setTotalPaginas(resp.meta.totalPaginas || 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error cargando organizaciones");
    } finally {
      setCargando(false);
    }
  }, [pagina, busqueda, filtroPlan]);
  reactExports.useEffect(() => {
    cargar();
  }, [cargar]);
  const abrirEditar = (org) => {
    setOrgEditando(org);
    setEditNombre(org.nombre);
    setEditPlan(org.plan);
    setEditMaxAsesores(org.maxAsesores);
    setModalEditar(true);
  };
  const guardarEdicion = async () => {
    if (!orgEditando) return;
    try {
      setGuardando(true);
      await actualizarOrganizacionApi(orgEditando.id, {
        nombre: editNombre,
        plan: editPlan,
        maxAsesores: editMaxAsesores
      });
      setModalEditar(false);
      setOrgEditando(null);
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error actualizando organizacion");
    } finally {
      setGuardando(false);
    }
  };
  const crearOrganizacion = async () => {
    if (!crearNombre.trim() || !crearEmailAdmin.trim() || !crearNombreAdmin.trim() || !crearPasswordAdmin.trim()) return;
    try {
      setCreando(true);
      await crearOrganizacionApi({
        nombre: crearNombre.trim(),
        cif: crearCif.trim() || null,
        plan: crearPlan,
        emailAdmin: crearEmailAdmin.trim(),
        nombreAdmin: crearNombreAdmin.trim(),
        passwordAdmin: crearPasswordAdmin
      });
      setModalCrear(false);
      setCrearNombre("");
      setCrearCif("");
      setCrearPlan("basico");
      setCrearEmailAdmin("");
      setCrearNombreAdmin("");
      setCrearPasswordAdmin("");
      await cargar();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error creando organizacion");
    } finally {
      setCreando(false);
    }
  };
  const impersonar = async (org) => {
    try {
      const tokenActual = localStorage.getItem("accessToken");
      if (!tokenActual) return;
      const resp = await impersonarOrgApi(org.id);
      if (resp.exito && resp.datos) {
        iniciarImpersonacion(tokenActual, org.id, org.nombre, resp.datos.accessToken);
        window.location.href = "/certigestor/app";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error impersonando organizacion");
    }
  };
  const badgePlan = (plan) => {
    const colores = {
      basico: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      profesional: "bg-purple-500/10 text-purple-400 border-purple-500/20",
      plus: "bg-amber-500/10 text-amber-400 border-amber-500/20"
    };
    return colores[plan] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20";
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-gray-100", children: "Organizaciones" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-gray-400 mt-1", children: "Gestion global de organizaciones" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setModalCrear(true),
          className: "inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-acento-500 text-white font-medium hover:bg-acento-600 transition-colors",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Plus, { className: "w-4 h-4" }),
            "Nueva organizacion"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "input",
          {
            type: "text",
            placeholder: "Buscar por nombre o CIF...",
            value: busqueda,
            onChange: (e) => {
              setBusqueda(e.target.value);
              setPagina(1);
            },
            className: "w-full pl-10 pr-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-acento-500"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "select",
        {
          value: filtroPlan,
          onChange: (e) => {
            setFiltroPlan(e.target.value);
            setPagina(1);
          },
          className: "px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "", children: "Todos los planes" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "basico", children: "Basico" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "profesional", children: "Profesional" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "plus", children: "Plus" })
          ]
        }
      )
    ] }),
    error && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400", children: error }),
    cargando ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center justify-center h-48", children: /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-8 h-8 text-acento-400 animate-spin" }) }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-gray-800 border border-gray-700 overflow-hidden", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-x-auto", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("table", { className: "w-full", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("thead", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "border-b border-gray-700", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Nombre" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "CIF" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Plan" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Usuarios" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-center px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Certificados" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Creada" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("th", { className: "text-right px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider", children: "Acciones" })
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("tbody", { className: "divide-y divide-gray-700/50", children: organizaciones.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("tr", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs("td", { colSpan: 7, className: "px-4 py-12 text-center text-gray-500", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Building2, { className: "w-10 h-10 mx-auto mb-2 opacity-50" }),
          "No se encontraron organizaciones"
        ] }) }) : organizaciones.map((org) => /* @__PURE__ */ jsxRuntimeExports.jsxs("tr", { className: "hover:bg-gray-700/30 transition-colors", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-100 font-medium", children: org.nombre }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-400", children: org.cif ?? "-" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3", children: /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex px-2.5 py-0.5 rounded-md text-xs font-medium border capitalize ${badgePlan(org.plan)}`, children: org.plan }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-300 text-center", children: org.totalUsuarios }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-300 text-center", children: org.totalCertificados }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-sm text-gray-400", children: new Date(org.creadoEn).toLocaleDateString("es-ES") }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("td", { className: "px-4 py-3 text-right", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-1", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => impersonar(org),
                title: "Impersonar organizacion",
                className: "p-2 rounded-lg text-gray-400 hover:text-amber-400 hover:bg-amber-500/10 transition-colors",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(UserCheck, { className: "w-4 h-4" })
              }
            ),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: () => abrirEditar(org),
                title: "Editar organizacion",
                className: "p-2 rounded-lg text-gray-400 hover:text-blue-400 hover:bg-blue-500/10 transition-colors",
                children: /* @__PURE__ */ jsxRuntimeExports.jsx(Pencil, { className: "w-4 h-4" })
              }
            )
          ] }) })
        ] }, org.id)) })
      ] }) }),
      totalPaginas > 1 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between px-4 py-3 border-t border-gray-700", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm text-gray-400", children: [
          "Pagina ",
          pagina,
          " de ",
          totalPaginas
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.max(1, p - 1)),
              disabled: pagina <= 1,
              className: "p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronLeft, { className: "w-4 h-4" })
            }
          ),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "button",
            {
              onClick: () => setPagina((p) => Math.min(totalPaginas, p + 1)),
              disabled: pagina >= totalPaginas,
              className: "p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors",
              children: /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "w-4 h-4" })
            }
          )
        ] })
      ] })
    ] }),
    modalEditar && orgEditando && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-gray-800 border border-gray-700 rounded-xl w-full max-w-md p-6 shadow-xl", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-gray-100", children: "Editar organizacion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setModalEditar(false), className: "p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Nombre" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: editNombre,
              onChange: (e) => setEditNombre(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Plan" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: editPlan,
              onChange: (e) => setEditPlan(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "basico", children: "Basico" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "profesional", children: "Profesional" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "plus", children: "Plus" })
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Max. asesores" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "number",
              min: 1,
              value: editMaxAsesores,
              onChange: (e) => setEditMaxAsesores(Number(e.target.value)),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-3 mt-6", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setModalEditar(false),
            className: "px-4 py-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: guardarEdicion,
            disabled: guardando,
            className: "px-4 py-2 rounded-lg bg-acento-500 text-white font-medium hover:bg-acento-600 disabled:opacity-50 transition-colors",
            children: guardando ? "Guardando..." : "Guardar"
          }
        )
      ] })
    ] }) }),
    modalCrear && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "bg-gray-800 border border-gray-700 rounded-xl w-full max-w-md p-6 shadow-xl max-h-[90vh] overflow-y-auto", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-gray-100", children: "Nueva organizacion" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setModalCrear(false), className: "p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "w-5 h-5" }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Nombre organizacion *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: crearNombre,
              onChange: (e) => setCrearNombre(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "CIF" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: crearCif,
              onChange: (e) => setCrearCif(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Plan" }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "select",
            {
              value: crearPlan,
              onChange: (e) => setCrearPlan(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "basico", children: "Basico" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "profesional", children: "Profesional" }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("option", { value: "plus", children: "Plus" })
              ]
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("hr", { className: "border-gray-700" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-gray-500 uppercase tracking-wider font-semibold", children: "Administrador inicial" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Email admin *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "email",
              value: crearEmailAdmin,
              onChange: (e) => setCrearEmailAdmin(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Nombre admin *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              value: crearNombreAdmin,
              onChange: (e) => setCrearNombreAdmin(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("label", { className: "block text-sm font-medium text-gray-300 mb-1", children: "Password admin *" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "password",
              value: crearPasswordAdmin,
              onChange: (e) => setCrearPasswordAdmin(e.target.value),
              className: "w-full px-3 py-2.5 rounded-lg bg-gray-900 border border-gray-700 text-gray-100 focus:outline-none focus:border-acento-500"
            }
          )
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-end gap-3 mt-6", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: () => setModalCrear(false),
            className: "px-4 py-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors",
            children: "Cancelar"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          "button",
          {
            onClick: crearOrganizacion,
            disabled: creando || !crearNombre.trim() || !crearEmailAdmin.trim() || !crearNombreAdmin.trim() || !crearPasswordAdmin.trim(),
            className: "px-4 py-2 rounded-lg bg-acento-500 text-white font-medium hover:bg-acento-600 disabled:opacity-50 transition-colors",
            children: creando ? "Creando..." : "Crear organizacion"
          }
        )
      ] })
    ] }) })
  ] });
}
export {
  PaginaSuperadminOrganizaciones
};
