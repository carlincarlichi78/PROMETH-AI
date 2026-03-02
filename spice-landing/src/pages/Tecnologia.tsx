import PageLayout from '../components/layout/PageLayout'
import HeroTecnologia from '../components/tecnologia/HeroTecnologia'
import StackTecnologico from '../components/tecnologia/StackTecnologico'
import MetricasCalidad from '../components/tecnologia/MetricasCalidad'
import ModulosNuevos from '../components/tecnologia/ModulosNuevos'
import DiagramaPipeline from '../components/DiagramaPipeline'
import DiagramaOCR from '../components/DiagramaOCR'
import TiposDocumento from '../components/TiposDocumento'
import DiagramaJerarquia from '../components/DiagramaJerarquia'
import DiagramaClasificador from '../components/DiagramaClasificador'
import DiagramaAprendizaje from '../components/DiagramaAprendizaje'
import ModelosFiscales from '../components/ModelosFiscales'
import MapaTerritorios from '../components/MapaTerritorios'
import FormasJuridicas from '../components/FormasJuridicas'

export default function Tecnologia() {
  return (
    <PageLayout>
      <HeroTecnologia />
      <MetricasCalidad />
      <StackTecnologico />
      <DiagramaPipeline />
      <DiagramaOCR />
      <TiposDocumento />
      <DiagramaJerarquia />
      <DiagramaClasificador />
      <DiagramaAprendizaje />
      <ModelosFiscales />
      <MapaTerritorios />
      <FormasJuridicas />
      <ModulosNuevos />
    </PageLayout>
  )
}
