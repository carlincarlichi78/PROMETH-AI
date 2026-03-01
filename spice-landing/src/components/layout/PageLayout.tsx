import Navbar from './Navbar'
import Footer from './Footer'

export default function PageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-prometh-bg">
      <Navbar />
      <main className="pt-16">{children}</main>
      <Footer />
    </div>
  )
}
