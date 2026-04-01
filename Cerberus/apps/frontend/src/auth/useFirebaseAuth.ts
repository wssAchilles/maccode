import type { User } from 'firebase/auth'
import { useCallback, useEffect, useState } from 'react'

import { useI18n } from '../i18n/I18nProvider'
import {
  loadFirebaseAuthModule,
  loadFirebaseAuthServices,
  type FirebaseAuthServices,
} from '../lib/firebase-services'
import { setAuthTokenProvider } from '../lib/auth-session'
import { describeAuthError, getAuthMessage } from './errors'

type AuthStatus = 'disabled' | 'loading' | 'ready' | 'error'

export type FirebaseAuthState = {
  required: boolean
  status: AuthStatus
  user: User | null
  error?: string
  signingIn: boolean
  email: string
  password: string
  setEmail: (value: string) => void
  setPassword: (value: string) => void
  signInWithEmail: () => Promise<void>
  signUpWithEmail: () => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOutCurrentUser: () => Promise<void>
}

export function useFirebaseAuth(): FirebaseAuthState {
  const { locale } = useI18n()
  const authRequiredOverride = import.meta.env.VITE_AUTH_REQUIRED
  const hasFirebaseConfig = Boolean(
    import.meta.env.VITE_FIREBASE_API_KEY && import.meta.env.VITE_FIREBASE_PROJECT_ID,
  )
  const required =
    authRequiredOverride === 'true' ||
    (import.meta.env.PROD && authRequiredOverride !== 'false' && hasFirebaseConfig)
  const [status, setStatus] = useState<AuthStatus>(required ? 'loading' : 'disabled')
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState<string | undefined>(undefined)
  const [signingIn, setSigningIn] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [services, setServices] = useState<FirebaseAuthServices | null>(null)

  useEffect(() => {
    if (!required) {
      setAuthTokenProvider(null)
      setStatus('disabled')
      setServices(null)
      return
    }

    let cancelled = false
    let unsubscribe: (() => void) | undefined

    const initializeServices = async () => {
      const [nextServices, authModule] = await Promise.all([
        loadFirebaseAuthServices(),
        loadFirebaseAuthModule(),
      ])

      if (cancelled) {
        return
      }

      if (!nextServices) {
        setStatus('error')
        setError(getAuthMessage(locale, 'missingConfig'))
        setAuthTokenProvider(null)
        return
      }

      setServices(nextServices)
      setAuthTokenProvider(async () => {
        const current = nextServices.auth.currentUser
        if (!current) {
          return undefined
        }
        return current.getIdToken()
      })

      unsubscribe = authModule.onAuthStateChanged(nextServices.auth, (nextUser) => {
        setUser(nextUser)
        setStatus('ready')
        setError(undefined)
      })
    }

    void initializeServices()

    return () => {
      cancelled = true
      unsubscribe?.()
      setAuthTokenProvider(null)
    }
  }, [locale, required])

  const signInWithEmail = useCallback(async () => {
    if (!services) {
      return
    }
    const normalizedEmail = email.trim().toLowerCase()
    if (!normalizedEmail || !password) {
      setError(getAuthMessage(locale, 'missingCredentials'))
      return
    }

    setSigningIn(true)
    setError(undefined)
    try {
      const authModule = await loadFirebaseAuthModule()
      await authModule.signInWithEmailAndPassword(services.auth, normalizedEmail, password)
    } catch (error) {
      setError(describeAuthError(error, locale))
    } finally {
      setSigningIn(false)
    }
  }, [email, locale, password, services])

  const signUpWithEmail = useCallback(async () => {
    if (!services) {
      return
    }
    const normalizedEmail = email.trim().toLowerCase()
    if (!normalizedEmail || !password) {
      setError(getAuthMessage(locale, 'missingCredentials'))
      return
    }

    setSigningIn(true)
    setError(undefined)
    try {
      const authModule = await loadFirebaseAuthModule()
      await authModule.createUserWithEmailAndPassword(services.auth, normalizedEmail, password)
    } catch (error) {
      setError(describeAuthError(error, locale))
    } finally {
      setSigningIn(false)
    }
  }, [email, locale, password, services])

  const signInWithGoogle = useCallback(async () => {
    if (!services) {
      return
    }
    setSigningIn(true)
    setError(undefined)
    try {
      const authModule = await loadFirebaseAuthModule()
      await authModule.signInWithPopup(services.auth, new authModule.GoogleAuthProvider())
    } catch (error) {
      setError(describeAuthError(error, locale))
    } finally {
      setSigningIn(false)
    }
  }, [locale, services])

  const signOutCurrentUser = useCallback(async () => {
    if (!services) {
      return
    }
    const authModule = await loadFirebaseAuthModule()
    await authModule.signOut(services.auth)
  }, [services])

  return {
    required,
    status,
    user,
    error,
    signingIn,
    email,
    password,
    setEmail,
    setPassword,
    signInWithEmail,
    signUpWithEmail,
    signInWithGoogle,
    signOutCurrentUser,
  }
}
