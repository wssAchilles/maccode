import type { User } from 'firebase/auth'
import { useCallback, useEffect, useRef, useState } from 'react'

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
    authRequiredOverride === 'true' || (import.meta.env.PROD && authRequiredOverride !== 'false')
  const [status, setStatus] = useState<AuthStatus>(() => (required ? 'loading' : 'disabled'))
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState<string | undefined>(undefined)
  const [signingIn, setSigningIn] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const localeRef = useRef(locale)
  const mountedRef = useRef(true)
  const servicesRef = useRef<FirebaseAuthServices | null>(null)
  const initializePromiseRef = useRef<Promise<FirebaseAuthServices | null> | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    localeRef.current = locale
  }, [locale])

  const ensureServices = useCallback(async (): Promise<FirebaseAuthServices | null> => {
    if (!required) {
      return null
    }

    if (servicesRef.current) {
      return servicesRef.current
    }

    if (!initializePromiseRef.current) {
      initializePromiseRef.current = (async () => {
        try {
          const [nextServices, authModule] = await Promise.all([
            loadFirebaseAuthServices(),
            loadFirebaseAuthModule(),
          ])

          if (!mountedRef.current) {
            return nextServices
          }

          if (!nextServices) {
            setStatus('error')
            setError(getAuthMessage(localeRef.current, 'missingConfig'))
            setAuthTokenProvider(null)
            return null
          }

          servicesRef.current = nextServices
          setAuthTokenProvider(async () => {
            const current = nextServices.auth.currentUser
            if (!current) {
              return undefined
            }
            return current.getIdToken()
          })

          if (!unsubscribeRef.current) {
            unsubscribeRef.current = authModule.onAuthStateChanged(nextServices.auth, (nextUser) => {
              if (!mountedRef.current) {
                return
              }
              setUser(nextUser)
              setStatus('ready')
              setError(undefined)
            })
          }

          return nextServices
        } finally {
          initializePromiseRef.current = null
        }
      })()
    }

    return initializePromiseRef.current
  }, [required])

  useEffect(() => {
    mountedRef.current = true

    if (!required) {
      setAuthTokenProvider(null)
      setStatus('disabled')
      servicesRef.current = null
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
      return
    }

    setStatus('loading')
    void ensureServices()

    return () => {
      mountedRef.current = false
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
      setAuthTokenProvider(null)
    }
  }, [ensureServices, required])

  const signInWithEmail = useCallback(async () => {
    const normalizedEmail = email.trim().toLowerCase()
    if (!normalizedEmail || !password) {
      setError(getAuthMessage(locale, 'missingCredentials'))
      return
    }

    setSigningIn(true)
    setError(undefined)
    try {
      const nextServices = (await ensureServices()) ?? servicesRef.current
      if (!nextServices) {
        return
      }
      const authModule = await loadFirebaseAuthModule()
      await authModule.signInWithEmailAndPassword(nextServices.auth, normalizedEmail, password)
    } catch (error) {
      setError(describeAuthError(error, locale))
    } finally {
      setSigningIn(false)
    }
  }, [email, ensureServices, locale, password])

  const signUpWithEmail = useCallback(async () => {
    const normalizedEmail = email.trim().toLowerCase()
    if (!normalizedEmail || !password) {
      setError(getAuthMessage(locale, 'missingCredentials'))
      return
    }

    setSigningIn(true)
    setError(undefined)
    try {
      const nextServices = (await ensureServices()) ?? servicesRef.current
      if (!nextServices) {
        return
      }
      const authModule = await loadFirebaseAuthModule()
      await authModule.createUserWithEmailAndPassword(nextServices.auth, normalizedEmail, password)
    } catch (error) {
      setError(describeAuthError(error, locale))
    } finally {
      setSigningIn(false)
    }
  }, [email, ensureServices, locale, password])

  const signInWithGoogle = useCallback(async () => {
    setSigningIn(true)
    setError(undefined)
    try {
      const nextServices = (await ensureServices()) ?? servicesRef.current
      if (!nextServices) {
        return
      }
      const authModule = await loadFirebaseAuthModule()
      await authModule.signInWithPopup(nextServices.auth, new authModule.GoogleAuthProvider())
    } catch (error) {
      setError(describeAuthError(error, locale))
    } finally {
      setSigningIn(false)
    }
  }, [ensureServices, locale])

  const signOutCurrentUser = useCallback(async () => {
    const nextServices = servicesRef.current ?? (await ensureServices())
    if (!nextServices) {
      return
    }
    const authModule = await loadFirebaseAuthModule()
    await authModule.signOut(nextServices.auth)
  }, [ensureServices])

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
