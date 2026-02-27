export interface FormaJuridica {
  id: string
  nombre: string
  tipo: 'fisica' | 'juridica'
  modelos: string[]
  particularidades: string
  regimen: string
}

export const formasJuridicas: FormaJuridica[] = [
  { id: 'autonomo', nombre: 'Autonomo persona fisica', tipo: 'fisica', modelos: ['303','130','390','347','100'], particularidades: '6 regimenes IRPF + 3 de IVA', regimen: 'IRPF directa/objetiva + IVA general/simplificado/RE' },
  { id: 'profesional', nombre: 'Profesional con retencion', tipo: 'fisica', modelos: ['303','130','111','190','390','347','100'], particularidades: 'Retencion 15% en facturas emitidas', regimen: 'IRPF directa + IVA general' },
  { id: 'sl', nombre: 'Sociedad Limitada (S.L.)', tipo: 'juridica', modelos: ['303','111','190','200','202','390','347'], particularidades: 'IS 25%, cuentas anuales RM', regimen: 'IS + IVA general' },
  { id: 'slu', nombre: 'S.L. Unipersonal', tipo: 'juridica', modelos: ['303','111','190','200','202','390','347'], particularidades: 'Igual que SL, socio unico', regimen: 'IS + IVA general' },
  { id: 'sa', nombre: 'Sociedad Anonima (S.A.)', tipo: 'juridica', modelos: ['303','111','190','200','202','390','347'], particularidades: 'IS 25%, auditoria si grande', regimen: 'IS + IVA general' },
  { id: 'sll', nombre: 'Sociedad Laboral', tipo: 'juridica', modelos: ['303','111','200','390','347'], particularidades: 'Mayoria capital en trabajadores', regimen: 'IS + IVA general' },
  { id: 'cb', nombre: 'Comunidad de Bienes', tipo: 'fisica', modelos: ['303','130','390','347','100'], particularidades: 'Tributa en IRPF de los comuneros', regimen: 'IRPF atribucion rentas + IVA' },
  { id: 'scp', nombre: 'Sociedad Civil Particular', tipo: 'fisica', modelos: ['303','130','390','347','100'], particularidades: 'Transparencia fiscal', regimen: 'IRPF atribucion rentas + IVA' },
  { id: 'cooperativa', nombre: 'Cooperativa', tipo: 'juridica', modelos: ['303','111','200','390','347'], particularidades: 'IS 20%, SS regimen especial', regimen: 'IS cooperativas + IVA' },
  { id: 'asociacion', nombre: 'Asociacion', tipo: 'juridica', modelos: ['303','200','390','347'], particularidades: 'Sin animo lucro, IS reducido', regimen: 'IS parcial + IVA si actividad' },
  { id: 'comunidad_prop', nombre: 'Comunidad de propietarios', tipo: 'juridica', modelos: [], particularidades: 'Sin IVA, sin IS, solo cuotas', regimen: 'Sin impuestos indirectos' },
  { id: 'fundacion', nombre: 'Fundacion', tipo: 'juridica', modelos: ['200','347'], particularidades: 'IS 10% si cumple requisitos', regimen: 'IS reducido + IVA exento parcial' },
]
