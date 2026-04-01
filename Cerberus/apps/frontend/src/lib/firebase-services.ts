import type { FirebaseApp } from 'firebase/app'
import type { Auth } from 'firebase/auth'

export type FirebaseAuthServices = {
  app: FirebaseApp
  auth: Auth
}

let firebaseAuthModulePromise: Promise<typeof import('firebase/auth')> | null = null

export function loadFirebaseAuthModule(): Promise<typeof import('firebase/auth')> {
  if (!firebaseAuthModulePromise) {
    firebaseAuthModulePromise = import('firebase/auth')
  }

  return firebaseAuthModulePromise
}

export async function loadFirebaseAuthServices(): Promise<FirebaseAuthServices | null> {
  const { initFirebase } = await import('./firebase')
  const app = initFirebase()
  if (!app) {
    return null
  }

  const { getAuth } = await loadFirebaseAuthModule()

  return {
    app,
    auth: getAuth(app),
  }
}
