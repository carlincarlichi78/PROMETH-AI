import { ai as useParams, u as useNavigate, aj as usePortalStore, r as reactExports, j as jsxRuntimeExports } from "./index-DMbE3NR1.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
function resolverBaseUrl() {
  if (window.electronAPI?.isDesktop) return "https://www.carloscanetegomez.dev/certigestor/api";
  return "http://localhost:3000/api";
}
function PaginaEntradaPortal() {
  const { token } = useParams();
  const navigate = useNavigate();
  const { iniciarPortal } = usePortalStore();
  const [error, setError] = reactExports.useState(false);
  reactExports.useEffect(() => {
    if (!token) {
      navigate("/portal/expirado", { replace: true });
      return;
    }
    const validar = async () => {
      try {
        const baseUrl = resolverBaseUrl();
        const respuesta = await fetch(`${baseUrl}/portal/validar/${token}`);
        if (!respuesta.ok) {
          navigate("/portal/expirado", { replace: true });
          return;
        }
        const json = await respuesta.json();
        if (!json.exito || !json.datos) {
          navigate("/portal/expirado", { replace: true });
          return;
        }
        const datos = json.datos;
        iniciarPortal({
          token: datos.token,
          nombreCliente: datos.nombreCliente,
          dniCif: datos.dniCif,
          nombreOrganizacion: datos.nombreOrganizacion,
          logoOrganizacion: datos.logoOrganizacion,
          colorPrimario: datos.colorPrimario
        });
        navigate("/portal/app", { replace: true });
      } catch {
        setError(true);
        navigate("/portal/expirado", { replace: true });
      }
    };
    validar();
  }, [token, navigate, iniciarPortal]);
  if (error) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "min-h-screen bg-superficie-950 flex items-center justify-center", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-8 h-8 text-acento-400 animate-spin" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Validando acceso al portal..." })
  ] }) });
}
export {
  PaginaEntradaPortal
};
