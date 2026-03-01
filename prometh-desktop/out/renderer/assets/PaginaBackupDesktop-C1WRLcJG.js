import { r as reactExports, y as Timer, ao as BellRing, au as Cog, G as Globe, q as FileText, D as Download, j as jsxRuntimeExports, av as HardDriveDownload, L as Lock, o as Upload } from "./index-DMbE3NR1.js";
import { C as CircleCheck } from "./circle-check-BxiPcB-x.js";
import { L as LoaderCircle } from "./loader-circle-C3xzc68t.js";
import { C as CircleAlert } from "./circle-alert-Br5xelJa.js";
const SECCIONES = [
  { id: "scheduler", etiqueta: "Tareas programadas", descripcion: "Scheduler local y frecuencias", icono: Timer },
  { id: "tray_config", etiqueta: "Config alertas", descripcion: "Preferencias de notificaciones desktop", icono: BellRing },
  { id: "workflows", etiqueta: "Workflows", descripcion: "Workflows personalizados y config SMTP", icono: Cog },
  { id: "config_portales", etiqueta: "Config portales", descripcion: "Portales de notificaciones activos", icono: Globe },
  { id: "config_docs", etiqueta: "Config documentos", descripcion: "Documentos activos por certificado", icono: FileText },
  { id: "historial_docs", etiqueta: "Historial descargas", descripcion: "Registro de descargas documentales", icono: Download }
];
function PaginaBackupDesktop() {
  const [seccionesSeleccionadas, setSeccionesSeleccionadas] = reactExports.useState(
    SECCIONES.map((s) => s.id)
  );
  const [passwordExportar, setPasswordExportar] = reactExports.useState("");
  const [exportando, setExportando] = reactExports.useState(false);
  const [resultadoExportar, setResultadoExportar] = reactExports.useState(null);
  const [passwordImportar, setPasswordImportar] = reactExports.useState("");
  const [importando, setImportando] = reactExports.useState(false);
  const [resultadoImportar, setResultadoImportar] = reactExports.useState(null);
  const [previsualizando, setPrevisualizando] = reactExports.useState(false);
  const [preview, setPreview] = reactExports.useState(null);
  const toggleSeccion = (id) => {
    setSeccionesSeleccionadas(
      (prev) => prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };
  const seleccionarTodas = () => {
    if (seccionesSeleccionadas.length === SECCIONES.length) {
      setSeccionesSeleccionadas([]);
    } else {
      setSeccionesSeleccionadas(SECCIONES.map((s) => s.id));
    }
  };
  const manejarExportar = async () => {
    if (seccionesSeleccionadas.length === 0 || passwordExportar.length < 6) return;
    setExportando(true);
    setResultadoExportar(null);
    try {
      const res = await window.electronAPI.backup.exportar({
        secciones: seccionesSeleccionadas,
        password: passwordExportar
      });
      if (res.exito) {
        setResultadoExportar({ exito: true, mensaje: `Backup guardado en: ${res.ruta}` });
        setPasswordExportar("");
      } else {
        setResultadoExportar({ exito: false, mensaje: res.error ?? "Error al exportar" });
      }
    } catch {
      setResultadoExportar({ exito: false, mensaje: "Error inesperado al exportar" });
    }
    setExportando(false);
  };
  const manejarPrevisualizar = async () => {
    if (passwordImportar.length < 6) return;
    setPrevisualizando(true);
    setPreview(null);
    setResultadoImportar(null);
    try {
      const res = await window.electronAPI.backup.previsualizar({ password: passwordImportar });
      if (res.exito && res.secciones) {
        setPreview({ secciones: res.secciones, fecha: res.fecha ?? "" });
      } else {
        setResultadoImportar({ exito: false, mensaje: res.error ?? "No se pudo leer el backup" });
      }
    } catch {
      setResultadoImportar({ exito: false, mensaje: "Error inesperado al leer backup" });
    }
    setPrevisualizando(false);
  };
  const manejarImportar = async () => {
    if (passwordImportar.length < 6) return;
    setImportando(true);
    setResultadoImportar(null);
    try {
      const res = await window.electronAPI.backup.importar({ password: passwordImportar });
      if (res.exito) {
        setResultadoImportar({
          exito: true,
          mensaje: `Importadas ${res.seccionesImportadas.length} secciones: ${res.seccionesImportadas.join(", ")}`
        });
        setPasswordImportar("");
        setPreview(null);
      } else {
        setResultadoImportar({ exito: false, mensaje: res.error ?? "Error al importar" });
      }
    } catch {
      setResultadoImportar({ exito: false, mensaje: "Error inesperado al importar" });
    }
    setImportando(false);
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-bold text-white", children: "Backup y restauración" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-superficie-400 mt-1", children: "Exporta tu configuración desktop a un archivo cifrado para migrar entre PCs" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 lg:grid-cols-2 gap-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl border border-white/[0.06] bg-superficie-900/50 p-6 space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-2 rounded-lg bg-acento-500/10", children: /* @__PURE__ */ jsxRuntimeExports.jsx(HardDriveDownload, { className: "w-5 h-5 text-acento-400" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Exportar" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Guardar configuración en archivo cifrado" })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-superficie-300", children: "Secciones a exportar" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx(
              "button",
              {
                onClick: seleccionarTodas,
                className: "text-xs text-acento-400 hover:text-acento-300",
                children: seccionesSeleccionadas.length === SECCIONES.length ? "Deseleccionar todas" : "Seleccionar todas"
              }
            )
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-1", children: SECCIONES.map((seccion) => {
            const Icono = seccion.icono;
            const seleccionada = seccionesSeleccionadas.includes(seccion.id);
            return /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                onClick: () => toggleSeccion(seccion.id),
                className: `w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${seleccionada ? "bg-acento-500/10 border border-acento-500/20 text-white" : "border border-white/[0.06] text-superficie-400 hover:bg-white/[0.03]"}`,
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(Icono, { className: "w-4 h-4 flex-shrink-0" }),
                  /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 text-left", children: [
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-medium", children: seccion.etiqueta }),
                    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "ml-2 text-xs text-superficie-500", children: seccion.descripcion })
                  ] }),
                  /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `w-4 h-4 rounded border flex items-center justify-center ${seleccionada ? "bg-acento-500 border-acento-500" : "border-superficie-600"}`, children: seleccionada && /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheck, { className: "w-3 h-3 text-white" }) })
                ]
              },
              seccion.id
            );
          }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "text-sm font-medium text-superficie-300 flex items-center gap-1.5", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Lock, { className: "w-3.5 h-3.5" }),
            "Contraseña de cifrado"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "password",
              value: passwordExportar,
              onChange: (e) => setPasswordExportar(e.target.value),
              placeholder: "Mínimo 6 caracteres",
              className: "w-full px-3 py-2 rounded-lg bg-superficie-800 border border-white/[0.06] text-white text-sm placeholder:text-superficie-600 focus:outline-none focus:border-acento-500/40"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarExportar,
            disabled: exportando || seccionesSeleccionadas.length === 0 || passwordExportar.length < 6,
            className: "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-acento-500/20 text-acento-300 font-medium text-sm hover:bg-acento-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors",
            children: [
              exportando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(HardDriveDownload, { className: "w-4 h-4" }),
              exportando ? "Exportando..." : "Exportar backup"
            ]
          }
        ),
        resultadoExportar && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-start gap-2 px-3 py-2 rounded-lg text-sm ${resultadoExportar.exito ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`, children: [
          resultadoExportar.exito ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheck, { className: "w-4 h-4 mt-0.5 flex-shrink-0" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 mt-0.5 flex-shrink-0" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: resultadoExportar.mensaje })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl border border-white/[0.06] bg-superficie-900/50 p-6 space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "p-2 rounded-lg bg-amber-500/10", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-5 h-5 text-amber-400" }) }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-lg font-semibold text-white", children: "Importar" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400", children: "Restaurar configuración desde archivo backup" })
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("label", { className: "text-sm font-medium text-superficie-300 flex items-center gap-1.5", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Lock, { className: "w-3.5 h-3.5" }),
            "Contraseña del backup"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "password",
              value: passwordImportar,
              onChange: (e) => {
                setPasswordImportar(e.target.value);
                setPreview(null);
                setResultadoImportar(null);
              },
              placeholder: "Introduce la contraseña usada al exportar",
              className: "w-full px-3 py-2 rounded-lg bg-superficie-800 border border-white/[0.06] text-white text-sm placeholder:text-superficie-600 focus:outline-none focus:border-acento-500/40"
            }
          )
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarPrevisualizar,
            disabled: previsualizando || passwordImportar.length < 6,
            className: "w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-white/[0.06] text-superficie-300 font-medium text-sm hover:bg-white/[0.03] disabled:opacity-40 disabled:cursor-not-allowed transition-colors",
            children: [
              previsualizando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(FileText, { className: "w-4 h-4" }),
              previsualizando ? "Leyendo..." : "Seleccionar y previsualizar"
            ]
          }
        ),
        preview && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-lg border border-white/[0.06] bg-superficie-800/50 p-3 space-y-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between text-sm", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-superficie-400", children: "Fecha del backup:" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-white", children: new Date(preview.fecha).toLocaleString("es-ES") })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-sm text-superficie-400", children: "Secciones incluidas:" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: preview.secciones.map((seccion) => {
            const info = SECCIONES.find((s) => s.id === seccion);
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              "span",
              {
                className: "px-2 py-0.5 rounded-md bg-acento-500/10 text-acento-400 text-xs font-medium",
                children: info?.etiqueta ?? seccion
              },
              seccion
            );
          }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: manejarImportar,
            disabled: importando || passwordImportar.length < 6,
            className: "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-amber-500/20 text-amber-300 font-medium text-sm hover:bg-amber-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors",
            children: [
              importando ? /* @__PURE__ */ jsxRuntimeExports.jsx(LoaderCircle, { className: "w-4 h-4 animate-spin" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "w-4 h-4" }),
              importando ? "Importando..." : "Importar backup"
            ]
          }
        ),
        resultadoImportar && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: `flex items-start gap-2 px-3 py-2 rounded-lg text-sm ${resultadoImportar.exito ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`, children: [
          resultadoImportar.exito ? /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheck, { className: "w-4 h-4 mt-0.5 flex-shrink-0" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(CircleAlert, { className: "w-4 h-4 mt-0.5 flex-shrink-0" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: resultadoImportar.mensaje })
        ] })
      ] })
    ] })
  ] });
}
export {
  PaginaBackupDesktop
};
