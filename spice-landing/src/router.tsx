import { createBrowserRouter, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import Gestorias from './pages/Gestorias'
import Asesores from './pages/Asesores'
import Clientes from './pages/Clientes'
import Tecnologia from './pages/Tecnologia'
import Seguridad from './pages/Seguridad'
import Precios from './pages/Precios'

export const router = createBrowserRouter([
  { path: '/',               element: <Home /> },
  { path: '/gestorias',      element: <Gestorias /> },
  { path: '/asesores',       element: <Asesores /> },
  { path: '/clientes',       element: <Clientes /> },
  { path: '/tecnologia',     element: <Tecnologia /> },
  { path: '/como-funciona',  element: <Navigate to="/tecnologia" replace /> },
  { path: '/seguridad',      element: <Seguridad /> },
  { path: '/precios',        element: <Precios /> },
])
