import { c as createLucideIcon, j as jsxRuntimeExports, S as ShieldCheck, L as Lock, U as Users, E as Eye, a as Shield, G as Globe, b as Link, D as Download } from "./index-DMbE3NR1.js";
import { H as History } from "./history-CoQ7xusF.js";
import { F as FileCheck } from "./file-check-CGZ00Z_g.js";
import { A as Award } from "./award-CLV5ctGj.js";
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Database = createLucideIcon("Database", [
  ["ellipse", { cx: "12", cy: "5", rx: "9", ry: "3", key: "msslwz" }],
  ["path", { d: "M3 5V19A9 3 0 0 0 21 19V5", key: "1wlel7" }],
  ["path", { d: "M3 12A9 3 0 0 0 21 12", key: "mv7ke4" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const KeyRound = createLucideIcon("KeyRound", [
  [
    "path",
    {
      d: "M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z",
      key: "1s6t7t"
    }
  ],
  ["circle", { cx: "16.5", cy: "7.5", r: ".5", fill: "currentColor", key: "w0ekpg" }]
]);
/**
 * @license lucide-react v0.469.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */
const Server = createLucideIcon("Server", [
  ["rect", { width: "20", height: "8", x: "2", y: "2", rx: "2", ry: "2", key: "ngkwjq" }],
  ["rect", { width: "20", height: "8", x: "2", y: "14", rx: "2", ry: "2", key: "iecqi9" }],
  ["line", { x1: "6", x2: "6.01", y1: "6", y2: "6", key: "16zg32" }],
  ["line", { x1: "6", x2: "6.01", y1: "18", y2: "18", key: "nzw8ys" }]
]);
const MEDIDAS_SEGURIDAD = [
  {
    icono: Lock,
    titulo: "Cifrado AES-256-GCM",
    descripcion: "Todos los datos sensibles se cifran con AES-256-GCM, el mismo estándar utilizado por entidades bancarias. Las contraseñas de certificados PFX, configuraciones IMAP y tokens de integración se almacenan cifrados con derivación de clave scrypt.",
    etiqueta: "Cifrado"
  },
  {
    icono: KeyRound,
    titulo: "Autenticación robusta",
    descripcion: "Sistema de tokens JWT con access token (15 min) y refresh token (7 días). Contraseñas hasheadas con bcrypt (12 rondas de salt). Algoritmo HS256 explícito. Protección contra ataques de fuerza bruta con rate limiting.",
    etiqueta: "Autenticación"
  },
  {
    icono: Users,
    titulo: "Control de acceso multinivel",
    descripcion: "RBAC (Control de Acceso Basado en Roles) con tres niveles: administrador, asesor y superadmin. Verificación de plan de suscripción por endpoint. Aislamiento total entre organizaciones — ningún usuario puede acceder a datos de otra organización.",
    etiqueta: "Autorización"
  },
  {
    icono: Eye,
    titulo: "Portal cliente read-only",
    descripcion: "Los clientes acceden a sus datos mediante enlace JWT seguro con hash SHA-256. El portal es estrictamente de solo lectura y nunca expone datos internos como notas, asignaciones ni contraseñas de certificados.",
    etiqueta: "Privacidad"
  },
  {
    icono: History,
    titulo: "Auditoría completa",
    descripcion: "Cada acceso a certificados, firma de documentos y cambio en notificaciones queda registrado con usuario, IP, acción y timestamp. Historial completo de cambios en notificaciones para trazabilidad total.",
    etiqueta: "Trazabilidad"
  },
  {
    icono: Database,
    titulo: "Protección contra inyección SQL",
    descripcion: "Utilizamos Drizzle ORM con consultas parametrizadas que hacen técnicamente imposible la inyección SQL. Toda entrada de usuario se valida con esquemas Zod antes de llegar a la base de datos.",
    etiqueta: "Integridad"
  },
  {
    icono: Shield,
    titulo: "Cabeceras de seguridad HTTP",
    descripcion: "Helmet.js protege contra clickjacking (X-Frame-Options), MIME sniffing (X-Content-Type-Options) y fuerza HTTPS (HSTS). Rate limiting diferenciado por tipo de endpoint.",
    etiqueta: "Infraestructura"
  },
  {
    icono: Server,
    titulo: "Infraestructura en la UE",
    descripcion: "Servidores alojados en Hetzner (Alemania), dentro de la Unión Europea. HTTPS obligatorio con certificado SSL. Base de datos PostgreSQL en contenedor Docker aislado. Backups cifrados.",
    etiqueta: "Infraestructura"
  },
  {
    icono: FileCheck,
    titulo: "Firma digital PAdES",
    descripcion: "Firma electrónica avanzada conforme al estándar ETSI.CAdES.detached (PAdES). Compatible con certificados cualificados. Verificación de integridad del documento firmado.",
    etiqueta: "Firma"
  }
];
const NORMATIVAS = [
  {
    siglas: "RGPD",
    nombre: "Reglamento General de Protección de Datos",
    referencia: "UE 2016/679",
    cumplimiento: [
      "Cifrado de datos personales (Art. 32)",
      "Minimización de datos (Art. 5)",
      "Registro de actividades de tratamiento (Art. 30)",
      "Derecho al olvido / soft delete (Art. 17)",
      "Portabilidad de datos (Art. 20)"
    ]
  },
  {
    siglas: "LOPDGDD",
    nombre: "Ley Orgánica de Protección de Datos",
    referencia: "LO 3/2018",
    cumplimiento: [
      "Transposición española del RGPD",
      "Protección reforzada de datos especialmente sensibles",
      "Auditoría de accesos registrada"
    ]
  },
  {
    siglas: "eIDAS",
    nombre: "Reglamento de Identificación Electrónica",
    referencia: "UE 910/2014",
    cumplimiento: [
      "Firma electrónica avanzada PAdES (ETSI)",
      "Gestión de certificados digitales cualificados",
      "Importación y custodia segura de certificados PFX/P12"
    ]
  },
  {
    siglas: "Ley 39/2015",
    nombre: "Procedimiento Administrativo Común",
    referencia: "Ley 39/2015",
    cumplimiento: [
      "Cálculo de plazos legales (días hábiles/naturales)",
      "Integración con DEHú (notificaciones electrónicas)",
      "Trazabilidad de notificaciones administrativas"
    ]
  },
  {
    siglas: "OWASP",
    nombre: "Top 10 Vulnerabilidades Web",
    referencia: "2021",
    cumplimiento: [
      "A01 — Control de acceso: RBAC + aislamiento organizacional",
      "A02 — Criptografía: AES-256-GCM + bcrypt + SHA-256",
      "A03 — Inyección: Drizzle ORM (SQL parameterizado) + Zod",
      "A04 — Diseño inseguro: Soft delete + auditoría",
      "A05 — Configuración: Secrets via env, validación en startup"
    ]
  },
  {
    siglas: "ENS",
    nombre: "Esquema Nacional de Seguridad",
    referencia: "RD 311/2022",
    cumplimiento: [
      "Confidencialidad: cifrado AES-256-GCM de datos sensibles",
      "Integridad: consultas parametrizadas + validación Zod",
      "Disponibilidad: Docker containerizado + health checks",
      "Autenticidad: JWT firmado + certificados digitales PAdES",
      "Trazabilidad: auditoría completa fire-and-forget"
    ]
  }
];
const ESTADISTICAS = [
  { valor: "AES-256", etiqueta: "Cifrado de grado militar" },
  { valor: "12", etiqueta: "Rondas de hash bcrypt" },
  { valor: "100%", etiqueta: "Consultas SQL parametrizadas" },
  { valor: "1.122", etiqueta: "Tests automatizados" }
];
function PaginaSeguridad() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-h-screen bg-superficie-950", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("section", { className: "relative overflow-hidden pt-24 pb-20 sm:pt-32 sm:pb-28", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute inset-0 bg-gradient-to-b from-acento-500/[0.03] to-transparent" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-acento-500/[0.04] rounded-full blur-3xl" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "inline-flex items-center gap-2 px-3 py-1.5 mb-6 rounded-full border border-acento-500/20 bg-acento-500/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(ShieldCheck, { size: 14, className: "text-acento-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium text-acento-400", children: "Seguridad de nivel empresarial" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("h1", { className: "text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight mb-6", children: [
          "La seguridad de tus clientes",
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "bg-gradient-to-r from-acento-400 to-acento-300 bg-clip-text text-transparent", children: "es nuestra prioridad" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg sm:text-xl text-superficie-400 max-w-2xl mx-auto mb-10", children: "CertiGestor protege los certificados digitales y datos de tus clientes con los mismos estándares de cifrado utilizados por entidades bancarias." }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mx-auto", children: ESTADISTICAS.map((stat) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "div",
          {
            className: "p-4 rounded-xl border border-white/[0.06] bg-white/[0.02]",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-2xl font-bold text-acento-400", children: stat.valor }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-superficie-500 mt-1", children: stat.etiqueta })
            ]
          },
          stat.etiqueta
        )) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("section", { className: "py-20 sm:py-28", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center mb-16", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-3xl sm:text-4xl font-bold text-white mb-4", children: "Medidas técnicas de protección" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg text-superficie-400 max-w-2xl mx-auto", children: "Cada capa de CertiGestor está diseñada para proteger los datos de tus clientes" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid md:grid-cols-2 lg:grid-cols-3 gap-6", children: MEDIDAS_SEGURIDAD.map((medida) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: "group p-6 rounded-2xl border border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-acento-500/20 transition-all duration-300",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 mb-4", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-xl bg-acento-500/10 flex items-center justify-center group-hover:bg-acento-500/15 transition-colors", children: /* @__PURE__ */ jsxRuntimeExports.jsx(medida.icono, { size: 20, className: "text-acento-400" }) }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-semibold uppercase tracking-widest text-acento-500/60", children: medida.etiqueta })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-lg font-semibold text-white mb-2", children: medida.titulo }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 leading-relaxed", children: medida.descripcion })
          ]
        },
        medida.titulo
      )) })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("section", { className: "py-20 sm:py-28 bg-white/[0.01]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center mb-16", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "inline-flex items-center gap-2 px-3 py-1.5 mb-4 rounded-full border border-acento-500/20 bg-acento-500/[0.06]", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Award, { size: 14, className: "text-acento-400" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-medium text-acento-400", children: "Cumplimiento normativo" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-3xl sm:text-4xl font-bold text-white mb-4", children: "Alineado con los estándares más exigentes" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg text-superficie-400 max-w-2xl mx-auto", children: "CertiGestor implementa medidas técnicas conformes a las principales normativas europeas y nacionales de seguridad de la información" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid md:grid-cols-2 lg:grid-cols-3 gap-6", children: NORMATIVAS.map((norma) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: "p-6 rounded-2xl border border-white/[0.06] bg-white/[0.02]",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-baseline gap-3 mb-4", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-2xl font-bold text-acento-400", children: norma.siglas }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs text-superficie-500", children: norma.referencia })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-medium text-superficie-300 mb-4", children: norma.nombre }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "space-y-2", children: norma.cumplimiento.map((punto, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex items-start gap-2 text-sm text-superficie-400", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(ShieldCheck, { size: 14, className: "text-acento-500/60 mt-0.5 shrink-0" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: punto })
            ] }, i)) })
          ]
        },
        norma.siglas
      )) })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("section", { className: "py-20 sm:py-28", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-4xl mx-auto px-4 sm:px-6 lg:px-8", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center mb-12", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-3xl sm:text-4xl font-bold text-white mb-4", children: "Arquitectura de seguridad por capas" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg text-superficie-400 max-w-2xl mx-auto", children: "Defensa en profundidad: cada petición atraviesa múltiples controles antes de acceder a datos" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-3", children: [
        {
          capa: "1",
          nombre: "Perímetro",
          detalle: "HTTPS + CORS + Helmet + Rate Limiting",
          icono: Globe
        },
        {
          capa: "2",
          nombre: "Autenticación",
          detalle: "JWT HS256 + bcrypt (12 rondas) + Refresh token",
          icono: KeyRound
        },
        {
          capa: "3",
          nombre: "Autorización",
          detalle: "RBAC roles + Planes + Aislamiento organizacional",
          icono: Users
        },
        {
          capa: "4",
          nombre: "Validación",
          detalle: "Zod schemas + SQL parametrizado + MIME filtering",
          icono: FileCheck
        },
        {
          capa: "5",
          nombre: "Datos",
          detalle: "AES-256-GCM + SHA-256 hashing + Soft delete",
          icono: Lock
        },
        {
          capa: "6",
          nombre: "Auditoría",
          detalle: "Registro de accesos + Historial de cambios + Trazabilidad",
          icono: History
        }
      ].map((item) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "div",
        {
          className: "flex items-center gap-4 p-4 rounded-xl border border-white/[0.06] bg-white/[0.02] hover:border-acento-500/20 transition-all",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "w-10 h-10 rounded-lg bg-acento-500/10 flex items-center justify-center shrink-0", children: /* @__PURE__ */ jsxRuntimeExports.jsx(item.icono, { size: 18, className: "text-acento-400" }) }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1 min-w-0", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-baseline gap-2", children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-xs font-mono text-acento-500/60", children: [
                  "CAPA ",
                  item.capa
                ] }),
                /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-sm font-semibold text-white", children: item.nombre })
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-superficie-400 mt-0.5", children: item.detalle })
            ] })
          ]
        },
        item.capa
      )) })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("section", { className: "py-20 sm:py-28 bg-white/[0.01]", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-3xl sm:text-4xl font-bold text-white mb-4", children: "Protege los datos de tus clientes hoy" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg text-superficie-400 mb-8 max-w-xl mx-auto", children: "Empieza a usar CertiGestor con total tranquilidad. Tus certificados y datos están en las mejores manos." }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col sm:flex-row gap-4 justify-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          Link,
          {
            to: "/registro",
            className: "inline-flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-superficie-950 bg-acento-500 rounded-lg hover:bg-acento-400 transition-colors",
            children: "Empezar gratis"
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "a",
          {
            href: "/documentos/informe-seguridad-certigestor.pdf",
            download: true,
            className: "inline-flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium text-superficie-300 border border-white/10 rounded-lg hover:bg-white/[0.05] transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { size: 16 }),
              "Descargar informe completo (PDF)"
            ]
          }
        )
      ] })
    ] }) })
  ] });
}
export {
  PaginaSeguridad
};
