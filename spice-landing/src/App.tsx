import Navbar from './components/Navbar'
import Hero from './components/Hero'
import Problema from './components/Problema'
import Vision from './components/Vision'
import DiagramaPipeline from './components/DiagramaPipeline'
import DiagramaOCR from './components/DiagramaOCR'
import TiposDocumento from './components/TiposDocumento'
import DiagramaJerarquia from './components/DiagramaJerarquia'
import DiagramaClasificador from './components/DiagramaClasificador'
import Trazabilidad from './components/Trazabilidad'
import MapaTerritorios from './components/MapaTerritorios'
import DiagramaCiclo from './components/DiagramaCiclo'
import ModelosFiscales from './components/ModelosFiscales'
import DiagramaAprendizaje from './components/DiagramaAprendizaje'
import FormasJuridicas from './components/FormasJuridicas'
import Resultados from './components/Resultados'
import Footer from './components/Footer'

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <Problema />
        <Vision />
        <DiagramaPipeline />
        <DiagramaOCR />
        <TiposDocumento />
        <DiagramaJerarquia />
        <DiagramaClasificador />
        <Trazabilidad />
        <MapaTerritorios />
        <DiagramaCiclo />
        <ModelosFiscales />
        <DiagramaAprendizaje />
        <FormasJuridicas />
        <Resultados />
      </main>
      <Footer />
    </>
  )
}
