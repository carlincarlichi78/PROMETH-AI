import PageLayout from '../components/layout/PageLayout'
import Hero from '../components/home/Hero'
import SelectorPerfil from '../components/home/SelectorPerfil'

export default function Home() {
  return (
    <PageLayout>
      <Hero />
      <SelectorPerfil />
    </PageLayout>
  )
}
