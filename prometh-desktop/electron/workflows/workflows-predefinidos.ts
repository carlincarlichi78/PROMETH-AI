import type { WorkflowDesktop, AccionWorkflowDesktop } from './tipos-workflows-desktop'

// --- Helpers para crear workflows predefinidos ---

function crearId(categoria: string, modelo: string): string {
  return `predef_${categoria}_${modelo}`.toLowerCase().replace(/\s+/g, '_')
}

const AHORA = new Date().toISOString()

/**
 * Crea un workflow predefinido con la cadena estandar:
 * 1. Split PDF por NIF → 2. Proteger con password → 3. Enviar email → 4. Organizar en repositorio
 */
function crearWorkflowModelo(
  modelo: string,
  nombre: string,
  categoria: string,
  descripcion: string,
  acciones?: AccionWorkflowDesktop[]
): WorkflowDesktop {
  const accionesDefault: AccionWorkflowDesktop[] = acciones ?? [
    {
      tipo: 'split_pdf',
      config: {
        carpetaOrigen: '{carpetaTrabajo}',
        carpetaDestino: '{carpetaTrabajo}/separados',
        modoCorte: 'nif',
        nombreArchivoDestino: `${modelo}_{nif}_{fecha}`,
      },
    },
    {
      tipo: 'protect_pdf',
      config: {
        carpetaOrigen: '{carpetaTrabajo}/separados',
        carpetaDestino: '{carpetaTrabajo}/protegidos',
        modoPassword: 'cliente',
      },
    },
    {
      tipo: 'send_mail',
      config: {
        emailOrigen: '',
        emailDestino: '',
        asunto: `${nombre} - {nif} - {fecha}`,
        cuerpo: `<p>Adjunto ${nombre} correspondiente al NIF {nif}.</p><p>Generado automaticamente por CertiGestor.</p>`,
        carpetaAdjuntos: '{carpetaTrabajo}/protegidos',
        extensiones: ['.pdf'],
        smtpHost: '',
        smtpPort: 587,
        smtpUser: '',
        smtpPass: '',
        smtpSecure: false,
      },
    },
    {
      tipo: 'send_to_repository',
      config: {
        repositorioRaiz: '',
        estructuraCarpetas: '{nif}/{anio}/{modelo}',
        sobreescribir: false,
        carpetaOrigen: '{carpetaTrabajo}/protegidos',
      },
    },
  ]

  return {
    id: crearId(categoria, modelo),
    nombre,
    descripcion,
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: accionesDefault,
    predefinido: true,
    categoria,
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  }
}

/**
 * Crea un workflow simplificado solo con split + organizar.
 */
function crearWorkflowSimple(
  modelo: string,
  nombre: string,
  categoria: string,
  descripcion: string
): WorkflowDesktop {
  return crearWorkflowModelo(modelo, nombre, categoria, descripcion, [
    {
      tipo: 'split_pdf',
      config: {
        carpetaOrigen: '{carpetaTrabajo}',
        carpetaDestino: '{carpetaTrabajo}/separados',
        modoCorte: 'nif',
        nombreArchivoDestino: `${modelo}_{nif}_{fecha}`,
      },
    },
    {
      tipo: 'send_to_repository',
      config: {
        repositorioRaiz: '',
        estructuraCarpetas: '{nif}/{anio}/{modelo}',
        sobreescribir: false,
        carpetaOrigen: '{carpetaTrabajo}/separados',
      },
    },
  ])
}

// --- Catalogo de workflows predefinidos ---

/** Modelos AEAT — Impuestos trimestrales */
const MODELOS_TRIMESTRALES: WorkflowDesktop[] = [
  crearWorkflowModelo('130', 'Modelo 130 - Pago fraccionado IRPF', 'IRPF',
    'Separar, proteger y enviar el modelo 130 de pago fraccionado de IRPF por NIF'),
  crearWorkflowModelo('131', 'Modelo 131 - Estimacion objetiva IRPF', 'IRPF',
    'Procesamiento del modelo 131 de estimacion objetiva'),
  crearWorkflowModelo('111', 'Modelo 111 - Retenciones IRPF', 'Retenciones',
    'Retenciones e ingresos a cuenta del IRPF'),
  crearWorkflowModelo('115', 'Modelo 115 - Retenciones alquileres', 'Retenciones',
    'Retenciones sobre rentas de arrendamientos inmobiliarios'),
  crearWorkflowModelo('123', 'Modelo 123 - Retenciones capital mobiliario', 'Retenciones',
    'Retenciones e ingresos a cuenta del capital mobiliario'),
  crearWorkflowModelo('303', 'Modelo 303 - IVA trimestral', 'IVA',
    'Autoliquidacion trimestral del IVA'),
  crearWorkflowModelo('309', 'Modelo 309 - IVA no periodico', 'IVA',
    'Declaracion-liquidacion no periodica del IVA'),
  crearWorkflowModelo('349', 'Modelo 349 - Operaciones intracomunitarias', 'IVA',
    'Declaracion recapitulativa de operaciones intracomunitarias'),
  crearWorkflowModelo('347', 'Modelo 347 - Operaciones terceros', 'Informativa',
    'Declaracion anual de operaciones con terceros'),
  crearWorkflowModelo('202', 'Modelo 202 - Pago fraccionado IS', 'Sociedades',
    'Pago fraccionado del Impuesto de Sociedades'),
]

/** Modelos AEAT — Anuales */
const MODELOS_ANUALES: WorkflowDesktop[] = [
  crearWorkflowModelo('100', 'Modelo 100 - Declaracion IRPF anual', 'IRPF',
    'Declaracion anual del Impuesto sobre la Renta'),
  crearWorkflowModelo('200', 'Modelo 200 - Impuesto de Sociedades', 'Sociedades',
    'Declaracion anual del Impuesto sobre Sociedades'),
  crearWorkflowModelo('390', 'Modelo 390 - Resumen anual IVA', 'IVA',
    'Declaracion-resumen anual del IVA'),
  crearWorkflowModelo('190', 'Modelo 190 - Resumen retenciones IRPF', 'Retenciones',
    'Resumen anual de retenciones e ingresos a cuenta del IRPF'),
  crearWorkflowModelo('180', 'Modelo 180 - Resumen retenciones alquileres', 'Retenciones',
    'Resumen anual de retenciones sobre rentas de arrendamientos'),
  crearWorkflowModelo('193', 'Modelo 193 - Resumen retenciones capital', 'Retenciones',
    'Resumen anual de retenciones del capital mobiliario'),
  crearWorkflowModelo('296', 'Modelo 296 - Retenciones no residentes', 'Retenciones',
    'Resumen anual de retenciones sobre no residentes'),
  crearWorkflowModelo('840', 'Modelo 840 - IAE alta/baja', 'IAE',
    'Declaracion del Impuesto sobre Actividades Economicas'),
]

/** Modelos AEAT — Especiales */
const MODELOS_ESPECIALES: WorkflowDesktop[] = [
  crearWorkflowModelo('036', 'Modelo 036 - Declaracion censal', 'Censal',
    'Declaracion censal de alta, modificacion o baja'),
  crearWorkflowModelo('037', 'Modelo 037 - Declaracion censal simplificada', 'Censal',
    'Declaracion censal simplificada'),
  crearWorkflowModelo('720', 'Modelo 720 - Bienes en el extranjero', 'Informativa',
    'Declaracion sobre bienes y derechos en el extranjero'),
  crearWorkflowModelo('714', 'Modelo 714 - Impuesto sobre el Patrimonio', 'Patrimonio',
    'Declaracion del Impuesto sobre el Patrimonio'),
  crearWorkflowModelo('210', 'Modelo 210 - IRNR', 'No residentes',
    'Impuesto sobre la Renta de No Residentes'),
  crearWorkflowModelo('216', 'Modelo 216 - Retenciones no residentes', 'No residentes',
    'Retenciones e ingresos a cuenta del IRNR'),
  crearWorkflowModelo('650', 'Modelo 650 - Sucesiones', 'Sucesiones',
    'Impuesto sobre Sucesiones y Donaciones — Sucesiones'),
  crearWorkflowModelo('651', 'Modelo 651 - Donaciones', 'Sucesiones',
    'Impuesto sobre Sucesiones y Donaciones — Donaciones'),
]

/** Seguridad Social */
const MODELOS_SS: WorkflowDesktop[] = [
  crearWorkflowModelo('TC1', 'TC1 - Boletin cotizacion', 'Seguridad Social',
    'Boletin de cotizacion a la Seguridad Social'),
  crearWorkflowModelo('TC2', 'TC2 - Relacion nominal trabajadores', 'Seguridad Social',
    'Relacion nominal de trabajadores para cotizacion'),
  crearWorkflowModelo('RLC', 'RLC - Recibo liquidacion cotizaciones', 'Seguridad Social',
    'Recibo de liquidacion de cotizaciones (sistema RED)'),
  crearWorkflowModelo('RNT', 'RNT - Relacion nominal trabajadores RED', 'Seguridad Social',
    'Relacion nominal de trabajadores (sistema RED)'),
  crearWorkflowSimple('VidaLaboral', 'Vida laboral', 'Seguridad Social',
    'Separar informes de vida laboral por NIF'),
  crearWorkflowSimple('DeudasSS', 'Certificado deudas SS', 'Seguridad Social',
    'Separar certificados de deuda con la Seguridad Social'),
]

/** Documentos AEAT */
const DOCUMENTOS_AEAT: WorkflowDesktop[] = [
  crearWorkflowSimple('DeudasAEAT', 'Certificado deudas AEAT', 'AEAT',
    'Separar certificados de deuda con la Agencia Tributaria'),
  crearWorkflowSimple('DatosFiscales', 'Datos fiscales', 'AEAT',
    'Separar datos fiscales por NIF'),
  crearWorkflowSimple('CertIRPF', 'Certificados tributarios IRPF', 'AEAT',
    'Separar certificados tributarios de IRPF'),
]

/** Otros organismos */
const OTROS_ORGANISMOS: WorkflowDesktop[] = [
  crearWorkflowSimple('CertNacimiento', 'Certificado de nacimiento', 'Justicia',
    'Separar certificados de nacimiento por NIF'),
  crearWorkflowSimple('CertPenales', 'Certificado de penales', 'Justicia',
    'Separar certificados de antecedentes penales'),
  crearWorkflowSimple('Empadronamiento', 'Certificado empadronamiento', 'Padron',
    'Separar certificados de empadronamiento'),
  crearWorkflowSimple('DGTVehiculos', 'Consulta vehiculos DGT', 'DGT',
    'Separar informes de vehiculos por NIF'),
  crearWorkflowSimple('CIRBE', 'Informe CIRBE', 'Banco de Espana',
    'Separar informes CIRBE por NIF'),
  crearWorkflowSimple('CertSEPE', 'Certificado SEPE', 'Empleo',
    'Separar certificados del SEPE'),
  crearWorkflowSimple('CertINSS', 'Certificado INSS', 'Seguridad Social',
    'Separar certificados del INSS'),
  crearWorkflowSimple('Catastro', 'Consulta inmuebles catastro', 'Catastro',
    'Separar datos catastrales por NIF'),
]

/** Workflows genericos de utilidad */
const GENERICOS: WorkflowDesktop[] = [
  {
    id: 'predef_generico_split_nif',
    nombre: 'Separar PDF generico por NIF',
    descripcion: 'Divide cualquier PDF buscando NIFs en cada pagina',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'split_pdf',
        config: {
          carpetaOrigen: '{carpetaTrabajo}',
          carpetaDestino: '{carpetaTrabajo}/separados',
          modoCorte: 'nif',
          nombreArchivoDestino: '{nif}_{original}',
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
  {
    id: 'predef_generico_split_paginas',
    nombre: 'Separar PDF por paginas',
    descripcion: 'Divide un PDF en paginas individuales',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'split_pdf',
        config: {
          carpetaOrigen: '{carpetaTrabajo}',
          carpetaDestino: '{carpetaTrabajo}/separados',
          modoCorte: 'paginas',
          numeroPaginas: 1,
          nombreArchivoDestino: '{original}_pag{indice}',
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
  {
    id: 'predef_generico_proteger_maestra',
    nombre: 'Proteger PDFs con password maestra',
    descripcion: 'Aplica la misma password a todos los PDFs de una carpeta',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'protect_pdf',
        config: {
          carpetaOrigen: '{carpetaTrabajo}',
          carpetaDestino: '{carpetaTrabajo}/protegidos',
          modoPassword: 'maestra',
          passwordMaestra: '',
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
  {
    id: 'predef_generico_proteger_nif',
    nombre: 'Proteger PDFs con NIF como password',
    descripcion: 'Usa el NIF encontrado en el nombre de cada PDF como password',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'protect_pdf',
        config: {
          carpetaOrigen: '{carpetaTrabajo}',
          carpetaDestino: '{carpetaTrabajo}/protegidos',
          modoPassword: 'cliente',
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
  {
    id: 'predef_generico_organizar',
    nombre: 'Organizar archivos en repositorio',
    descripcion: 'Copia archivos a la estructura NIF/Anio/Tipo',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'send_to_repository',
        config: {
          repositorioRaiz: '',
          estructuraCarpetas: '{nif}/{anio}',
          sobreescribir: false,
          carpetaOrigen: '{carpetaTrabajo}',
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
  {
    id: 'predef_generico_email_batch',
    nombre: 'Enviar archivos por email',
    descripcion: 'Envia todos los PDFs de una carpeta por email',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'send_mail',
        config: {
          emailOrigen: '',
          emailDestino: '',
          asunto: 'Documentos - {fecha}',
          cuerpo: '<p>Adjunto documentos generados por CertiGestor.</p>',
          carpetaAdjuntos: '{carpetaTrabajo}',
          extensiones: ['.pdf'],
          smtpHost: '',
          smtpPort: 587,
          smtpUser: '',
          smtpPass: '',
          smtpSecure: false,
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
  {
    id: 'predef_generico_completo',
    nombre: 'Flujo completo: Separar → Proteger → Enviar → Organizar',
    descripcion: 'Cadena completa de procesamiento de documentos tributarios',
    activo: true,
    disparador: 'manual',
    condiciones: [],
    acciones: [
      {
        tipo: 'split_pdf',
        config: {
          carpetaOrigen: '{carpetaTrabajo}',
          carpetaDestino: '{carpetaTrabajo}/separados',
          modoCorte: 'nif',
          nombreArchivoDestino: '{nif}_{original}',
        },
      },
      {
        tipo: 'protect_pdf',
        config: {
          carpetaOrigen: '{carpetaTrabajo}/separados',
          carpetaDestino: '{carpetaTrabajo}/protegidos',
          modoPassword: 'cliente',
        },
      },
      {
        tipo: 'send_mail',
        config: {
          emailOrigen: '',
          emailDestino: '',
          asunto: 'Documentos {nif} - {fecha}',
          cuerpo: '<p>Adjunto documentos del NIF {nif}.</p>',
          carpetaAdjuntos: '{carpetaTrabajo}/protegidos',
          extensiones: ['.pdf'],
          smtpHost: '',
          smtpPort: 587,
          smtpUser: '',
          smtpPass: '',
          smtpSecure: false,
        },
      },
      {
        tipo: 'send_to_repository',
        config: {
          repositorioRaiz: '',
          estructuraCarpetas: '{nif}/{anio}',
          sobreescribir: false,
          carpetaOrigen: '{carpetaTrabajo}/protegidos',
        },
      },
    ],
    predefinido: true,
    categoria: 'Generico',
    creadoEn: AHORA,
    actualizadoEn: AHORA,
  },
]

/** Modelos IVA adicionales */
const MODELOS_IVA_EXTRA: WorkflowDesktop[] = [
  crearWorkflowModelo('310', 'Modelo 310 - IVA regimen simplificado', 'IVA',
    'Declaracion IVA regimen simplificado trimestral'),
  crearWorkflowModelo('341', 'Modelo 341 - Recargo equivalencia', 'IVA',
    'Solicitud reembolso recargo de equivalencia'),
  crearWorkflowModelo('353', 'Modelo 353 - IVA grupo entidades', 'IVA',
    'IVA grupo de entidades — modelo agregado'),
  crearWorkflowModelo('368', 'Modelo 368 - IVA servicios digitales', 'IVA',
    'Declaracion IVA regimen de servicios digitales (MOSS)'),
]

/** Retenciones adicionales */
const RETENCIONES_EXTRA: WorkflowDesktop[] = [
  crearWorkflowModelo('117', 'Modelo 117 - Retenciones fondos inversion', 'Retenciones',
    'Retenciones de participaciones de fondos de inversion'),
  crearWorkflowModelo('124', 'Modelo 124 - Retenciones rentas capital', 'Retenciones',
    'Retenciones de rentas procedentes del arrendamiento de activos'),
  crearWorkflowModelo('128', 'Modelo 128 - Retenciones rentas derivadas', 'Retenciones',
    'Retenciones sobre rentas derivadas de reembolso de participaciones'),
  crearWorkflowModelo('230', 'Modelo 230 - Retenciones no residentes trimestral', 'Retenciones',
    'Retenciones e ingresos a cuenta rendimientos no residentes — trimestral'),
]

/** Modelos informativos adicionales */
const MODELOS_INFORMATIVOS: WorkflowDesktop[] = [
  crearWorkflowModelo('170', 'Modelo 170 - Plataformas digitales', 'Informativa',
    'Declaracion informativa operaciones plataformas digitales'),
  crearWorkflowModelo('182', 'Modelo 182 - Donaciones recibidas', 'Informativa',
    'Declaracion informativa de donativos, donaciones y aportaciones'),
  crearWorkflowModelo('184', 'Modelo 184 - Entidades regimen atribucion', 'Informativa',
    'Declaracion informativa entidades en regimen de atribucion de rentas'),
  crearWorkflowModelo('345', 'Modelo 345 - Planes de pensiones', 'Informativa',
    'Declaracion informativa de planes de pensiones'),
]

/**
 * Retorna todos los workflows predefinidos.
 * Total: 60+ workflows organizados por categoria.
 */
export function obtenerWorkflowsPredefinidos(): WorkflowDesktop[] {
  return [
    ...MODELOS_TRIMESTRALES,
    ...MODELOS_ANUALES,
    ...MODELOS_ESPECIALES,
    ...MODELOS_IVA_EXTRA,
    ...RETENCIONES_EXTRA,
    ...MODELOS_INFORMATIVOS,
    ...MODELOS_SS,
    ...DOCUMENTOS_AEAT,
    ...OTROS_ORGANISMOS,
    ...GENERICOS,
  ]
}

/**
 * Retorna categorias unicas de los workflows predefinidos.
 */
export function obtenerCategorias(): string[] {
  const predefinidos = obtenerWorkflowsPredefinidos()
  const categorias = new Set(predefinidos.map((w) => w.categoria))
  return [...categorias].sort()
}
