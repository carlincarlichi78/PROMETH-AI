import { c as createLucideIcon, a as Shield, B as Bell, aa as PenLine, p as Brain, C as CalendarDays, e as SquareCheckBig, W as Workflow, F as FolderOpen, ag as Settings, r as reactExports, j as jsxRuntimeExports, m as Search, n as ChevronDown, ah as CircleHelp } from "./index-DMbE3NR1.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const ChevronUp = createLucideIcon("ChevronUp", [["path", { d: "m18 15-6-6-6 6", key: "153udz" }]]);
const categoriasAyuda = [
  {
    id: "certificados",
    nombre: "Certificados",
    icono: Shield,
    descripcion: "Gestiona tus certificados digitales y alertas de caducidad.",
    articulos: [
      {
        id: "cert-agregar",
        titulo: "Como agregar un certificado",
        contenido: 'Ve a la sección "Certificados" del panel y haz clic en "Nuevo certificado". Rellena el nombre, entidad emisora, fecha de emisión y fecha de caducidad. Opcionalmente añade notas internas y asígnale etiquetas para organizarlo. Haz clic en "Guardar" para que quede registrado y comience a monitorizarse.',
        etiquetas: ["crear", "agregar", "nuevo", "certificado"]
      },
      {
        id: "cert-importar",
        titulo: "Importar certificado P12 / PFX",
        contenido: 'En "Certificados", usa el botón "Importar P12/PFX" para subir directamente un fichero de certificado. Introduce la contraseña del fichero si está protegido: CertiGestor la cifra con AES-256-GCM y nunca la almacena en texto plano. Los datos del certificado (titular, caducidad, emisor) se extraen automáticamente del fichero. El fichero cifrado queda almacenado para poder usarlo en firmas digitales.',
        etiquetas: ["importar", "p12", "pfx", "fichero", "subir"]
      },
      {
        id: "cert-alertas",
        titulo: "Alertas de caducidad",
        contenido: 'CertiGestor genera automáticamente notificaciones de aviso cuando un certificado está próximo a caducar. El número de días de antelación se configura en Configuración → "Días de aviso previo a caducidad". Recibirás también avisos el mismo día de la caducidad y tras ella si el certificado no se renueva. Estas notificaciones aparecen en la sección "Notificaciones" y en el widget de la agenda.',
        etiquetas: ["alertas", "caducidad", "avisos", "días", "vencimiento"]
      },
      {
        id: "cert-buscar",
        titulo: "Buscar y filtrar certificados",
        contenido: "Usa el buscador en la parte superior del listado para localizar certificados por nombre o entidad emisora. Aplica el filtro por etiqueta para ver solo los certificados de una categoría concreta. El listado está paginado; puedes ajustar cuántos resultados se muestran por página. Los certificados caducados aparecen resaltados en rojo para identificarlos de un vistazo.",
        etiquetas: ["buscar", "filtrar", "etiquetas", "paginación", "listado"]
      },
      {
        id: "cert-eliminar",
        titulo: "Eliminar un certificado",
        contenido: 'Abre el detalle del certificado y selecciona "Eliminar". La eliminación es lógica (soft delete): el certificado desaparece del listado activo pero sus datos se conservan en auditoría. Las notificaciones asociadas quedan en el historial con el certificado referenciado como eliminado.',
        etiquetas: ["eliminar", "borrar", "soft delete"]
      }
    ]
  },
  {
    id: "notificaciones",
    nombre: "Notificaciones",
    icono: Bell,
    descripcion: "Recibe y gestiona avisos sobre tus certificados y expedientes.",
    articulos: [
      {
        id: "notif-que-son",
        titulo: "Qué son las notificaciones",
        contenido: "Las notificaciones son avisos generados automáticamente o de forma manual sobre eventos relevantes. Incluyen alertas de caducidad de certificados, recordatorios de expedientes y mensajes de organismos. Cada notificación tiene un estado (pendiente, en proceso, resuelta) y puede asignarse a un usuario del equipo. Desde el panel principal puedes ver un resumen de notificaciones pendientes y próximos vencimientos.",
        etiquetas: ["notificaciones", "avisos", "alertas"]
      },
      {
        id: "notif-estados",
        titulo: "Estados de una notificación",
        contenido: 'Una notificación pasa por los estados: Pendiente → En proceso → Resuelta. "Pendiente" significa que nadie ha actuado aún sobre ella. "En proceso" indica que un usuario la está tramitando. "Resuelta" cierra la notificación; puedes añadir notas de resolución antes de cerrarla. Todos los cambios de estado quedan registrados en el historial de la notificación.',
        etiquetas: ["estados", "pendiente", "en proceso", "resuelta", "estado"]
      },
      {
        id: "notif-triaje",
        titulo: "Triaje y urgencia",
        contenido: "El triaje permite clasificar notificaciones por urgencia (crítica, alta, media, baja) y categoría. Puedes asignar urgencia y categoría manualmente desde el detalle de la notificación. AEGIS IA puede auto-clasificar urgencia y categoría si tienes el plan Profesional o superior. El listado permite filtrar por nivel de urgencia para priorizar tu trabajo diario.",
        etiquetas: ["triaje", "urgencia", "crítica", "alta", "media", "baja", "categoría", "clasificar"]
      },
      {
        id: "notif-asignar",
        titulo: "Asignar notificaciones a un usuario",
        contenido: 'En el detalle de la notificación, usa el campo "Asignado a" para asignarla a cualquier miembro del equipo. Solo los administradores pueden reasignar notificaciones ya asignadas a otro usuario. El cambio de asignación queda registrado en el historial con la fecha y el usuario que realizó el cambio.',
        etiquetas: ["asignar", "usuario", "equipo", "responsable"]
      },
      {
        id: "notif-email",
        titulo: "Enviar notificación por email",
        contenido: "Desde el detalle de una notificación puedes reenviarla por email al destinatario correspondiente. El email se envía desde la dirección configurada en los ajustes de la organización. El envío queda registrado en el historial de la notificación con la fecha y hora exactas.",
        etiquetas: ["email", "correo", "enviar", "reenviar"]
      }
    ]
  },
  {
    id: "firmas",
    nombre: "Firma Digital",
    icono: PenLine,
    descripcion: "Firma documentos PDF con tus certificados digitales (PAdES).",
    articulos: [
      {
        id: "firma-como",
        titulo: "Como firmar un PDF",
        contenido: 'Ve a la sección "Firmas" y haz clic en "Firmar documento". Sube el PDF que quieres firmar y selecciona el certificado digital importado con el que deseas firmar. CertiGestor aplica la firma PAdES (PDF Advanced Electronic Signature) de forma automática. El documento firmado queda disponible en el listado de firmas para su descarga inmediata.',
        etiquetas: ["firmar", "pdf", "firma", "PAdES", "documento"]
      },
      {
        id: "firma-requisitos",
        titulo: "Requisitos previos para firmar",
        contenido: 'Para firmar necesitas tener al menos un certificado P12/PFX importado en la sección "Certificados". El certificado debe estar vigente (no caducado) en el momento de la firma. Solo los certificados importados con su fichero P12/PFX pueden usarse para firmar; los introducidos manualmente no contienen la clave privada necesaria.',
        etiquetas: ["requisitos", "p12", "pfx", "clave privada", "vigente"]
      },
      {
        id: "firma-descargar",
        titulo: "Descargar un documento firmado",
        contenido: 'En la sección "Firmas" aparece el historial de todos los documentos firmados. Haz clic en el botón de descarga de cualquier fila para obtener el PDF firmado. El fichero descargado contiene la firma digital embebida y puede verificarse con cualquier lector de PDF compatible con PAdES (Adobe Acrobat, Evince, etc.).',
        etiquetas: ["descargar", "descarga", "historial", "pdf firmado"]
      }
    ]
  },
  {
    id: "aegis",
    nombre: "AEGIS IA",
    icono: Brain,
    descripcion: "Analiza notificaciones con inteligencia artificial.",
    articulos: [
      {
        id: "aegis-que-es",
        titulo: "Qué es AEGIS",
        contenido: "AEGIS es el motor de inteligencia artificial de CertiGestor, basado en GPT-4o-mini de OpenAI. Analiza el contenido de las notificaciones para identificar fechas clave, acciones requeridas y riesgos. Disponible en los planes Profesional y superior; los usuarios del plan Básico ven el resumen de uso pero no pueden analizar. Cada mes se reinicia el contador de análisis según el límite de tu plan.",
        etiquetas: ["aegis", "ia", "inteligencia artificial", "gpt", "análisis"]
      },
      {
        id: "aegis-analizar",
        titulo: "Analizar una notificación con IA",
        contenido: 'Abre el detalle de cualquier notificación y haz clic en "Analizar con AEGIS". La IA procesará el contenido y devolverá un resumen, las acciones recomendadas y el nivel de urgencia sugerido. Puedes aplicar la clasificación sugerida (urgencia y categoría) directamente desde el panel de resultados. El análisis se registra en el historial de la notificación.',
        etiquetas: ["analizar", "análisis", "notificación", "ia", "resumen"]
      },
      {
        id: "aegis-limites",
        titulo: "Límites del plan",
        contenido: 'El número de análisis mensuales varía según el plan: Profesional incluye 50 análisis/mes, y el plan Enterprise incluye análisis ilimitados. Puedes consultar el uso actual en la sección "AEGIS" → panel de uso mensual. Al llegar al límite, el botón de análisis se desactiva hasta el inicio del próximo mes.',
        etiquetas: ["límites", "plan", "mensual", "uso", "cuota"]
      },
      {
        id: "aegis-autoclasificacion",
        titulo: "Auto-clasificación de urgencia y categoría",
        contenido: 'AEGIS puede sugerir automáticamente la urgencia (crítica/alta/media/baja) y la categoría de la notificación. Tras el análisis, aparece un botón "Aplicar clasificación" que actualiza los campos en un solo clic. Puedes revisar y modificar la clasificación sugerida antes de aplicarla. La auto-clasificación consume un análisis de tu cuota mensual.',
        etiquetas: ["auto-clasificación", "urgencia", "categoría", "aplicar", "sugerencia"]
      }
    ]
  },
  {
    id: "agenda",
    nombre: "Agenda",
    icono: CalendarDays,
    descripcion: "Visualiza vencimientos y gestiona recordatorios.",
    articulos: [
      {
        id: "agenda-calendario",
        titulo: "Calendario de eventos",
        contenido: 'La sección "Agenda" muestra un calendario mensual con todos los eventos relevantes. Los vencimientos de certificados aparecen automáticamente según la fecha de caducidad configurada. Los recordatorios manuales que hayas creado también aparecen en el calendario. Puedes navegar entre meses con las flechas y hacer clic en cualquier día para ver sus eventos.',
        etiquetas: ["calendario", "mensual", "eventos", "vencimientos", "agenda"]
      },
      {
        id: "agenda-recordatorio",
        titulo: "Crear un recordatorio manual",
        contenido: 'En la sección "Agenda", haz clic en "Nuevo recordatorio" (disponible en plan Profesional o superior). Introduce el título, la fecha, una descripción opcional y si debe repetirse. El recordatorio aparecerá en el calendario y en el widget de próximos eventos del dashboard. Puedes editar o eliminar cualquier recordatorio desde el listado lateral.',
        etiquetas: ["recordatorio", "crear", "manual", "título", "fecha"]
      },
      {
        id: "agenda-vencimientos",
        titulo: "Vencimientos automáticos de certificados",
        contenido: 'CertiGestor genera eventos de vencimiento automáticamente para cada certificado activo. Se crean eventos en la fecha de caducidad y tantos días antes como configures en "Días de aviso". Estos eventos no pueden editarse directamente; para modificarlos cambia la fecha del certificado o los días de aviso. Aparecen con un icono de escudo para distinguirlos de los recordatorios manuales.',
        etiquetas: ["vencimientos", "automático", "certificado", "caducidad", "escudo"]
      }
    ]
  },
  {
    id: "tareas",
    nombre: "Tareas",
    icono: SquareCheckBig,
    descripcion: "Organiza el trabajo de tu equipo con tareas y comentarios.",
    articulos: [
      {
        id: "tarea-crear",
        titulo: "Crear una tarea",
        contenido: 'Ve a "Tareas" y haz clic en "Nueva tarea". Introduce el título y opcionalmente una descripción, fecha límite, prioridad (baja/media/alta/urgente) y una referencia a un certificado o notificación relacionados. Puedes asignar la tarea a cualquier miembro del equipo en el momento de la creación. La tarea aparece en el listado con estado "Pendiente" hasta que alguien la inicie.',
        etiquetas: ["crear", "tarea", "nueva", "título", "descripción"]
      },
      {
        id: "tarea-estados",
        titulo: "Estados y prioridades",
        contenido: "Los estados posibles son: Pendiente → En curso → En revisión → Completada. Las prioridades van de Baja a Urgente y se muestran con colores diferenciados en el listado. Cambia el estado desde el detalle de la tarea o directamente desde el listado con el menú rápido. Las tareas completadas quedan en el historial y pueden filtrarse por estado.",
        etiquetas: ["estados", "prioridad", "pendiente", "en curso", "completada", "urgente"]
      },
      {
        id: "tarea-comentarios",
        titulo: "Comentarios en una tarea",
        contenido: 'Abre el detalle de una tarea y desplázate hasta la sección "Comentarios". Escribe tu comentario y haz clic en "Enviar". Los comentarios se ordenan cronológicamente y muestran el autor y la fecha. Son visibles para todos los miembros de la organización con acceso a esa tarea.',
        etiquetas: ["comentarios", "notas", "comunicación", "tarea"]
      },
      {
        id: "tarea-asignar",
        titulo: "Asignar tareas al equipo",
        contenido: 'Al crear o editar una tarea, selecciona el campo "Asignado a" y elige un miembro del equipo. Solo los administradores pueden reasignar tareas ya asignadas a otra persona. El listado de tareas permite filtrar por usuario asignado para ver la carga de trabajo de cada miembro.',
        etiquetas: ["asignar", "equipo", "usuario", "responsable", "filtrar"]
      }
    ]
  },
  {
    id: "workflows",
    nombre: "Workflows",
    icono: Workflow,
    descripcion: "Automatiza acciones con reglas SI condición ENTONCES acción.",
    articulos: [
      {
        id: "workflow-que-es",
        titulo: "Qué es un workflow",
        contenido: 'Un workflow es una regla de automatización con la estructura "SI [condición] ENTONCES [acción]". Permite automatizar tareas repetitivas como cambiar el estado de una notificación cuando cambia su urgencia, o crear una tarea automáticamente cuando se registra un nuevo certificado. Los workflows están disponibles en planes Profesional y superior; los administradores son quienes los gestionan.',
        etiquetas: ["workflow", "automatización", "regla", "condición", "acción"]
      },
      {
        id: "workflow-crear",
        titulo: "Crear una regla de automatización",
        contenido: 'En "Workflows", haz clic en "Nuevo workflow". El editor tiene tres pestañas: General (nombre y descripción), Condiciones (disparador + filtros) y Acciones (qué hace el workflow cuando se cumple la condición). Activa o desactiva el workflow con el interruptor del listado sin necesidad de eliminarlo. Guarda el workflow; se ejecutará automáticamente cuando se cumpla la condición configurada.',
        etiquetas: ["crear", "workflow", "editor", "condición", "acción", "activar"]
      },
      {
        id: "workflow-disparadores",
        titulo: "Disparadores y acciones disponibles",
        contenido: "Disparadores disponibles: creación de certificado, actualización de notificación, cambio de urgencia, vencimiento próximo, y ejecución manual. Acciones disponibles: cambiar estado de notificación, asignar notificación a usuario, crear tarea asociada. Puedes combinar múltiples condiciones con operadores (igual a, contiene, mayor que, etc.) para afinar cuándo se ejecuta el workflow.",
        etiquetas: ["disparador", "trigger", "acción", "operador", "condición"]
      },
      {
        id: "workflow-manual",
        titulo: "Ejecutar un workflow manualmente",
        contenido: 'Desde el listado de workflows, haz clic en el botón de ejecución (▶) de cualquier workflow activo. La ejecución manual es útil para probar el workflow antes de activarlo en producción. Cada ejecución queda registrada en el historial de ejecuciones con su resultado (éxito o error). El historial está accesible desde "Workflows" → pestaña "Historial de ejecuciones".',
        etiquetas: ["ejecutar", "manual", "historial", "ejecución", "probar"]
      }
    ]
  },
  {
    id: "gestiones",
    nombre: "Gestiones",
    icono: FolderOpen,
    descripcion: "Agrupa notificaciones en expedientes de cliente.",
    articulos: [
      {
        id: "gestion-crear",
        titulo: "Crear una gestión",
        contenido: 'Ve a "Gestiones" y haz clic en "Nueva gestión" (disponible para administradores en planes Profesional o superior). Introduce el nombre del expediente, el cliente asociado, el tipo de gestión y una descripción opcional. Una vez creada, podrás asignarle notificaciones relacionadas para agrupar toda la tramitación en un único expediente.',
        etiquetas: ["crear", "gestión", "expediente", "cliente", "nuevo"]
      },
      {
        id: "gestion-notificaciones",
        titulo: "Asignar notificaciones a una gestión",
        contenido: 'Desde el detalle de una gestión, haz clic en "Asignar notificaciones". Selecciona las notificaciones que quieres incluir en el expediente y confirma. La asignación es de tipo reemplazar: las notificaciones seleccionadas sustituyen a las anteriores. Una notificación puede pertenecer a varias gestiones simultáneamente.',
        etiquetas: ["asignar", "notificaciones", "expediente", "gestión", "añadir"]
      },
      {
        id: "gestion-estados",
        titulo: "Estados de una gestión",
        contenido: 'Los estados posibles son: Activa, En tramitación, Pendiente de resolución, Resuelta y Archivada. El estado "Archivada" es el equivalente al soft delete: la gestión desaparece del listado activo pero se conserva en el historial. Cambia el estado desde el detalle de la gestión o desde el menú de opciones del listado. El listado permite filtrar gestiones por tipo y estado para localizarlas rápidamente.',
        etiquetas: ["estados", "activa", "archivada", "resuelta", "tramitación"]
      }
    ]
  },
  {
    id: "configuracion",
    nombre: "Configuración",
    icono: Settings,
    descripcion: "Personaliza CertiGestor para tu organización.",
    articulos: [
      {
        id: "config-dias-aviso",
        titulo: "Configurar días de aviso previo",
        contenido: 'En Configuración → "Avisos de caducidad", ajusta cuántos días antes de la caducidad quieres recibir notificaciones. El valor predeterminado es 30 días, pero puedes personalizarlo según las necesidades de tu organización. El cambio se aplica inmediatamente: los próximos eventos de agenda se recalculan con el nuevo valor.',
        etiquetas: ["días", "aviso", "caducidad", "configurar", "antelación"]
      },
      {
        id: "config-logo",
        titulo: "Logo corporativo",
        contenido: 'Sube el logo de tu organización en Configuración → "Apariencia". El logo aparecerá en los reportes PDF generados por CertiGestor. Formatos aceptados: PNG y JPEG. Tamaño recomendado: 200×80 píxeles o similar ratio horizontal.',
        etiquetas: ["logo", "corporativo", "imagen", "apariencia", "pdf"]
      },
      {
        id: "config-integraciones",
        titulo: "Integraciones con calendarios",
        contenido: 'Conecta Google Calendar o Microsoft Outlook desde Configuración → "Integraciones" (plan Profesional o superior). Tras autorizar el acceso OAuth, sincroniza los vencimientos de tus certificados al calendario seleccionado. Puedes desconectar la integración en cualquier momento sin pérdida de datos en CertiGestor.',
        etiquetas: ["google calendar", "outlook", "integración", "sincronizar", "oauth"]
      },
      {
        id: "config-usuarios",
        titulo: "Gestión de usuarios",
        contenido: 'Los administradores pueden invitar nuevos usuarios en Configuración → "Usuarios" o desde la sección "Usuarios" del menú. Cada usuario tiene un rol (administrador o asesor) que determina qué acciones puede realizar. El número máximo de usuarios depende del plan contratado; al alcanzar el límite, el botón de crear queda bloqueado. Los usuarios pueden desactivarse (soft delete) para revocar su acceso sin eliminar su historial.',
        etiquetas: ["usuarios", "invitar", "rol", "administrador", "asesor", "límite"]
      }
    ]
  }
];
function PaginaAyuda() {
  const [categoriaActiva, setCategoriaActiva] = reactExports.useState(categoriasAyuda[0].id);
  const [busqueda, setBusqueda] = reactExports.useState("");
  const [busquedaDebounced, setBusquedaDebounced] = reactExports.useState("");
  const [articuloExpandido, setArticuloExpandido] = reactExports.useState(null);
  reactExports.useEffect(() => {
    const timer = setTimeout(() => setBusquedaDebounced(busqueda), 300);
    return () => clearTimeout(timer);
  }, [busqueda]);
  const cambiarCategoria = (id) => {
    setCategoriaActiva(id);
    setArticuloExpandido(null);
  };
  const articulosFiltrados = reactExports.useMemo(() => {
    if (!busquedaDebounced) {
      const cat = categoriasAyuda.find((c) => c.id === categoriaActiva);
      return cat?.articulos ?? [];
    }
    const termino = busquedaDebounced.toLowerCase();
    return categoriasAyuda.flatMap(
      (cat) => cat.articulos.filter(
        (a) => a.titulo.toLowerCase().includes(termino) || a.contenido.toLowerCase().includes(termino) || a.etiquetas.some((e) => e.toLowerCase().includes(termino))
      )
    );
  }, [busquedaDebounced, categoriaActiva]);
  const toggleArticulo = (id) => {
    setArticuloExpandido((prev) => prev === id ? null : id);
  };
  const hasBusqueda = busquedaDebounced.length > 0;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold text-white", children: "Centro de ayuda" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-superficie-400", children: "Encuentra respuestas sobre el uso de CertiGestor" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-1 gap-6 lg:grid-cols-[240px_1fr]", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("aside", { className: "cristal h-fit p-2", children: /* @__PURE__ */ jsxRuntimeExports.jsx("nav", { className: "space-y-0.5", children: categoriasAyuda.map((cat) => {
        const Icono = cat.icono;
        const activa = cat.id === categoriaActiva && !hasBusqueda;
        return /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => {
              cambiarCategoria(cat.id);
              setBusqueda("");
            },
            className: [
              "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
              activa ? "bg-acento-500/10 text-acento-400" : "text-superficie-300 hover:bg-white/[0.04] hover:text-white"
            ].join(" "),
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(
                Icono,
                {
                  className: ["h-4 w-4 shrink-0", activa ? "text-acento-400" : "text-superficie-500"].join(" ")
                }
              ),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "truncate", children: cat.nombre })
            ]
          },
          cat.id
        );
      }) }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-superficie-500 pointer-events-none" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(
            "input",
            {
              type: "text",
              placeholder: "Buscar en el centro de ayuda…",
              value: busqueda,
              onChange: (e) => setBusqueda(e.target.value),
              className: [
                "w-full rounded-lg py-2.5 pl-9 pr-4 text-sm",
                "bg-superficie-900/50 border border-white/[0.06]",
                "text-superficie-100 placeholder-superficie-500",
                "focus:outline-none focus:ring-2 focus:ring-acento-500/40 focus:border-acento-500/40",
                "transition-colors"
              ].join(" ")
            }
          )
        ] }),
        hasBusqueda ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: articulosFiltrados.length === 0 ? "Sin resultados" : `${articulosFiltrados.length} artículo${articulosFiltrados.length !== 1 ? "s" : ""} encontrado${articulosFiltrados.length !== 1 ? "s" : ""}` }) : (() => {
          const cat = categoriasAyuda.find((c) => c.id === categoriaActiva);
          return cat ? /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500", children: cat.descripcion }) : null;
        })(),
        articulosFiltrados.length > 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: articulosFiltrados.map((articulo) => {
          const expandido = articuloExpandido === articulo.id;
          return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal overflow-hidden", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs(
              "button",
              {
                onClick: () => toggleArticulo(articulo.id),
                className: "flex w-full items-center justify-between gap-4 p-4 text-left hover:bg-white/[0.03] transition-colors",
                children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-medium text-white", children: articulo.titulo }),
                  expandido ? /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronUp, { className: "h-4 w-4 shrink-0 text-superficie-400" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "h-4 w-4 shrink-0 text-superficie-400" })
                ]
              }
            ),
            expandido && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-white/[0.06] px-4 pb-4 pt-3", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm leading-relaxed text-superficie-300", children: articulo.contenido }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-3 flex flex-wrap gap-1.5", children: articulo.etiquetas.map((etiqueta) => /* @__PURE__ */ jsxRuntimeExports.jsx(
                "span",
                {
                  className: "rounded-full bg-superficie-800/60 px-2 py-0.5 text-xs text-superficie-500",
                  children: etiqueta
                },
                etiqueta
              )) })
            ] })
          ] }, articulo.id);
        }) }) : (
          /* Estado vacio */
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "cristal flex flex-col items-center justify-center py-16 text-center", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(CircleHelp, { className: "mb-3 h-10 w-10 text-superficie-600" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-400", children: "No se encontraron artículos" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-xs text-superficie-600", children: "Prueba con otros términos de búsqueda" })
          ] })
        )
      ] })
    ] })
  ] });
}
export {
  PaginaAyuda
};
