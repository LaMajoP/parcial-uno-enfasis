import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { CitizenForm } from './pages/CitizenForm'
import { Login } from './pages/Login'
import { OperatorDashboard } from './pages/OperatorDashboard'
import { TrackEmergency } from './pages/TrackEmergency'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Un fallo de red en una emergencia no se reintenta indefinidamente: es
      // mejor mostrar el error y dejar que la persona decida.
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

function NavItem({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `rounded-md px-3 py-1.5 text-sm font-medium ${
          isActive
            ? 'bg-slate-900 text-white'
            : 'text-slate-600 hover:bg-slate-100'
        }`
      }
    >
      {children}
    </NavLink>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50">
          <nav className="border-b border-slate-200 bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
              <Link to="/" className="font-semibold text-slate-900">
                Plataforma de Emergencias
              </Link>
              <div className="flex gap-2">
                <NavItem to="/">Reportar</NavItem>
                <NavItem to="/operator">Operador</NavItem>
                <NavItem to="/login">Sesión</NavItem>
              </div>
            </div>
          </nav>

          <main className="mx-auto max-w-6xl">
            <Routes>
              <Route path="/" element={<CitizenForm />} />
              <Route path="/track/:id" element={<TrackEmergency />} />
              <Route path="/operator" element={<OperatorDashboard />} />
              <Route path="/login" element={<Login />} />
              <Route
                path="*"
                element={
                  <div className="p-6 text-slate-600">
                    Esta página no existe.{' '}
                    <Link to="/" className="underline">
                      Volver al inicio
                    </Link>
                  </div>
                }
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
