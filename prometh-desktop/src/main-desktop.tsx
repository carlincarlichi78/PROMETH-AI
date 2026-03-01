import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { App } from '@/App'
import './index.css'

const raiz = document.getElementById('root')

if (!raiz) {
  throw new Error('No se encontro el elemento root')
}

// Electron usa HashRouter porque file:// no soporta BrowserRouter
createRoot(raiz).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
