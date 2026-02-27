import { Routes, Route } from 'react-router-dom'
import { Layout } from './Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Empresa, EmpresaSubpagina } from './pages/Empresa'
import { PyG } from './pages/PyG'
import { Balance } from './pages/Balance'
import { Diario } from './pages/Diario'
import { Facturas } from './pages/Facturas'
import { Activos } from './pages/Activos'
import { Inbox } from './pages/Inbox'
import { Pipeline } from './pages/Pipeline'
import { Cuarentena } from './pages/Cuarentena'
import { Importar } from './pages/Importar'
import { Exportar } from './pages/Exportar'
import { Calendario } from './pages/Calendario'
import { CierreEjercicio } from './pages/CierreEjercicio'
import { Directorio } from './pages/Directorio'
import { ModelosFiscales } from './pages/ModelosFiscales'
import { GenerarModelo } from './pages/GenerarModelo'
import { HistoricoModelos } from './pages/HistoricoModelos'
import { NotFound } from './pages/NotFound'

/** Definicion de rutas de la aplicacion */
export function App() {
  return (
    <Routes>
      {/* Login — sin layout */}
      <Route path="/login" element={<Login />} />

      {/* Rutas protegidas con layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Home />} />
        <Route path="/directorio" element={<Directorio />} />

        {/* Rutas de empresa */}
        <Route path="/empresa/:id" element={<Empresa />} />

        {/* Contabilidad */}
        <Route path="/empresa/:id/pyg" element={<PyG />} />
        <Route path="/empresa/:id/balance" element={<Balance />} />
        <Route path="/empresa/:id/diario" element={<Diario />} />
        <Route path="/empresa/:id/facturas" element={<Facturas />} />
        <Route path="/empresa/:id/activos" element={<Activos />} />

        {/* Documentos / Procesamiento */}
        <Route path="/empresa/:id/documentos" element={<EmpresaSubpagina titulo="Documentos" />} />
        <Route path="/empresa/:id/inbox" element={<Inbox />} />
        <Route path="/empresa/:id/pipeline" element={<Pipeline />} />
        <Route path="/empresa/:id/cuarentena" element={<Cuarentena />} />

        {/* Herramientas / Operaciones */}
        <Route path="/empresa/:id/importar" element={<Importar />} />
        <Route path="/empresa/:id/exportar" element={<Exportar />} />
        <Route path="/empresa/:id/calendario" element={<Calendario />} />
        <Route path="/empresa/:id/cierre" element={<CierreEjercicio />} />

        {/* Modelos fiscales */}
        <Route path="/empresa/:id/modelos-fiscales" element={<ModelosFiscales />} />
        <Route path="/empresa/:id/modelos-fiscales/generar" element={<GenerarModelo />} />
        <Route path="/empresa/:id/modelos-fiscales/historico" element={<HistoricoModelos />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
