import { type User, createUserWithEmailAndPassword, onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, signOut } from 'firebase/auth'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { getFirebaseServices } from '../lib/firebase-services'
import { setAuthTokenProvider } from '../lib/auth-session'

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
  signInWithEmailAutoRegister: () => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOutCurrentUser: () => Promise<void>
}

const USER_NOT_FOUND_CODES = new Set(['auth/user-not-found', 'auth/invalid-credential'])

function normalizeAuthError(error: unknown): string {
  const code = (error as { code?: unknown }).code
  const message = (error as { message?: unknown }).message
  if (typeof code === 'string' && code.length > 0) {
    if (code === 'auth/wrong-password') {
      return 'invalid email or password'
    }
    if (code === 'auth/popup-closed-by-user') {
      return 'google sign-in canceled'
    }
    return code
  }
  if (typeof message === 'string' && message.length > 0) {
    return message
  }
  return 'authentication failed'
}

export function useFirebaseAuth(): FirebaseAuthState {
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
      setError('firebase auth is required but firebase config is missing')
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

  const signInWithEmailAutoRegister = useCallback(async () => {
    if (!services) {
      return
    }
    const normalizedEmail = email.trim().toLowerCase()
    if (!normalizedEmail || !password) {
      setError('email and password are required')
      return
    }

    setSigningIn(true)
    setError(undefined)
    try {
      await signInWithEmailAndPassword(services.auth, normalizedEmail, password)
    } catch (error) {
      const code = (error as { code?: unknown }).code
      if (typeof code === 'string' && USER_NOT_FOUND_CODES.has(code)) {
        try {
          await createUserWithEmailAndPassword(services.auth, normalizedEmail, password)
        } catch (createError) {
          setError(normalizeAuthError(createError))
        }
      } else {
        setError(normalizeAuthError(error))
      }
    } finally {
      setSigningIn(false)
    }
  }, [email, password, services])

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
      setError(normalizeAuthError(error))
    } finally {
      setSigningIn(false)
    }
  }, [services])

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
    signInWithEmailAutoRegister,
    signInWithGoogle,
    signOutCurrentUser,
  }
}
