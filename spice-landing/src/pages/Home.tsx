import PageLayout from '../components/layout/PageLayout'
import Hero from '../components/home/Hero'
import Metricas from '../components/home/Metricas'
import SelectorPerfil from '../components/home/SelectorPerfil'
import NuevaGeneracion from '../components/home/NuevaGeneracion'
import Pasos from '../components/home/Pasos'
import BannerSeguridad from '../components/home/BannerSeguridad'

export default function Home() {
  return (
    <PageLayout>
      <Hero />
      <Metricas />
      <Pasos />
      <NuevaGeneracion />
      <SelectorPerfil />
      <BannerSeguridad />
    </PageLayout>
  )
}
