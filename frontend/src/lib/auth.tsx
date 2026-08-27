/**
 * Sesión y rol del usuario (§8.2 de la guía).
 *
 * El rol vive en `app_metadata.role` del JWT, con valores CITIZEN u OPERATOR.
 * Se lee de `app_metadata` y NO de `user_metadata` porque el segundo lo puede
 * modificar el propio usuario desde el navegador: guardar ahí el rol permitiría
 * que cualquier ciudadano se ascendiera a operador con dos líneas en la consola.
 *
 * Ojo con lo que este archivo NO es: el rol que se lee aquí sirve para decidir
 * qué se PINTA, no para autorizar. Quien autoriza de verdad son las políticas
 * RLS de la base de datos, que evalúan el mismo campo del JWT del lado servidor.
 * Si alguien manipula el estado de React para colarse en `/operator`, verá la
 * pantalla pero la base de datos no le devolverá una sola fila.
 */
import type { Session, User } from '@supabase/supabase-js'
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { supabase } from './supabase'

export type Role = 'CITIZEN' | 'OPERATOR'

interface AuthValue {
  session: Session | null
  user: User | null
  /** Rol del usuario, o `null` si no hay sesión. */
  role: Role | null
  /** `true` mientras se resuelve la sesión inicial. Evita parpadeos y redirecciones falsas. */
  loading: boolean
  /** Devuelve el rol recién obtenido: el estado de React aún no se ha actualizado
   *  cuando la pantalla de login necesita decidir a dónde redirigir. */
  signIn: (email: string, password: string) => Promise<Role>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

/** Lee el rol del JWT. Ante la duda, el privilegio mínimo: CITIZEN. */
function roleOf(user: User | null): Role | null {
  if (!user) return null
  return user.app_metadata?.role === 'OPERATOR' ? 'OPERATOR' : 'CITIZEN'
}

/** Traduce los errores de Supabase Auth, que llegan siempre en inglés. */
function translateAuthError(message: string): string {
  if (message.includes('Invalid login credentials')) {
    return 'Correo o contraseña incorrectos.'
  }
  if (message.includes('Email not confirmed')) {
    return 'La cuenta existe pero el correo no está confirmado.'
  }
  if (message.includes('Failed to fetch')) {
    return 'No se pudo contactar con Supabase. Revisa la conexión o la configuración del proyecto.'
  }
  return message
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Dos fuentes distintas y las dos hacen falta:
    //   getSession()        → la sesión ya guardada (recarga de página).
    //   onAuthStateChange() → los cambios posteriores (login, logout, refresco
    //                         del token, o un logout hecho en otra pestaña).
    // Con solo la segunda, al recargar la página el usuario aparecería
    // deslogueado hasta que ocurriera algún evento.
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setLoading(false)
    })

    const { data: subscription } = supabase.auth.onAuthStateChange(
      (_event, next) => {
        setSession(next)
        setLoading(false)
      },
    )

    return () => subscription.subscription.unsubscribe()
  }, [])

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    // Se lanza en vez de devolver el error para que la pantalla de login pueda
    // usar el try/catch de siempre y no tenga que inspeccionar un objeto.
    if (error) throw new Error(translateAuthError(error.message))
    // No hace falta setSession: onAuthStateChange ya lo hará. Pero el rol se
    // devuelve aquí porque quien llama lo necesita YA, y el estado de React
    // todavía no lo refleja.
    return roleOf(data.user) ?? 'CITIZEN'
  }, [])

  const signOut = useCallback(async () => {
    await supabase.auth.signOut()
  }, [])

  const user = session?.user ?? null

  const value = useMemo<AuthValue>(
    () => ({ session, user, role: roleOf(user), loading, signIn, signOut }),
    [session, user, loading, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  }
  return context
}
