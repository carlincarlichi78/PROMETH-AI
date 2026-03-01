import PageLayout from '../components/layout/PageLayout'
import DiagramaPipeline from '../components/DiagramaPipeline'
import DiagramaOCR from '../components/DiagramaOCR'
import TiposDocumento from '../components/TiposDocumento'
import DiagramaJerarquia from '../components/DiagramaJerarquia'
import DiagramaClasificador from '../components/DiagramaClasificador'
import DiagramaAprendizaje from '../components/DiagramaAprendizaje'
import ModelosFiscales from '../components/ModelosFiscales'

export default function ComoFunciona() {
  return (
    <PageLayout>
      <section className="pt-12 pb-8 px-4 text-center">
        <div className="max-w-3xl mx-auto">
          <span className="inline-block text-xs font-bold bg-prometh-amber/15 text-prometh-amber px-3 py-1 rounded-full mb-6 uppercase tracking-widest">
            Documentación técnica
          </span>
          <h1 className="text-4xl md:text-5xl font-heading font-bold text-prometh-text mb-4">
            Cómo funciona PROMETH-AI
          </h1>
          <p className="text-prometh-muted text-lg">
            Arquitectura detallada del pipeline de automatización contable
          </p>
        </div>
      </section>
      <DiagramaPipeline />
      <DiagramaOCR />
      <TiposDocumento />
      <DiagramaJerarquia />
      <DiagramaClasificador />
      <DiagramaAprendizaje />
      <ModelosFiscales />
    </PageLayout>
  )
}
