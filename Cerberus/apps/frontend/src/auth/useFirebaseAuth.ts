import {
  type User,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
} from 'firebase/auth'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { useI18n } from '../i18n/I18nProvider'
import { getFirebaseServices } from '../lib/firebase-services'
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
  signInWithGoogle: () => Promise<void>
  signOutCurrentUser: () => Promise<void>
}

export function useFirebaseAuth(): FirebaseAuthState {
  const { locale } = useI18n()
  const required = import.meta.env.VITE_AUTH_REQUIRED === 'true'
  const [status, setStatus] = useState<AuthStatus>(required ? 'loading' : 'disabled')
  const [user, setUser] = useState<User | null>(null)
  const [error, setError] = useState<string | undefined>(undefined)
  const [signingIn, setSigningIn] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const services = useMemo(() => {
    if (!required) {
      return null
    }
    return getFirebaseServices()
  }, [required])

  useEffect(() => {
    if (!required) {
      setAuthTokenProvider(null)
      setStatus('disabled')
      return
    }

    if (!services) {
      setStatus('error')
      setError(getAuthMessage(locale, 'missingConfig'))
      setAuthTokenProvider(null)
      return
    }

    setAuthTokenProvider(async () => {
      const current = services.auth.currentUser
      if (!current) {
        return undefined
      }
      return current.getIdToken()
    })

    const unsubscribe = onAuthStateChanged(services.auth, (nextUser) => {
      setUser(nextUser)
      setStatus('ready')
      setError(undefined)
    })

    return () => {
      unsubscribe()
      setAuthTokenProvider(null)
    }
  }, [required, services])

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
      await signInWithEmailAndPassword(services.auth, normalizedEmail, password)
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
      const { GoogleAuthProvider } = await import('firebase/auth')
      await signInWithPopup(services.auth, new GoogleAuthProvider())
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
    await signOut(services.auth)
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
    signInWithGoogle,
    signOutCurrentUser,
  }
}
