import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { AuthProvider, useAuth } from './lib/auth'
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

/**
 * Navegación dependiente del rol (§8.4: "diferenciar las vistas de ciudadano y
 * de operador"). El enlace a Operador solo se muestra a quien puede usarlo:
 * ofrecer una puerta que va a dar a un "no tienes acceso" es peor que no
 * mostrarla.
 */
function Nav() {
  const { user, role, signOut } = useAuth()

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <Link to="/" className="font-semibold text-slate-900">
          Plataforma de Emergencias
        </Link>

        <div className="flex items-center gap-2">
          <NavItem to="/">Reportar</NavItem>
          {role === 'OPERATOR' && <NavItem to="/operator">Operador</NavItem>}

          {user ? (
            <>
              <span className="hidden px-2 text-sm text-slate-500 sm:inline">
                {user.email}
                <span className="ml-1 rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium text-slate-600">
                  {role}
                </span>
              </span>
              <button
                type="button"
                onClick={signOut}
                className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Salir
              </button>
            </>
          ) : (
            <NavItem to="/login">Sesión</NavItem>
          )}
        </div>
      </div>
    </nav>
  )
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {/* AuthProvider va DENTRO de BrowserRouter: sus hijos usan useNavigate
            y useLocation, que necesitan el contexto del router. */}
        <AuthProvider>
          <div className="min-h-screen bg-slate-50">
            <Nav />

            <main className="mx-auto max-w-6xl">
              <Routes>
                <Route path="/" element={<CitizenForm />} />
                <Route path="/track/:id" element={<TrackEmergency />} />
                <Route
                  path="/operator"
                  element={
                    <ProtectedRoute requireRole="OPERATOR">
                      <OperatorDashboard />
                    </ProtectedRoute>
                  }
                />
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
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
