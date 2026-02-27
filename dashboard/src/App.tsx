import { Routes, Route } from 'react-router-dom'
import { Layout } from './Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Home } from './pages/Home'
import { Login } from './pages/Login'
import { Empresa, EmpresaSubpagina } from './pages/Empresa'
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

        {/* Rutas de empresa */}
        <Route path="/empresa/:id" element={<Empresa />} />
        <Route path="/empresa/:id/pyg" element={<EmpresaSubpagina titulo="Perdidas y Ganancias" />} />
        <Route path="/empresa/:id/balance" element={<EmpresaSubpagina titulo="Balance de Situacion" />} />
        <Route path="/empresa/:id/diario" element={<EmpresaSubpagina titulo="Libro Diario" />} />
        <Route path="/empresa/:id/facturas" element={<EmpresaSubpagina titulo="Facturas" />} />
        <Route path="/empresa/:id/activos" element={<EmpresaSubpagina titulo="Activos Fijos" />} />
        <Route path="/empresa/:id/documentos" element={<EmpresaSubpagina titulo="Documentos" />} />
        <Route path="/empresa/:id/cuarentena" element={<EmpresaSubpagina titulo="Cuarentena" />} />
        <Route path="/empresa/:id/inbox" element={<EmpresaSubpagina titulo="Bandeja de Entrada" />} />
        <Route path="/empresa/:id/importar" element={<EmpresaSubpagina titulo="Importar" />} />
        <Route path="/empresa/:id/exportar" element={<EmpresaSubpagina titulo="Exportar" />} />
        <Route path="/empresa/:id/calendario" element={<EmpresaSubpagina titulo="Calendario Fiscal" />} />
        <Route path="/empresa/:id/cierre" element={<EmpresaSubpagina titulo="Cierre de Ejercicio" />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
